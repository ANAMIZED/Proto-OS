"""Canonical encoding, hashing, identifiers and clocks for ProtoOS."""
from __future__ import annotations

import base64
import hashlib
import json
import threading
import time
import uuid


def cjson(obj) -> str:
    """Deterministic canonical JSON used for all signing and hashing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def b32(data: bytes) -> str:
    return base64.b32encode(data).decode("ascii").rstrip("=").lower()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


class Clock:
    """Wall clock; injectable for deterministic tests."""

    def now(self) -> float:
        return time.time()


class FixedClock(Clock):
    def __init__(self, start: float = 1_700_000_000.0):
        self._t = float(start)
        self._lock = threading.Lock()

    def now(self) -> float:
        return self._t

    def advance(self, seconds: float) -> float:
        with self._lock:
            self._t += seconds
            return self._t


class ProtoError(Exception):
    """Base error for ProtoOS."""


class PolicyDenied(ProtoError):
    def __init__(self, action: str, reason: str, rule_id: str | None = None):
        super().__init__(f"policy denied '{action}': {reason}" + (f" (rule {rule_id})" if rule_id else ""))
        self.action, self.reason, self.rule_id = action, reason, rule_id


class ProtoHalted(ProtoError):
    """Raised when a kill switch is engaged."""


class RateLimited(ProtoError):
    pass


class MandateInvalid(ProtoError):
    pass


class BudgetExceeded(ProtoError):
    pass
