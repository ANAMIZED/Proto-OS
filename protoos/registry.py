"""Discovery & Registry.

  - UnifiedAgentCard: a JSON-LD-flavoured superset of A2A Agent Cards, MCP
    server manifests, UCP merchant profiles and ANP/LMOS descriptions.
  - Backends: LocalRegistry (Kubernetes-CRD-shaped, resourceVersion'd),
    WellKnownDirectory (open-internet /.well-known publication, ANP mode,
    simulated on the local filesystem), FederatedRegistry (AGNTCY-like union).
  - SemanticIndex: pure-Python TF-IDF vector search over capabilities with an
    optional policy/constraint filter ("find agents that can do X under Y").
  - rank_candidates: AGP-inspired cost-aware selection.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .canonical import cjson, new_id

CONTEXT = "https://protoos.dev/context/v1"


@dataclass
class UnifiedAgentCard:
    did: str
    name: str
    description: str
    skills: list[dict] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    products: list[dict] = field(default_factory=list)
    endpoints: dict = field(default_factory=dict)
    protocols: list[str] = field(default_factory=list)
    cost: dict = field(default_factory=dict)
    labels: dict = field(default_factory=dict)
    context: str = CONTEXT

    def to_json(self) -> dict:
        return {
            "@context": self.context, "did": self.did, "name": self.name,
            "description": self.description, "skills": self.skills, "tools": self.tools,
            "products": self.products, "endpoints": self.endpoints,
            "protocols": self.protocols, "cost": self.cost, "labels": self.labels,
        }

    @classmethod
    def from_json(cls, d: dict) -> "UnifiedAgentCard":
        return cls(did=d["did"], name=d["name"], description=d.get("description", ""),
                   skills=d.get("skills", []), tools=d.get("tools", []),
                   products=d.get("products", []), endpoints=d.get("endpoints", {}),
                   protocols=d.get("protocols", []), cost=d.get("cost", {}),
                   labels=d.get("labels", {}), context=d.get("@context", CONTEXT))

    def text(self) -> str:
        parts = [self.name, self.description]
        for s in self.skills:
            parts += [s.get("name", ""), s.get("description", "")]
        parts += self.tools
        return " ".join(p for p in parts if p)


class LocalRegistry:
    def __init__(self):
        self._cards: dict[str, UnifiedAgentCard] = {}
        self._rv = 0

    def put(self, card: UnifiedAgentCard) -> dict:
        self._rv += 1
        self._cards[card.did] = card
        return {"did": card.did, "resourceVersion": str(self._rv)}

    def get(self, did: str) -> UnifiedAgentCard | None:
        return self._cards.get(did)

    def list(self) -> list[UnifiedAgentCard]:
        return list(self._cards.values())

    def to_crd(self, card: UnifiedAgentCard) -> dict:
        return {
            "apiVersion": "proto.dev/v1", "kind": "AgentCard",
            "metadata": {"name": card.name.lower().replace(" ", "-"), "resourceVersion": "1"},
            "spec": card.to_json(),
        }


class WellKnownDirectory:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def publish(self, card: UnifiedAgentCard, host: str) -> Path:
        d = self.root / host
        d.mkdir(parents=True, exist_ok=True)
        p = d / "agent.json"
        p.write_text(json.dumps(card.to_json(), indent=2))
        return p

    def resolve(self, host: str) -> UnifiedAgentCard | None:
        p = self.root / host / "agent.json"
        if not p.exists():
            return None
        return UnifiedAgentCard.from_json(json.loads(p.read_text()))


class FederatedRegistry:
    def __init__(self, backends: list):
        self.backends = backends

    def put(self, card: UnifiedAgentCard):
        for b in self.backends:
            if hasattr(b, "put"):
                b.put(card)

    def list(self) -> list[UnifiedAgentCard]:
        seen = set()
        out = []
        for b in self.backends:
            for c in b.list() if hasattr(b, "list") else []:
                if c.did not in seen:
                    seen.add(c.did)
                    out.append(c)
        return out

    def get(self, did: str) -> UnifiedAgentCard | None:
        for b in self.backends:
            if hasattr(b, "get"):
                c = b.get(did)
                if c:
                    return c
        return None


_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class SemanticIndex:
    def __init__(self):
        self._cards: list[UnifiedAgentCard] = []
        self._vecs: list[dict[str, float]] = []
        self._idf: dict[str, float] = {}

    def build(self, cards: list[UnifiedAgentCard]) -> None:
        self._cards = list(cards)
        docs = [_tokens(c.text()) for c in self._cards]
        df = Counter()
        for d in docs:
            df.update(set(d))
        n = max(len(docs), 1)
        self._idf = {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}
        self._vecs = []
        for d in docs:
            tf = Counter(d)
            vec = {t: tf[t] * self._idf.get(t, 1.0) for t in tf}
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            self._vecs.append({t: v / norm for t, v in vec.items()})

    def search(self, query: str, k: int = 5, where=None) -> list[tuple[UnifiedAgentCard, float]]:
        q = Counter(_tokens(query))
        qvec = {t: q[t] * self._idf.get(t, 1.0) for t in q}
        qnorm = math.sqrt(sum(v * v for v in qvec.values())) or 1.0
        qvec = {t: v / qnorm for t, v in qvec.items()}
        scored = []
        for card, vec in zip(self._cards, self._vecs):
            if where is not None and not where(card):
                continue
            s = sum(qvec[t] * vec.get(t, 0.0) for t in qvec)
            if s > 0:
                scored.append((card, round(s, 6)))
        scored.sort(key=lambda x: -x[1])
        return scored[:k]


def rank_candidates(candidates: list[tuple[UnifiedAgentCard, float]],
                    max_cost: float | None = None,
                    cost_weight: float = 0.5) -> list[UnifiedAgentCard]:
    pool = []
    costs = []
    for card, score in candidates:
        cost = float(card.cost.get("per_task", 0.0))
        if max_cost is not None and cost > max_cost:
            continue
        pool.append((card, score, cost))
        costs.append(cost)
    if not pool:
        return []
    cmax = max(costs) or 1.0
    pool.sort(key=lambda t: -(t[1] - cost_weight * (t[2] / cmax)))
    return [c for c, _, _ in pool]
