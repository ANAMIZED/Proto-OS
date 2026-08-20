"""A2A task lifecycle + AG-UI event bus.

States: submitted / working / input-required / completed / failed / canceled.
AG-UI events stream over the bus (and over SSE via httpapi).
"""
from __future__ import annotations

import json
from typing import Any, Callable, Iterator

from .canonical import Clock, new_id
from .audit import AuditLog

# AG-UI event types (stable strings)
RUN_STARTED = "RUN_STARTED"
RUN_FINISHED = "RUN_FINISHED"
TEXT_MESSAGE = "TEXT_MESSAGE_CONTENT"
STATE_DELTA = "STATE_DELTA"
TOOL_CALL_START = "TOOL_CALL_START"
TOOL_CALL_END = "TOOL_CALL_END"
HUMAN_INPUT_REQUEST = "HUMAN_INPUT_REQUEST"
HUMAN_INPUT_RESULT = "HUMAN_INPUT_RESULT"


class InputRequired(Exception):
    """Raised by a handler to park a task waiting for human/agent input."""
    def __init__(self, prompt: str, meta: dict | None = None):
        self.prompt = prompt
        self.meta = meta or {}
        super().__init__(prompt)


class AGUIBus:
    """In-process multi-subscriber event bus + shared state."""

    def __init__(self, clock: Clock):
        self.clock = clock
        self._events: dict[str, list[dict]] = {}
        self._state: dict[str, dict] = {}
        self._subscribers: dict[str, list] = {}

    def start_run(self, run_id: str) -> None:
        self._events[run_id] = []
        self._state[run_id] = {}
        self.emit(run_id, RUN_STARTED, {"runId": run_id})

    def emit(self, run_id: str, event_type: str, payload: dict) -> None:
        ev = {
            "type": event_type,
            "ts": self.clock.now(),
            "runId": run_id,
            **payload,
        }
        self._events.setdefault(run_id, []).append(ev)
        for cb in self._subscribers.get(run_id, []):
            try:
                cb(ev)
            except Exception:
                pass

    def apply_state_delta(self, run_id: str, delta: dict) -> dict:
        st = self._state.setdefault(run_id, {})
        st.update(delta)
        self.emit(run_id, STATE_DELTA, {"delta": delta, "state": dict(st)})
        return st

    def subscribe(self, run_id: str) -> Iterator[dict]:
        # Snapshot + live
        for ev in list(self._events.get(run_id, [])):
            yield ev
        # In real SSE the connection stays open; here we just drain what exists

    def finish_run(self, run_id: str) -> None:
        self.emit(run_id, RUN_FINISHED, {"runId": run_id})


class A2AAdapter:
    """A2A-shaped task store + JSON-RPC surface."""

    def __init__(self, clock: Clock, audit: AuditLog):
        self.clock = clock
        self.audit = audit
        self._tasks: dict[str, dict] = {}

    def create_task(self, agent_did: str, message: str, meta: dict | None = None) -> dict:
        tid = new_id("task")
        task = {
            "id": tid,
            "agent": agent_did,
            "message": message,
            "state": "submitted",
            "created": self.clock.now(),
            "updated": self.clock.now(),
            "artifact": None,
            "meta": meta or {},
        }
        self._tasks[tid] = task
        self.audit.append(agent_did, "a2a.task.created", {"taskId": tid})
        return task

    def set_state(self, task_id: str, state: str, artifact: Any = None) -> dict:
        t = self._tasks[task_id]
        t["state"] = state
        t["updated"] = self.clock.now()
        if artifact is not None:
            t["artifact"] = artifact
        self.audit.append(t["agent"], f"a2a.task.{state}", {"taskId": task_id})
        return t

    def get(self, task_id: str) -> dict | None:
        return self._tasks.get(task_id)

    def handle_jsonrpc(self, req: dict) -> dict:
        method = req.get("method")
        params = req.get("params") or {}
        id_ = req.get("id")
        try:
            if method == "tasks/send":
                t = self.create_task(params.get("agent"), params.get("message", ""), params.get("meta"))
                return {"jsonrpc": "2.0", "id": id_, "result": t}
            if method == "tasks/get":
                t = self.get(params.get("id"))
                return {"jsonrpc": "2.0", "id": id_, "result": t}
            return {"jsonrpc": "2.0", "id": id_, "error": {"code": -32601, "message": "method not found"}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": id_, "error": {"code": -32000, "message": str(e)}}
