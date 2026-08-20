"""Hash-chained audit log + OpenTelemetry-shaped tracer.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .canonical import Clock, cjson, new_id


class AuditLog:
    def __init__(self, clock: Clock):
        self.clock = clock
        self.entries: list[dict] = []
        self._prev_hash = "0" * 64

    def append(self, actor: str, action: str, payload: dict | None = None) -> dict:
        # Deep-copy payload so later mutation cannot break the chain
        import copy
        safe_payload = copy.deepcopy(payload or {})
        entry = {
            "id": new_id("aud"),
            "ts": self.clock.now(),
            "actor": actor,
            "action": action,
            "payload": safe_payload,
            "prev": self._prev_hash,
        }
        digest = hashlib.sha256(cjson(entry).encode()).hexdigest()
        entry["hash"] = digest
        self._prev_hash = digest
        self.entries.append(entry)
        return entry

    def verify(self) -> tuple[bool, int | None]:
        prev = "0" * 64
        for i, e in enumerate(self.entries):
            if e.get("prev") != prev:
                return False, i
            check = {k: v for k, v in e.items() if k != "hash"}
            if hashlib.sha256(cjson(check).encode()).hexdigest() != e.get("hash"):
                return False, i
            prev = e["hash"]
        return True, None

    def export_jsonl(self, path: str | Path) -> None:
        path = Path(path)
        with path.open("w") as f:
            for e in self.entries:
                f.write(json.dumps(e, default=str) + "\n")


class Tracer:
    def __init__(self, clock: Clock):
        self.clock = clock
        self.spans: list[dict] = []
        self._stack: list[str] = []

    def start(self, name: str, attrs: dict | None = None) -> str:
        sid = new_id("span")
        parent = self._stack[-1] if self._stack else None
        span = {
            "id": sid,
            "name": name,
            "parent": parent,
            "start": self.clock.now(),
            "end": None,
            "attrs": attrs or {},
            "status": "ok",
            "error": None,
        }
        self.spans.append(span)
        self._stack.append(sid)
        return sid

    def end(self, span_id: str, error: str | None = None) -> None:
        for s in self.spans:
            if s["id"] == span_id:
                s["end"] = self.clock.now()
                if error:
                    s["status"] = "error"
                    s["error"] = error
                break
        if self._stack and self._stack[-1] == span_id:
            self._stack.pop()

    def export_jsonl(self, path: str | Path) -> None:
        path = Path(path)
        with path.open("w") as f:
            for s in self.spans:
                f.write(json.dumps(s, default=str) + "\n")
