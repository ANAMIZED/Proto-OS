"""Shared primitives: ids, clocks, errors, canonical JSON.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def cjson(obj: Any) -> str:
    """Canonical JSON (sorted keys, no whitespace) for hashing/signing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


class Clock:
    def now(self) -> float:
        return time.time()


class FixedClock(Clock):
    def __init__(self, t: float = 1_700_000_000.0):
        self._t = t

    def now(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


class ProtoError(Exception):
    pass


class PolicyDenied(ProtoError):
    def __init__(self, action: str, reason: str = "denied"):
        self.action, self.reason = action, reason
        super().__init__(f"policy denied {action}: {reason}")


class BudgetExceeded(ProtoError):
    def __init__(self, budget_id: str, reason: str = "exceeded"):
        self.budget_id, self.reason = budget_id, reason
        super().__init__(f"budget {budget_id}: {reason}")


class ProtoHalted(ProtoError):
    def __init__(self, reason: str = "kill switch engaged"):
        super().__init__(reason)


class RateLimited(ProtoError):
    pass


class MandateInvalid(ProtoError):
    pass
