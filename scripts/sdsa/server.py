from __future__ import annotations

import json
import mimetypes
import os
import pathlib
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .config import load_profile, require_live_ready
from .pipeline import process_signals
from .providers import collect_socialcrawl, load_json_records
from .storage import Store


ROOT = pathlib.Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True).encode("utf-8")


def build_handler(profile_path: pathlib.Path, database_path: pathlib.Path):
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, status: int, value: Any) -> None:
            payload = json_bytes(value)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            payload = self.rfile.read(length) if length else b"{}"
            value = json.loads(payload.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("Request body must be an object")
            return value

        def do_GET(self) -> None:
            path = urllib.parse.urlparse(self.path).path
            if path == "/api/state":
                try:
                    profile = load_profile(profile_path)
                    store = Store(database_path)
                    state = store.state(profile)
                    store.close()
                    self.send_json(200, state)
                except Exception as exc:
                    self.send_json(500, {"error": str(exc)})
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
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:
            path = urllib.parse.urlparse(self.path).path
            store: Store | None = None
            try:
                body = self.read_json()
                store = Store(database_path)
                if path == "/api/collect":
                    profile = load_profile(profile_path)
                    provider = str(body.get("provider") or "")
                    source = str(body.get("source") or "")
                    if provider == "fixture":
                        source_path = ROOT / "assets" / "fixtures" / "signals.json"
                        signals = load_json_records(source_path, "fixture")
                        logs = [f"loaded {source_path.name}"]
                    elif provider == "json":
                        if not source:
                            raise ValueError("A JSON source path is required")
                        signals = load_json_records(pathlib.Path(source).expanduser(), "observed")
                        logs = [f"loaded {source}"]
                    elif provider == "socialcrawl":
                        require_live_ready(profile)
                        listening = profile["listening"]
                        signals, logs = collect_socialcrawl(
                            os.environ.get("SOCIALCRAWL_API_KEY", ""),
                            list(listening["queries"]),
                            list(listening["platforms"]),
                            int(listening.get("max_items", 50)),
                        )
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
                    payload = {
                        "profile": load_profile(profile_path),
                        "instructions": "Follow references/agent-contract.md. Return only the required JSON object.",
                        "signals": batch,
                    }
                    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
                    store.close()
                    self.send_json(200, {"exported": len(batch), "path": str(output_path)})
                    return
                if path == "/api/review":
                    store.review(
                        str(body.get("signal_id") or ""),
                        str(body.get("decision") or ""),
                        str(body.get("final_body") or ""),
                        str(body.get("note") or ""),
                    )
                elif path == "/api/event":
                    profile = load_profile(profile_path)
                    store.record_event(
                        str(body.get("signal_id") or ""),
                        str(body.get("event_type") or ""),
                        str(body.get("data_label") or "reviewer_entered"),
                        max_responses_per_author_24h=int(profile["safety"]["max_responses_per_author_24h"]),
                    )
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


def run_server(
    profile_path: pathlib.Path,
    database_path: pathlib.Path,
    host: str,
    port: int,
    no_browser: bool,
) -> int:
    load_profile(profile_path)
    url = f"http://{host}:{port}/"
    server = ThreadingHTTPServer((host, port), build_handler(profile_path, database_path))
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
