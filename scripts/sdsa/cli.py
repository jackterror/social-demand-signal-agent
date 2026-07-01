from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import sys
from typing import Any

from .config import ConfigError, load_profile, profile_summary, require_live_ready
from .pipeline import process_signals
from .providers import ProviderError, collect_socialcrawl, load_json_records
from .server import run_server
from .storage import Store


ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "runtime"
DEFAULT_PROFILE = RUNTIME / "company-profile.json"
DEFAULT_DB = RUNTIME / "signal-agent.sqlite3"
PROFILE_TEMPLATE = ROOT / "assets" / "company-profile.example.json"
DEMO_PROFILE = ROOT / "assets" / "fixtures" / "demo-profile.json"
DEMO_SIGNALS = ROOT / "assets" / "fixtures" / "signals.json"
DEMO_DRAFTS = ROOT / "assets" / "fixtures" / "agent-results.json"


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def collect_records(
    provider: str,
    profile: dict[str, Any],
    source: pathlib.Path | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    if provider in {"fixture", "json"}:
        if source is None:
            raise ProviderError(f"--source is required for provider {provider}")
        label = "fixture" if provider == "fixture" else "observed"
        return load_json_records(source, data_label=label), [f"loaded {source}"]
    if provider == "socialcrawl":
        require_live_ready(profile)
        listening = profile["listening"]
        return collect_socialcrawl(
            os.environ.get("SOCIALCRAWL_API_KEY", ""),
            list(listening["queries"]),
            list(listening["platforms"]),
            int(listening.get("max_items", 50)),
        )
    raise ProviderError(f"Unknown provider: {provider}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="signal-agent",
        description="Run a company-configured, human-reviewed social demand workflow.",
    )
    parser.add_argument("--profile", type=pathlib.Path, default=DEFAULT_PROFILE)
    parser.add_argument("--database", type=pathlib.Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create an editable company profile")
    init.add_argument("--force", action="store_true")

    sub.add_parser("validate", help="Validate the company profile")

    collect = sub.add_parser("collect", help="Collect and route signals")
    collect.add_argument("--provider", choices=("fixture", "json", "socialcrawl"), required=True)
    collect.add_argument("--source", type=pathlib.Path)

    export = sub.add_parser("agent-export", help="Export pending signals for host-agent analysis")
    export.add_argument("--output", type=pathlib.Path, default=RUNTIME / "agent-batch.json")

    import_cmd = sub.add_parser("agent-import", help="Validate and import host-agent drafts")
    import_cmd.add_argument("--input", type=pathlib.Path, required=True)

    review = sub.add_parser("review", help="Record a human review decision")
    review.add_argument("signal_id")
    review.add_argument("decision", choices=("approved", "rejected", "escalated"))
    review.add_argument("--body", default="")
    review.add_argument("--note", default="")

    event = sub.add_parser("event", help="Record a downstream outcome")
    event.add_argument("signal_id")
    event.add_argument("event_type")
    event.add_argument("--data-label", default="reviewer_entered")

    state = sub.add_parser("state", help="Export current state")
    state.add_argument("--output", type=pathlib.Path)

    demo = sub.add_parser("demo", help="Build a labeled fixture demonstration")
    demo.add_argument("--reset", action="store_true")

    serve = sub.add_parser("serve", help="Start the local review application")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8766)
    serve.add_argument("--no-browser", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            if args.profile.exists() and not args.force:
                raise ConfigError(f"Profile already exists: {args.profile}. Use --force to replace it.")
            args.profile.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(PROFILE_TEMPLATE, args.profile)
            print(f"Created company profile: {args.profile}")
            print("Edit every required field, then set profile_status to ready.")
            return 0

        if args.command == "demo":
            if args.reset and args.database.exists():
                args.database.unlink()
            args.profile.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(DEMO_PROFILE, args.profile)
            profile = load_profile(args.profile)
            signals = process_signals(load_json_records(DEMO_SIGNALS, "fixture"), profile)
            store = Store(args.database)
            store.upsert_signals(signals)
            drafts = json.loads(DEMO_DRAFTS.read_text(encoding="utf-8"))["results"]
            store.import_drafts(drafts)
            store.close()
            print(f"Fixture demo ready with {len(signals)} signal(s).")
            return 0

        profile = load_profile(args.profile)

        if args.command == "validate":
            print(json.dumps(profile_summary(profile), indent=2))
            return 0

        if args.command == "serve":
            return run_server(args.profile, args.database, args.host, args.port, args.no_browser)

        store = Store(args.database)
        try:
            if args.command == "collect":
                signals, logs = collect_records(args.provider, profile, args.source)
                processed = process_signals(signals, profile)
                store.upsert_signals(processed)
                print(json.dumps({"collected": len(signals), "stored": len(processed), "logs": logs}, indent=2))
            elif args.command == "agent-export":
                payload = {
                    "profile": profile,
                    "instructions": "Follow references/agent-contract.md. Return only the required JSON object.",
                    "signals": store.agent_batch(),
                }
                write_json(args.output, payload)
                print(f"Exported {len(payload['signals'])} pending signal(s) to {args.output}")
            elif args.command == "agent-import":
                payload = json.loads(args.input.read_text(encoding="utf-8"))
                count = store.import_drafts(payload.get("results") or [])
                print(f"Imported {count} variant draft(s)")
            elif args.command == "review":
                store.review(args.signal_id, args.decision, args.body, args.note)
                print(f"Recorded {args.decision} for {args.signal_id}")
            elif args.command == "event":
                store.record_event(
                    args.signal_id,
                    args.event_type,
                    args.data_label,
                    max_responses_per_author_24h=int(profile["safety"]["max_responses_per_author_24h"]),
                )
                print(f"Recorded {args.event_type} for {args.signal_id}")
            elif args.command == "state":
                state = store.state(profile)
                if args.output:
                    write_json(args.output, state)
                    print(f"Wrote state to {args.output}")
                else:
                    print(json.dumps(state, indent=2))
        finally:
            store.close()
        return 0
    except (ConfigError, ProviderError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
