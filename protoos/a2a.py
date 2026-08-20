"""A2A adapter + AG-UI event bus.

A2A (reference-shaped): Tasks with the A2A lifecycle states — submitted,
working, input-required, completed, failed, canceled — driven by registered
per-agent handlers; message/send, tasks/get, tasks/cancel and input resume.
Long-running work is modelled by tasks parking in input-required and later
resuming. AG-UI is the standard event stream to frontends.
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
        self._state: dict[str, dict] = {}
        self._history: dict[str, list] = {}

    def subscribe(self, run_id: str, callback: Callable) -> None:
        self._subs.setdefault(run_id, []).append(callback)

    def emit(self, run_id: str, event_type: str, data: dict) -> dict:
        ev = {"type": event_type, "run_id": run_id, "ts": self.clock.now(), "data": data}
        self._history.setdefault(run_id, []).append(ev)
        for cb in self._subs.get(run_id, []):
            try:
                cb(ev)
            except Exception:
                pass
        return ev

    def apply_state_delta(self, run_id: str, delta: dict) -> dict:
        st = self._state.setdefault(run_id, {})
        st.update(delta)
        self.emit(run_id, STATE_DELTA, {"delta": delta, "state": dict(st)})
        return dict(st)

    def history(self, run_id: str) -> list:
        return list(self._history.get(run_id, []))


class A2AAdapter:
    def __init__(self, clock: Clock, audit: AuditLog):
        self.clock, self.audit = clock, audit
        self.tasks: dict[str, dict] = {}

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
