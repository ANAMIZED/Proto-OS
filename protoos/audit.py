"""Observability & Audit.

  - AuditLog: hash-chained, tamper-evident log of every mandate, tool call,
    delegation and payment. append() deep-copies payloads.
  - Tracer: OTel-shaped spans for run/tool/purchase/graph.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .canonical import Clock, cjson, new_id, sha256_hex


class AuditLog:
    def __init__(self, clock: Clock):
        self.clock = clock
        self.entries: list[dict] = []
        self._prev = "0" * 64

    def append(self, actor: str, action: str, payload: dict | None = None) -> dict:
        # Deep-copy to close aliasing hole (caller must not be able to mutate
        # the logged dict and break the hash chain after the fact).
        body = {
            "seq": len(self.entries),
            "ts": self.clock.now(),
            "actor": actor,
            "action": action,
            "payload": copy.deepcopy(payload or {}),
            "prev": self._prev,
        }
        body["hash"] = sha256_hex(cjson(body))
        self._prev = body["hash"]
        self.entries.append(body)
        return body

    def verify(self) -> tuple[bool, int | None]:
        prev = "0" * 64
        for i, e in enumerate(self.entries):
            if e.get("prev") != prev:
                return False, i
            check = {k: v for k, v in e.items() if k != "hash"}
            if sha256_hex(cjson(check)) != e.get("hash"):
                return False, i
            prev = e["hash"]
        return True, None

    def export_jsonl(self) -> str:
        return "\n".join(json.dumps(e, sort_keys=True) for e in self.entries) + "\n"


@dataclass
class Span:
    name: str
    start: float
    end: float | None = None
    parent: str | None = None
    attrs: dict = field(default_factory=dict)
    status: str = "ok"
    span_id: str = field(default_factory=lambda: new_id("span"))


class Tracer:
    def __init__(self, clock: Clock):
        self.clock = clock
        self.spans: list[Span] = []
        self._stack: list[Span] = []

    def start(self, name: str, **attrs) -> Span:
        parent = self._stack[-1].span_id if self._stack else None
        s = Span(name=name, start=self.clock.now(), parent=parent, attrs=attrs)
        self._stack.append(s)
        self.spans.append(s)
        return s

    def end(self, span: Span | None = None, status: str = "ok") -> None:
        s = span or (self._stack[-1] if self._stack else None)
        if not s:
            return
        s.end = self.clock.now()
        s.status = status
        if self._stack and self._stack[-1] is s:
            self._stack.pop()

    def export_jsonl(self) -> str:
        rows = []
        for s in self.spans:
            rows.append({
                "span_id": s.span_id, "name": s.name, "start": s.start,
                "end": s.end, "parent": s.parent, "status": s.status,
                "attrs": s.attrs,
            })
        return "\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n"
