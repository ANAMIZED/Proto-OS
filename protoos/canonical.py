"""Canonical encoding, hashing, identifiers, clock, and error types.

Provides the shared primitives used across the control plane:
- cjson: deterministic JSON serialization
- sha256_hex / b32 helpers
- new_id: unique ID generator
- Clock / FixedClock for deterministic testing
- ProtoError hierarchy (PolicyDenied, BudgetExceeded, MandateInvalid, etc.)
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from base64 import b32encode


def cjson(obj) -> str:
    """Canonical JSON: sorted keys, no whitespace, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def b32(data: bytes) -> str:
    return b32encode(data).decode("ascii").rstrip("=").lower()


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


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
    pass


class BudgetExceeded(ProtoError):
    pass


class MandateInvalid(ProtoError):
    pass


class ProtoHalted(ProtoError):
    pass


class RateLimited(ProtoError):
    pass
