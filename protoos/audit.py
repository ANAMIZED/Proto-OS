"""Observability & Audit.

  - AuditLog: hash-chained, tamper-evident record of every mandate, policy
    decision, tool call, delegation and payment.
  - Tracer: OpenTelemetry-shaped spans (trace/span/parent ids, wall times,
    attributes) covering task graphs, tool latency, settlement times and
    policy decisions; exportable as JSONL.
"""
from __future__ import annotations

import copy

import contextlib
import json
import threading
from pathlib import Path

from .canonical import Clock, cjson, new_id, sha256_hex

GENESIS = "0" * 64


class AuditLog:
    def __init__(self, clock: Clock):
        self.clock = clock
        self.entries: list[dict] = []
        self._lock = threading.Lock()

    def append(self, actor: str, action: str, payload: dict) -> dict:
        payload = copy.deepcopy(payload)  # chain integrity: own the bytes we hash
        with self._lock:
            prev = self.entries[-1]["hash"] if self.entries else GENESIS
            entry = {
                "i": len(self.entries),
                "ts": self.clock.now(),
                "actor": actor,
                "action": action,
                "payload": payload,
                "payload_hash": sha256_hex(cjson(payload)),
                "prev": prev,
            }
            entry["hash"] = sha256_hex(cjson(entry))
            self.entries.append(entry)
            return entry

    def verify(self) -> tuple[bool, int | None]:
        prev = GENESIS
        for i, e in enumerate(self.entries):
            body = {k: v for k, v in e.items() if k != "hash"}
            if e.get("prev") != prev or e.get("i") != i:
                return False, i
            if sha256_hex(cjson(e["payload"])) != e.get("payload_hash"):
                return False, i
            if sha256_hex(cjson(body)) != e.get("hash"):
                return False, i
            prev = e["hash"]
        return True, None

    def by_action(self, prefix: str) -> list[dict]:
        return [e for e in self.entries if e["action"].startswith(prefix)]

    def export_jsonl(self, path: str | Path) -> int:
        p = Path(path)
        with p.open("w") as f:
            for e in self.entries:
                f.write(json.dumps(e, sort_keys=True) + "\n")
        return len(self.entries)


class Tracer:
    def __init__(self, clock: Clock):
        self.clock = clock
        self.spans: list[dict] = []
        self._stack = threading.local()
        self._lock = threading.Lock()

    def _current(self):
        return getattr(self._stack, "frames", [])

    @contextlib.contextmanager
    def span(self, name: str, attrs: dict | None = None):
        frames = self._current()
        parent = frames[-1] if frames else None
        s = {
            "trace_id": parent["trace_id"] if parent else new_id("trace"),
            "span_id": new_id("span"),
            "parent_id": parent["span_id"] if parent else None,
            "name": name,
            "start": self.clock.now(),
            "attrs": dict(attrs or {}),
            "status": "ok",
        }
        self._stack.frames = frames + [s]
        try:
            yield s
        except Exception as exc:
            s["status"] = "error"
            s["attrs"]["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            s["end"] = self.clock.now()
            s["duration_ms"] = round((s["end"] - s["start"]) * 1000, 3)
            self._stack.frames = self._current()[:-1]
            with self._lock:
                self.spans.append(s)

    def export_jsonl(self, path: str | Path) -> int:
        p = Path(path)
        with p.open("w") as f:
            for s in self.spans:
                f.write(json.dumps(s, sort_keys=True) + "\n")
        return len(self.spans)
