"""Runtime primitives: TaskGraph, sessions, rate limiter, kill switch, sandbox.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Callable

from .canonical import Clock, ProtoHalted, RateLimited, new_id


class TaskGraph:
    """DAG of tasks; topological order; cycle detection."""

    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.edges: list[tuple[str, str]] = []

    def add(self, task_id: str, meta: dict | None = None) -> None:
        self.nodes[task_id] = meta or {}

    def edge(self, from_id: str, to_id: str) -> None:
        self.edges.append((from_id, to_id))

    def order(self) -> list[str]:
        from collections import deque
        indeg = defaultdict(int)
        adj = defaultdict(list)
        for a, b in self.edges:
            adj[a].append(b)
            indeg[b] += 1
        for n in self.nodes:
            indeg.setdefault(n, 0)
        q = deque([n for n in self.nodes if indeg[n] == 0])
        out = []
        while q:
            n = q.popleft()
            out.append(n)
            for m in adj[n]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    q.append(m)
        if len(out) != len(self.nodes):
            raise ValueError("cycle detected in TaskGraph")
        return out


class SessionManager:
    def __init__(self, clock: Clock):
        self.clock = clock
        self._sessions: dict[str, dict] = {}

    def open(self, principal: str, ttl: float = 3600) -> str:
        sid = new_id("sess")
        self._sessions[sid] = {
            "principal": principal,
            "opened": self.clock.now(),
            "expires": self.clock.now() + ttl,
            "state": {},
        }
        return sid

    def get(self, sid: str) -> dict | None:
        s = self._sessions.get(sid)
        if not s or s["expires"] < self.clock.now():
            return None
        return s

    def close(self, sid: str) -> None:
        self._sessions.pop(sid, None)


class RateLimiter:
    """Token-bucket rate limiter."""

    def __init__(self, clock: Clock, rate_per_sec: float = 10.0, burst: int = 20):
        self.clock = clock
        self.rate = rate_per_sec
        self.burst = burst
        self._tokens: dict[str, float] = defaultdict(lambda: float(burst))
        self._last: dict[str, float] = {}

    def check(self, key: str) -> None:
        now = self.clock.now()
        last = self._last.get(key, now)
        elapsed = now - last
        self._tokens[key] = min(self.burst, self._tokens[key] + elapsed * self.rate)
        self._last[key] = now
        if self._tokens[key] < 1.0:
            raise RateLimited(f"rate limited: {key}")
        self._tokens[key] -= 1.0


class KillSwitch:
    def __init__(self):
        self._global = False
        self._scoped: set[str] = set()

    def engage(self, scope: str | None = None) -> None:
        if scope is None:
            self._global = True
        else:
            self._scoped.add(scope)

    def release(self, scope: str | None = None) -> None:
        if scope is None:
            self._global = False
            self._scoped.clear()
        else:
            self._scoped.discard(scope)

    def check(self, scope: str | None = None) -> None:
        if self._global or (scope and scope in self._scoped):
            raise ProtoHalted("kill switch engaged" + (f" ({scope})" if scope else " (global)"))


class SandboxedExecutor:
    """In-process capability scoping (production: replace with microVM)."""

    def __init__(self, allowed: set[str] | None = None, max_bytes: int = 1_000_000):
        self.allowed = allowed or {"read", "compute"}
        self.max_bytes = max_bytes

    def run(self, fn: Callable, *args, capabilities: set[str] | None = None, **kwargs) -> Any:
        caps = capabilities or set()
        if not caps.issubset(self.allowed):
            raise PermissionError(f"capabilities {caps - self.allowed} not allowed")
        result = fn(*args, **kwargs)
        if isinstance(result, (str, bytes)) and len(result) > self.max_bytes:
            raise ValueError("result exceeds size limit")
        return result
