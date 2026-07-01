from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import socket
import sys
from typing import Any

from .config import (
    ConfigError,
    atomic_write_json,
    backup_profile,
    ensure_profile,
    load_profile,
    migrate_profile,
    profile_summary,
    read_profile,
    save_profile,
    setup_status,
)
from .pipeline import process_signals
from .providers import ProviderError, collect_socialcrawl, load_json_records
from .server import run_server
from .settings import credential_status, runtime_api_key
from .storage import Store


ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "runtime"
DEFAULT_PROFILE = RUNTIME / "company-profile.json"
DEFAULT_DB = RUNTIME / "signal-agent.sqlite3"
DEFAULT_ENV = ROOT / ".env"
PROFILE_TEMPLATE = ROOT / "assets" / "company-profile.example.json"
DEMO_PROFILE = ROOT / "assets" / "fixtures" / "demo-profile.json"
DEMO_SIGNALS = ROOT / "assets" / "fixtures" / "signals.json"
DEMO_DRAFTS = ROOT / "assets" / "fixtures" / "agent-results.json"


def write_json(path: pathlib.Path, value: Any) -> None:
    if not isinstance(value, dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        return
    atomic_write_json(path, value)


def build_demo(profile_path: pathlib.Path, database_path: pathlib.Path, reset: bool) -> int:
    if reset and database_path.exists():
        database_path.unlink()
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DEMO_PROFILE, profile_path)
    profile = load_profile(profile_path)
    signals = process_signals(load_json_records(DEMO_SIGNALS, "fixture"), profile)
    store = Store(database_path)
    try:
        store.upsert_signals(signals)
        drafts = json.loads(DEMO_DRAFTS.read_text(encoding="utf-8"))["results"]
        store.import_drafts(drafts)
    finally:
        store.close()
    return len(signals)


def collect_records(
    provider: str,
    profile: dict[str, Any],
    source: pathlib.Path | None,
    env_path: pathlib.Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    if provider in {"fixture", "json"}:
        if source is None:
            raise ProviderError(f"--source is required for provider {provider}")
        label = "fixture" if provider == "fixture" else "observed"
        return load_json_records(source, data_label=label), [f"loaded {source}"]
    if provider == "socialcrawl":
        from .config import require_live_ready

        require_live_ready(profile)
        listening = profile["listening"]
        api_key, _ = runtime_api_key(env_path)
        return collect_socialcrawl(
            api_key,
            list(listening["queries"]),
            list(listening["platforms"]),
            int(listening.get("max_items", 50)),
        )
    raise ProviderError(f"Unknown provider: {provider}")


def port_available(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind((host, port))
        return True
    except OSError:
        return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="signal-agent",
        description="Run a company-configured, human-reviewed social listening workflow.",
    )
    parser.add_argument("--profile", type=pathlib.Path, default=DEFAULT_PROFILE)
    parser.add_argument("--database", type=pathlib.Path, default=DEFAULT_DB)
    parser.add_argument("--env-file", type=pathlib.Path, default=DEFAULT_ENV)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create the local setup profile")
    init.add_argument("--force", action="store_true")
    sub.add_parser("validate", help="Validate the company profile")
    sub.add_parser("setup-status", help="Show profile and provider readiness without secrets")
    doctor = sub.add_parser("doctor", help="Check local setup and runtime readiness")
    doctor.add_argument("--host", default="127.0.0.1")
    doctor.add_argument("--port", type=int, default=8766)

    export_profile = sub.add_parser("profile-export", help="Export the company profile without credentials")
    export_profile.add_argument("--output", type=pathlib.Path, required=True)
    import_profile = sub.add_parser("profile-import", help="Import a company profile without credentials")
    import_profile.add_argument("--input", type=pathlib.Path, required=True)

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
            if args.profile.exists() and args.force:
                backup_profile(args.profile, "manual")
                shutil.copyfile(PROFILE_TEMPLATE, args.profile)
            elif args.profile.exists():
                ensure_profile(args.profile, PROFILE_TEMPLATE)
            else:
                ensure_profile(args.profile, PROFILE_TEMPLATE)
            print(f"Setup profile ready: {args.profile}")
            print("Launch the dashboard to complete onboarding.")
            return 0

        if args.command == "profile-import":
            incoming = read_profile(args.input)
            migrated, _, _ = migrate_profile(incoming)
            complete = migrated.get("profile_status") == "ready"
            backup_profile(args.profile, "pre-import")
            save_profile(args.profile, migrated, complete=complete)
            print(f"Imported profile: {args.profile}")
            return 0

        if args.command == "demo":
            count = build_demo(args.profile, args.database, args.reset)
            print(f"Fixture demo ready with {count} signal(s).")
            return 0

        profile, backup = ensure_profile(args.profile, PROFILE_TEMPLATE)
        if backup:
            print(f"Migrated profile and wrote backup: {backup}")

        if args.command == "setup-status":
            status = setup_status(profile, bool(credential_status(args.env_file)["configured"]))
            print(json.dumps(status, indent=2))
            return 0

        if args.command == "doctor":
            status = setup_status(profile, bool(credential_status(args.env_file)["configured"]))
            checks = {
                "python_3_11_or_newer": sys.version_info >= (3, 11),
                "profile_ready": status["profile_ready"],
                "provider_ready": status["provider_ready"],
                "runtime_writable": args.profile.parent.exists() and args.profile.parent.is_dir() and os.access(args.profile.parent, os.W_OK),
                "port_available": port_available(args.host, args.port),
            }
            print(json.dumps({"checks": checks, "setup": status}, indent=2))
            return 0 if all(checks.values()) else 2

        if args.command == "profile-export":
            write_json(args.output, profile)
            print(f"Exported profile without credentials: {args.output}")
            return 0

        if args.command == "serve":
            return run_server(args.profile, args.database, args.env_file, args.host, args.port, args.no_browser)

        profile = load_profile(args.profile)
        if args.command == "validate":
            print(json.dumps(profile_summary(profile), indent=2))
            return 0

        store = Store(args.database)
        try:
            if args.command == "collect":
                signals, logs = collect_records(args.provider, profile, args.source, args.env_file)
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
                current = store.state(profile)
                if args.output:
                    write_json(args.output, current)
                    print(f"Wrote state to {args.output}")
                else:
                    print(json.dumps(current, indent=2))
        finally:
            store.close()
        return 0
    except (ConfigError, ProviderError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
