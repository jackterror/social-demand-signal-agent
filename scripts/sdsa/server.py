from __future__ import annotations

import json
import mimetypes
import pathlib
import shutil
import threading
import urllib.parse
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .config import (
    ConfigError,
    backup_profile,
    ensure_profile,
    load_profile,
    read_profile,
    require_live_ready,
    save_profile,
    setup_status,
)
from .pipeline import process_signals
from .providers import ProviderError, collect_socialcrawl, load_json_records, test_socialcrawl
from .settings import credential_status, remove_api_key, runtime_api_key, save_api_key
from .storage import Store


ROOT = pathlib.Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
PROFILE_TEMPLATE = ASSETS / "company-profile.example.json"
DEMO_PROFILE = ASSETS / "fixtures" / "demo-profile.json"
DEMO_SIGNALS = ASSETS / "fixtures" / "signals.json"
DEMO_DRAFTS = ASSETS / "fixtures" / "agent-results.json"
SOCIALCRAWL_SIGNUP_URL = "https://www.socialcrawl.dev/"
SOCIALCRAWL_DOCS_URL = "https://www.socialcrawl.dev/docs/authentication"
MAX_REQUEST_BYTES = 1_000_000


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True).encode("utf-8")


def reset_demo(profile_path: pathlib.Path, database_path: pathlib.Path) -> int:
    if database_path.exists():
        database_path.unlink()
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    backup_profile(profile_path, "pre-demo")
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


def build_handler(profile_path: pathlib.Path, database_path: pathlib.Path, env_path: pathlib.Path | None = None):
    env_file = env_path or ROOT / ".env"
    provider_runtime: dict[str, Any] = {"state": "untested", "checked_at": None}

    class Handler(BaseHTTPRequestHandler):
        def security_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")

        def send_json(self, status: int, value: Any, extra_headers: dict[str, str] | None = None) -> None:
            payload = json_bytes(value)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.security_headers()
            for name, content in (extra_headers or {}).items():
                self.send_header(name, content)
            self.end_headers()
            self.wfile.write(payload)

        def read_json(self) -> dict[str, Any]:
            content_type = self.headers.get("Content-Type", "")
            if not content_type.startswith("application/json"):
                raise ValueError("Content-Type must be application/json")
            length = int(self.headers.get("Content-Length", "0"))
            if length > MAX_REQUEST_BYTES:
                raise ValueError("Request body is too large")
            payload = self.rfile.read(length) if length else b"{}"
            value = json.loads(payload.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("Request body must be an object")
            return value

        def require_local_mutation(self) -> None:
            if self.headers.get("X-SDSA-Request") != "local":
                raise ValueError("Missing local request header")
            origin = self.headers.get("Origin")
            host = self.headers.get("Host")
            if origin and host and origin not in {f"http://{host}", f"https://{host}"}:
                raise ValueError("Cross-origin requests are not allowed")

        def current_setup(self) -> dict[str, Any]:
            profile, _ = ensure_profile(profile_path, PROFILE_TEMPLATE)
            credentials = credential_status(env_file)
            readiness = setup_status(profile, bool(credentials["configured"]))
            provider_state = provider_runtime["state"] if credentials["configured"] else "missing"
            return {
                "profile": profile,
                "readiness": readiness,
                "provider": {
                    "name": "SocialCrawl",
                    "credential_configured": credentials["configured"],
                    "credential_source": credentials["source"],
                    "connection_state": provider_state,
                    "checked_at": provider_runtime["checked_at"],
                    "signup_url": SOCIALCRAWL_SIGNUP_URL,
                    "docs_url": SOCIALCRAWL_DOCS_URL,
                },
            }

        def do_GET(self) -> None:
            path = urllib.parse.urlparse(self.path).path
            if path == "/api/setup":
                try:
                    self.send_json(200, self.current_setup())
                except Exception as exc:
                    self.send_json(500, {"error": str(exc)})
                return
            if path == "/api/state":
                try:
                    profile = load_profile(profile_path)
                    if profile.get("profile_status") == "setup":
                        raise ConfigError("Complete setup or load the fixture demo before opening the review queue")
                    store = Store(database_path)
                    try:
                        state = store.state(profile)
                    finally:
                        store.close()
                    self.send_json(200, state)
                except Exception as exc:
                    self.send_json(409, {"error": str(exc)})
                return
            target = ASSETS / ("index.html" if path in {"", "/"} else path.lstrip("/"))
            try:
                resolved = target.resolve()
                if ASSETS.resolve() not in resolved.parents and resolved != ASSETS.resolve():
                    raise FileNotFoundError
                payload = resolved.read_bytes()
            except (FileNotFoundError, IsADirectoryError):
                self.send_error(404)
                return
            content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.security_headers()
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:
            path = urllib.parse.urlparse(self.path).path
            store: Store | None = None
            try:
                self.require_local_mutation()
                body = self.read_json()

                if path == "/api/setup/save":
                    profile = body.get("profile")
                    if not isinstance(profile, dict):
                        raise ValueError("Profile must be an object")
                    saved = save_profile(profile_path, profile, complete=bool(body.get("complete")))
                    self.send_json(200, {"saved": True, "setup": self.current_setup(), "profile_status": saved["profile_status"]})
                    return
                if path == "/api/credential":
                    action = str(body.get("action") or "")
                    if action == "save":
                        save_api_key(env_file, str(body.get("api_key") or ""))
                        provider_runtime.update({"state": "untested", "checked_at": None})
                    elif action == "remove":
                        remove_api_key(env_file)
                        provider_runtime.update({"state": "missing", "checked_at": None})
                    else:
                        raise ValueError("Credential action must be save or remove")
                    self.send_json(200, {"saved": True, "provider": self.current_setup()["provider"]})
                    return
                if path == "/api/provider/test":
                    api_key, _ = runtime_api_key(env_file)
                    try:
                        result = test_socialcrawl(api_key)
                        provider_runtime.update({"state": "connected", "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
                        self.send_json(200, result | {"provider": self.current_setup()["provider"]})
                    except Exception:
                        provider_runtime.update({"state": "failed", "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
                        raise ProviderError("SocialCrawl did not accept the configured credential")
                    return
                if path == "/api/reset/setup":
                    backup_profile(profile_path, "pre-reset")
                    shutil.copyfile(PROFILE_TEMPLATE, profile_path)
                    self.send_json(200, {"reset": True, "setup": self.current_setup()})
                    return
                if path == "/api/reset/demo":
                    count = reset_demo(profile_path, database_path)
                    self.send_json(200, {"reset": True, "signals": count, "setup": self.current_setup()})
                    return

                store = Store(database_path)
                if path == "/api/collect":
                    profile = load_profile(profile_path)
                    provider = str(body.get("provider") or "")
                    source = str(body.get("source") or "")
                    if provider == "fixture":
                        if profile.get("profile_status") != "demo":
                            raise ValueError("Load the fixture demo before collecting fixture records")
                        signals = load_json_records(DEMO_SIGNALS, "fixture")
                        logs = [f"loaded {DEMO_SIGNALS.name}"]
                    elif provider == "json":
                        require_live_ready(profile)
                        if not source:
                            raise ValueError("A JSON source path is required")
                        signals = load_json_records(pathlib.Path(source).expanduser(), "observed")
                        logs = [f"loaded {source}"]
                    elif provider == "socialcrawl":
                        require_live_ready(profile)
                        listening = profile["listening"]
                        api_key, _ = runtime_api_key(env_file)
                        signals, logs = collect_socialcrawl(api_key, list(listening["queries"]), list(listening["platforms"]), int(listening.get("max_items", 50)))
                    else:
                        raise ValueError("Provider must be fixture, json, or socialcrawl")
                    processed = process_signals(signals, profile)
                    store.upsert_signals(processed)
                    store.close()
                    self.send_json(200, {"collected": len(signals), "stored": len(processed), "logs": logs})
                    return
                if path == "/api/export":
                    output_path = ROOT / "runtime" / "agent-batch.json"
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    batch = store.agent_batch()
                    payload = {"profile": load_profile(profile_path), "instructions": "Follow references/agent-contract.md. Return only the required JSON object.", "signals": batch}
                    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
                    store.close()
                    self.send_json(200, {"exported": len(batch), "path": str(output_path)})
                    return
                if path == "/api/review":
                    store.review(str(body.get("signal_id") or ""), str(body.get("decision") or ""), str(body.get("final_body") or ""), str(body.get("note") or ""))
                elif path == "/api/event":
                    profile = load_profile(profile_path)
                    store.record_event(str(body.get("signal_id") or ""), str(body.get("event_type") or ""), str(body.get("data_label") or "reviewer_entered"), max_responses_per_author_24h=int(profile["safety"]["max_responses_per_author_24h"]))
                else:
                    store.close()
                    self.send_json(404, {"error": "not found"})
                    return
                store.close()
                self.send_json(200, {"ok": True})
            except Exception as exc:
                if store is not None:
                    store.close()
                self.send_json(400, {"error": str(exc)})

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


def run_server(profile_path: pathlib.Path, database_path: pathlib.Path, env_path: pathlib.Path, host: str, port: int, no_browser: bool) -> int:
    if host not in {"127.0.0.1", "localhost"}:
        raise ConfigError("The local application can only bind to a loopback address")
    ensure_profile(profile_path, PROFILE_TEMPLATE)
    url = f"http://{host}:{port}/"
    server = ThreadingHTTPServer((host, port), build_handler(profile_path, database_path, env_path))
    print(f"Social Demand Signal Agent: {url}")
    if not no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
