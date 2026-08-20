"""HTTP/JSON-RPC + SSE transport surface (loopback).

Endpoints:
  POST /mcp          MCP JSON-RPC
  POST /a2a          A2A JSON-RPC
  GET  /agui/<run>   AG-UI SSE stream
  GET  /.well-known/agents
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import ProtoOS


class ProtoHTTPHandler(BaseHTTPRequestHandler):
    os_: "ProtoOS" = None  # set by server factory

    def log_message(self, fmt, *args):
        pass  # quiet

    def _json(self, code: int, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/.well-known/agents"):
            cards = [c.to_dict() for c in self.os_.registry.list()]
            self._json(200, {"agents": cards})
            return
        if self.path.startswith("/agui/"):
            run_id = self.path.split("/agui/", 1)[1].split("?")[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            for ev in self.os_.ui.subscribe(run_id):
                data = json.dumps(ev)
                self.wfile.write(f"data: {data}\n\n".encode())
                self.wfile.flush()
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            req = json.loads(raw)
        except Exception:
            self._json(400, {"error": "invalid json"})
            return
        if self.path == "/mcp":
            result = self.os_.mcp.handle_jsonrpc(req)
            self._json(200, result)
            return
        if self.path == "/a2a":
            result = self.os_.a2a.handle_jsonrpc(req)
            self._json(200, result)
            return
        self._json(404, {"error": "not found"})


def serve(os_: "ProtoOS", host: str = "127.0.0.1", port: int = 8080):
    ProtoHTTPHandler.os_ = os_
    server = HTTPServer((host, port), ProtoHTTPHandler)
    return server
