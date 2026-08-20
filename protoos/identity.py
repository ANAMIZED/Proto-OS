"""Identity & Trust layer.

Cryptographic identities (Ed25519 when cryptography is available; HMAC fallback),
DID-style identifiers, Verifiable Credentials, short-lived session tokens,
RFC 8693-style token exchange, enterprise IdP bridge stub.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os as _os
from dataclasses import dataclass, field
from pathlib import Path

from .canonical import Clock, ProtoError, b32, cjson, new_id, sha256_hex

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.hazmat.primitives import serialization
    _HAVE_ED25519 = True
except Exception:
    _HAVE_ED25519 = False


class KeyBackend:
    name = "abstract"
    def new_keypair(self): raise NotImplementedError
    def sign(self, private_handle, data: bytes) -> bytes: raise NotImplementedError
    def verify(self, public_bytes: bytes, signature: bytes, data: bytes) -> bool: raise NotImplementedError


class Ed25519Backend(KeyBackend):
    name = "ed25519"
    def new_keypair(self):
        priv = Ed25519PrivateKey.generate()
        pub = priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return priv, pub
    def sign(self, private_handle, data: bytes) -> bytes:
        return private_handle.sign(data)
    def verify(self, public_bytes: bytes, signature: bytes, data: bytes) -> bool:
        try:
            Ed25519PublicKey.from_public_bytes(public_bytes).verify(signature, data)
            return True
        except Exception:
            return False


class HMACBackend(KeyBackend):
    name = "hmac"
    def new_keypair(self):
        key = _os.urandom(32)
        return key, key
    def sign(self, private_handle, data: bytes) -> bytes:
        return hmac.new(private_handle, data, hashlib.sha256).digest()
    def verify(self, public_bytes: bytes, signature: bytes, data: bytes) -> bool:
        return hmac.compare_digest(self.sign(public_bytes, data), signature)


def default_backend() -> KeyBackend:
    return Ed25519Backend() if _HAVE_ED25519 else HMACBackend()


@dataclass
class Identity:
    did: str
    name: str
    kind: str
    public: bytes
    _private: object = field(repr=False)


class IdentityService:
    def __init__(self, backend: KeyBackend, clock: Clock, wellknown_root: Path | None = None):
        self.backend = backend
        self.clock = clock
        self.wellknown_root = Path(wellknown_root) if wellknown_root else None
        self._identities: dict[str, Identity] = {}
        self._tokens: dict[str, dict] = {}

    def create_identity(self, name: str, kind: str = "agent") -> Identity:
        priv, pub = self.backend.new_keypair()
        did = f"did:proto:{b32(pub)[:32]}"
        ident = Identity(did=did, name=name, kind=kind, public=pub, _private=priv)
        self._identities[did] = ident
        return ident

    def sign_as(self, did: str, body: dict) -> str:
        ident = self._identities[did]
        sig = self.backend.sign(ident._private, cjson(body).encode())
        return b32(sig)

    def verify_for(self, did: str, sig: str, body: dict) -> bool:
        ident = self._identities.get(did)
        if not ident:
            return False
        try:
            raw = __import__("base64").b32decode(sig.upper() + "=" * ((8 - len(sig) % 8) % 8))
            return self.backend.verify(ident.public, raw, cjson(body).encode())
        except Exception:
            return False

    def issue_token(self, did: str, audience: str, ttl: float = 3600) -> str:
        tid = new_id("tok")
        self._tokens[tid] = {"did": did, "aud": audience, "exp": self.clock.now() + ttl}
        return tid

    def exchange_token(self, token: str, act_as: str) -> str:
        t = self._tokens.get(token)
        if not t or t["exp"] < self.clock.now():
            raise ProtoError("invalid or expired token")
        return self.issue_token(act_as, t["aud"])


class EnterpriseIdPStub:
    def bridge_to_proto(self, assertion: dict, ids: IdentityService) -> str:
        sub = assertion.get("sub", "external")
        ident = ids.create_identity(sub, "user")
        return ids.issue_token(ident.did, "proto")
