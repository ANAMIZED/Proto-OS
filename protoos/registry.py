"""Discovery & registry: local (CRD-shaped), federated, well-known, semantic index.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from .canonical import new_id


class UnifiedAgentCard:
    """Superset of A2A cards, MCP manifests, UCP profiles, ANP descriptions."""

    def __init__(self, did: str, name: str, description: str = "",
                 capabilities: list[str] | None = None,
                 cost: dict | None = None,
                 endpoints: dict | None = None,
                 context: list[str] | None = None):
        self.did = did
        self.name = name
        self.description = description
        self.capabilities = capabilities or []
        self.cost = cost or {}
        self.endpoints = endpoints or {}
        self.context = context or ["https://www.w3.org/ns/did/v1"]

    def to_dict(self) -> dict:
        return {
            "@context": self.context,
            "did": self.did,
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "cost": self.cost,
            "endpoints": self.endpoints,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UnifiedAgentCard":
        return cls(
            d["did"], d.get("name", ""), d.get("description", ""),
            d.get("capabilities"), d.get("cost"), d.get("endpoints"),
            d.get("@context"),
        )


class LocalRegistry:
    """In-memory + CRD-shaped records (matches deploy/k8s/crds.yaml)."""

    def __init__(self):
        self._cards: dict[str, UnifiedAgentCard] = {}

    def put(self, card: UnifiedAgentCard) -> None:
        self._cards[card.did] = card

    def get(self, did: str) -> UnifiedAgentCard | None:
        return self._cards.get(did)

    def list(self) -> list[UnifiedAgentCard]:
        return list(self._cards.values())

    def to_crd(self, card: UnifiedAgentCard) -> dict:
        return {
            "apiVersion": "proto.dev/v1",
            "kind": "AgentCard",
            "metadata": {"name": card.name.replace(" ", "-").lower()},
            "spec": card.to_dict(),
        }


class WellKnownDirectory:
    """Publishes agent cards under a local well-known root (did:web / ANP style)."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def publish(self, card: UnifiedAgentCard, host: str) -> Path:
        d = self.root / host
        d.mkdir(parents=True, exist_ok=True)
        path = d / "agent.json"
        path.write_text(json.dumps(card.to_dict(), indent=2))
        return path

    def resolve(self, host: str) -> UnifiedAgentCard | None:
        path = self.root / host / "agent.json"
        if not path.exists():
            return None
        return UnifiedAgentCard.from_dict(json.loads(path.read_text()))

    def list(self) -> list[UnifiedAgentCard]:
        out = []
        for p in self.root.rglob("agent.json"):
            try:
                out.append(UnifiedAgentCard.from_dict(json.loads(p.read_text())))
            except Exception:
                pass
        return out


class FederatedRegistry:
    """Union of multiple backends with simple dedupe by did."""

    def __init__(self, backends: list):
        self.backends = backends

    def list(self) -> list[UnifiedAgentCard]:
        seen = set()
        out = []
        for b in self.backends:
            for c in b.list():
                if c.did not in seen:
                    seen.add(c.did)
                    out.append(c)
        return out

    def get(self, did: str) -> UnifiedAgentCard | None:
        for b in self.backends:
            c = b.get(did) if hasattr(b, "get") else None
            if c:
                return c
        return None


class SemanticIndex:
    """TF-IDF cosine over card text + optional where filter."""

    def __init__(self):
        self._cards: list[UnifiedAgentCard] = []
        self._tfidf: list[dict[str, float]] = []
        self._idf: dict[str, float] = {}

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def build(self, cards: list[UnifiedAgentCard]) -> None:
        self._cards = list(cards)
        docs = []
        for c in cards:
            text = f"{c.name} {c.description} {' '.join(c.capabilities)}"
            docs.append(Counter(self._tokenize(text)))
        df = Counter()
        for d in docs:
            for t in d:
                df[t] += 1
        n = max(len(docs), 1)
        self._idf = {t: math.log((n + 1) / (df[t] + 1)) + 1 for t in df}
        self._tfidf = []
        for d in docs:
            vec = {t: (cnt / sum(d.values())) * self._idf.get(t, 0) for t, cnt in d.items()}
            self._tfidf.append(vec)

    def search(self, query: str, k: int = 5, where: Callable | None = None) -> list[UnifiedAgentCard]:
        qtok = self._tokenize(query)
        if not qtok or not self._tfidf:
            return self._cards[:k]
        qvec = Counter(qtok)
        qnorm = math.sqrt(sum((c * self._idf.get(t, 0)) ** 2 for t, c in qvec.items())) or 1
        scores = []
        for i, vec in enumerate(self._tfidf):
            if where and not where(self._cards[i]):
                continue
            dot = sum(vec.get(t, 0) * c * self._idf.get(t, 0) for t, c in qvec.items())
            nrm = math.sqrt(sum(v ** 2 for v in vec.values())) or 1
            scores.append((dot / (qnorm * nrm), self._cards[i]))
        scores.sort(key=lambda x: -x[0])
        return [c for _, c in scores[:k]]


def rank_candidates(cards: list[UnifiedAgentCard], max_cost: float | None = None) -> list[UnifiedAgentCard]:
    """Cost-aware ranking (AGP-inspired)."""
    def cost_of(c):
        return float(c.cost.get("per_task", c.cost.get("per_call", 0)) or 0)
    filtered = [c for c in cards if max_cost is None or cost_of(c) <= max_cost]
    return sorted(filtered, key=cost_of)
