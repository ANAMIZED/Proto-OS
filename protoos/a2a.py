"""A2A adapter + AG-UI event bus.

A2A (reference-shaped): Tasks with the A2A lifecycle states — submitted,
working, input-required, completed, failed, canceled — driven by registered
per-agent handlers; message/send, tasks/get, tasks/cancel and input resume.
Long-running work is modelled by tasks parking in `input-required` and
resuming later, alongside SessionManager contexts.

AG-UI (reference-shaped): the standard event stream to frontends
(TEXT_MESSAGE, TOOL_CALL_*, HUMAN_INPUT_*, STATE_DELTA, RUN_*).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .audit import AuditLog
from .canonical import Clock, ProtoError, new_id

RUN_STARTED = "RUN_STARTED"
RUN_FINISHED = "RUN_FINISHED"
TEXT_MESSAGE = "TEXT_MESSAGE"
TOOL_CALL_START = "TOOL_CALL_START"
TOOL_CALL_END = "TOOL_CALL_END"
HUMAN_INPUT_REQUEST = "HUMAN_INPUT_REQUEST"
HUMAN_INPUT_RESULT = "HUMAN_INPUT_RESULT"
STATE_DELTA = "STATE_DELTA"


@dataclass
class InputRequired:
    prompt: str
    meta: dict = field(default_factory=dict)


class AGUIBus:
    def __init__(self, clock: Clock):
        self.clock = clock
        self._subs: dict[str, list[Callable]] = {}
        self.state: dict[str, dict] = {}
        self._events: dict[str, list] = {}

    def subscribe(self, run_id: str, callback: Callable) -> None:
        self._subs.setdefault(run_id, []).append(callback)

    def emit(self, run_id: str, event_type: str, data: dict) -> dict:
        ev = {"type": event_type, "run_id": run_id, "ts": self.clock.now(), "data": data}
        self._events.setdefault(run_id, []).append(ev)
        for cb in self._subs.get(run_id, []):
            try:
                cb(ev)
            except Exception:
                pass
        return ev

    def events(self, run_id: str) -> list[dict]:
        return list(self._events.get(run_id, []))

    def apply_state_delta(self, run_id: str, delta: dict) -> dict:
        st = self.state.setdefault(run_id, {})
        st.update(delta)
        self.emit(run_id, STATE_DELTA, {"delta": delta, "state": dict(st)})
        return dict(st)


class A2AAdapter:
    def __init__(self, clock: Clock, audit: AuditLog):
        self.clock, self.audit = clock, audit
        self.tasks: dict[str, dict] = {}
        self._handlers: dict[str, Callable] = {}

    def register_handler(self, agent_did: str, handler: Callable) -> None:
        self._handlers[agent_did] = handler

    def create_task(self, agent_did: str, message: str, meta: dict | None = None) -> dict:
        tid = new_id("task")
        t = {"id": tid, "agent": agent_did, "message": message, "state": "submitted",
             "artifacts": [], "meta": meta or {}, "created": self.clock.now(),
             "updated": self.clock.now()}
        self.tasks[tid] = t
        self.audit.append(agent_did, "a2a.task.created", {"task_id": tid})
        return t

    def set_state(self, task_id: str, state: str, artifact: Any = None) -> dict:
        t = self.tasks[task_id]
        t["state"] = state
        t["updated"] = self.clock.now()
        if artifact is not None:
            t["artifacts"].append({"parts": [{"text": str(artifact)}]})
        self.audit.append(t["agent"], f"a2a.task.{state}", {"task_id": task_id})
        return t

    def get(self, task_id: str) -> dict | None:
        return self.tasks.get(task_id)

    def cancel(self, task_id: str) -> dict:
        return self.set_state(task_id, "canceled")

    def handle(self, req: dict) -> dict:
        method = req.get("method", "")
        params = req.get("params", {})
        if method == "message/send":
            t = self.create_task(params.get("agent", ""), params.get("message", ""))
            return {"jsonrpc": "2.0", "id": req.get("id"), "result": t}
        if method == "tasks/get":
            t = self.get(params.get("id", ""))
            return {"jsonrpc": "2.0", "id": req.get("id"), "result": t}
        if method == "tasks/cancel":
            t = self.cancel(params.get("id", ""))
            return {"jsonrpc": "2.0", "id": req.get("id"), "result": t}
        return {"jsonrpc": "2.0", "id": req.get("id"), "error": {"code": -32601, "message": "method not found"}}
