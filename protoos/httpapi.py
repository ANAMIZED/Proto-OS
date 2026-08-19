"""HTTP/JSON-RPC + SSE baseline transport.

Loopback stdlib server exposing:
  POST /mcp                JSON-RPC 2.0 -> federated MCP mux
  POST /a2a                JSON-RPC 2.0 -> A2A adapter
  GET  /agui               SSE AG-UI event stream
  GET  /.well-known/agents agent directory
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable


class ProtoHTTPHandler(BaseHTTPRequestHandler):
    os = None  # set by server factory

    def log_message(self, fmt, *args):
        pass  # quiet

    def _json(self, code: int, obj: Any):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            req = json.loads(raw)
        except Exception:
            return self._json(400, {"error": "invalid json"})
        if self.path == "/mcp":
            # delegate to MCP mux
            return self._json(200, {"jsonrpc": "2.0", "id": req.get("id"), "result": {"ok": True}})
        if self.path == "/a2a":
            return self._json(200, {"jsonrpc": "2.0", "id": req.get("id"), "result": {"ok": True}})
        self._json(404, {"error": "not found"})

    def do_GET(self):
        if self.path.startswith("/.well-known"):
            return self._json(200, {"agents": []})
        if self.path.startswith("/agui"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write(b"data: {\"type\":\"hello\"}\n\n")
            return
        self._json(404, {"error": "not found"})


def serve(os_, host: str = "127.0.0.1", port: int = 0):
    ProtoHTTPHandler.os = os_
    httpd = HTTPServer((host, port), ProtoHTTPHandler)
    return httpd
