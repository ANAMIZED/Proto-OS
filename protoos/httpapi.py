"""HTTP/JSON-RPC + SSE baseline transport.

Loopback stdlib server exposing:
  POST /mcp                JSON-RPC 2.0 -> federated MCP mux
  POST /a2a                JSON-RPC 2.0 -> A2A adapter (message/send, tasks/*)
  GET  /agui/<run_id>      text/event-stream of AG-UI events for a run
  GET  /.well-known/agents federated agent directory (Unified Agent Cards)
  GET  /healthz

gRPC/QUIC remain optional per spec and are deferred (see VERIFICATION.md).
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def start_http(proto_os, host: str = "127.0.0.1", port: int = 0):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # keep test output quiet
            pass

        def _json(self, code: int, obj) -> None:
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/healthz":
                return self._json(200, {"ok": True,
                                        "backend": proto_os.ids.backend.name})
            if self.path == "/.well-known/agents":
                cards = [c.to_json() for c in proto_os.registry.all()]
                return self._json(200, {"agents": cards})
            if self.path.startswith("/agui/"):
                run_id = self.path.split("/agui/", 1)[1]
                events = proto_os.ui.events(run_id)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                for ev in events:
                    self.wfile.write(f"data: {json.dumps(ev)}\n\n".encode())
                self.wfile.write(b"data: [DONE]\n\n")
                return
            self._json(404, {"error": "not found"})

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            try:
                req = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._json(400, {"error": "bad json"})
            if self.path == "/mcp":
                return self._json(200, proto_os.mcp.handle(req))
            if self.path == "/a2a":
                return self._json(200, proto_os.a2a.handle(req))
            self._json(404, {"error": "not found"})

    server = ThreadingHTTPServer((host, port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, server.server_address[1]


def stop_http(server, thread) -> None:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
