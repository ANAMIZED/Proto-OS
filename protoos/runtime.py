"""Runtime primitives: rate limits, kill switches, sandboxed execution,
declarative task graphs and long-running sessions."""
from __future__ import annotations

from .canonical import Clock, ProtoError, ProtoHalted, RateLimited, new_id


class RateLimiter:
    """Token bucket per key."""

    def __init__(self, clock: Clock, rate_per_sec: float = 5.0, burst: int = 10):
        self.clock = clock
        self.rate, self.burst = rate_per_sec, burst
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_ts)

    def allow(self, key: str, cost: float = 1.0) -> bool:
        now = self.clock.now()
        tokens, last = self._buckets.get(key, (float(self.burst), now))
        tokens = min(self.burst, tokens + (now - last) * self.rate)
        if tokens >= cost:
            self._buckets[key] = (tokens - cost, now)
            return True
        self._buckets[key] = (tokens, now)
        return False

    def check(self, key: str, cost: float = 1.0) -> None:
        if not self.allow(key, cost):
            raise RateLimited(f"rate limit exceeded for {key}")


class KillSwitch:
    def __init__(self):
        self._global = False
        self._scoped: set[str] = set()

    def engage(self, scope: str = "global") -> None:
        if scope == "global":
            self._global = True
        else:
            self._scoped.add(scope)

    def release(self, scope: str = "global") -> None:
        if scope == "global":
            self._global = False
        else:
            self._scoped.discard(scope)

    def engaged(self, scope: str | None = None) -> bool:
        return self._global or (scope in self._scoped if scope else False)

    def check(self, scope: str | None = None) -> None:
        if self.engaged(scope):
            raise ProtoHalted(f"kill switch engaged ({'global' if self._global else scope})")


class SandboxedExecutor:
    """Capability-scoped tool execution: only whitelisted callables run, with
    argument size limits. In-process approximation of container sandboxing;
    real OS-level isolation is deferred to the production runtime."""

    def __init__(self, max_arg_bytes: int = 65536):
        self._allowed: dict[str, object] = {}
        self.max_arg_bytes = max_arg_bytes

    def grant(self, name: str, fn) -> None:
        self._allowed[name] = fn

    def run(self, name: str, **kwargs):
        if name not in self._allowed:
            raise ProtoError(f"sandbox: capability {name!r} not granted")
        import json as _json
        if len(_json.dumps(kwargs, default=str)) > self.max_arg_bytes:
            raise ProtoError("sandbox: arguments exceed size limit")
        return self._allowed[name](**kwargs)


class TaskGraph:
    """Declarative DAG of named steps with dependencies; runs topologically
    under tracer + kill-switch supervision."""

    def __init__(self, name: str = "graph"):
        self.name = name
        self._nodes: dict[str, tuple[object, list[str]]] = {}

    def add(self, name: str, fn, deps: list[str] | None = None) -> "TaskGraph":
        self._nodes[name] = (fn, list(deps or []))
        return self

    def run(self, tracer=None, killswitch: KillSwitch | None = None) -> dict:
        for n, (_, deps) in self._nodes.items():
            for d in deps:
                if d not in self._nodes:
                    raise ProtoError(f"task graph: unknown dependency {d!r} of {n!r}")
        done: dict[str, object] = {}
        remaining = dict(self._nodes)
        while remaining:
            ready = [n for n, (_, deps) in remaining.items() if all(d in done for d in deps)]
            if not ready:
                raise ProtoError("task graph: cycle detected")
            for n in ready:
                if killswitch:
                    killswitch.check()
                fn, deps = remaining.pop(n)
                inputs = {d: done[d] for d in deps}
                if tracer:
                    with tracer.span(f"graph:{self.name}:{n}", {"deps": deps}):
                        done[n] = fn(**inputs) if deps else fn()
                else:
                    done[n] = fn(**inputs) if deps else fn()
        return done


class SessionManager:
    """Long-running session contexts surviving across many task turns."""

    def __init__(self, clock: Clock):
        self.clock = clock
        self._sessions: dict[str, dict] = {}

    def create(self, owner: str, state: dict | None = None) -> str:
        sid = new_id("sess")
        self._sessions[sid] = {"owner": owner, "created": self.clock.now(),
                               "updated": self.clock.now(), "state": dict(state or {}),
                               "open": True}
        return sid

    def get(self, sid: str) -> dict:
        if sid not in self._sessions:
            raise ProtoError(f"unknown session {sid}")
        return self._sessions[sid]

    def update(self, sid: str, **delta) -> dict:
        s = self.get(sid)
        if not s["open"]:
            raise ProtoError(f"session {sid} is closed")
        s["state"].update(delta)
        s["updated"] = self.clock.now()
        return dict(s["state"])

    def close(self, sid: str) -> None:
        self.get(sid)["open"] = False
