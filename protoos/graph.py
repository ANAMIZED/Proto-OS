"""Constellation: the live object graph of a ProtoOS world."""
from __future__ import annotations

import json
import math
import random
from xml.sax.saxutils import escape as _x

NODE_TYPES = ("id", "bud", "srv", "tool", "mnd", "rcp", "task", "appr")
EDGE_KINDS = ("struct", "own", "vc", "chain", "money")
DEFAULT_INCLUDE = frozenset({"mandates", "receipts", "tasks", "tools"})

def build_graph(os_, include: frozenset = DEFAULT_INCLUDE) -> dict:
    nodes = []
    edges = []
    def add(**n): nodes.append(n)
    def link(a, b, kind): edges.append({"a": a, "b": b, "kind": kind})

    idents = dict(getattr(os_.ids, "_identities", {}))
    for ident in idents.values():
        add(key=ident.did, type="id", sub=ident.kind, label=ident.name)

    budgets = dict(getattr(os_.wallet, "budgets", {}))
    for b in budgets.values():
        spent = os_.wallet.spent(b.id)
        add(key=b.id, type="bud", label=f"budget {b.id[-4:]}", limit=b.limit_total, spent=round(spent, 2))
        if b.parent: link(b.id, b.parent, "struct")
        if b.owner in idents: link(b.owner, b.id, "own")

    if "tools" in include:
        for prefix, srv in getattr(os_.mcp, "servers", lambda: {})().items():
            skey = f"srv:{prefix}"
            add(key=skey, type="srv", label=prefix)
            for tname in getattr(srv, "tools", {}):
                tkey = f"tool:{prefix}.{tname}"
                add(key=tkey, type="tool", label=tname)
                link(skey, tkey, "struct")

    return {"nodes": nodes, "edges": edges}

def layout(graph, seed=42, iterations=100):
    random.seed(seed)
    nodes = {n["key"]: n for n in graph["nodes"]}
    pos = {k: (random.uniform(-1, 1), random.uniform(-1, 1)) for k in nodes}
    for _ in range(iterations):
        # simple force layout stub
        for k in pos:
            x, y = pos[k]
            pos[k] = (x * 0.99 + random.uniform(-0.01, 0.01), y * 0.99 + random.uniform(-0.01, 0.01))
    return pos

def to_json(graph, pos=None):
    return json.dumps({"nodes": graph["nodes"], "edges": graph["edges"], "pos": pos or {}}, indent=2)

def to_dot(graph, pos=None):
    lines = ["digraph G {"]
    for n in graph["nodes"]:
        lines.append(f'  "{n["key"]}" [label="{n.get("label", n["key"])}"];')
    for e in graph["edges"]:
        lines.append(f'  "{e["a"]}" -> "{e["b"]}" [label="{e["kind"]}"];')
    lines.append("}")
    return "\n".join(lines)

def to_svg(graph, pos=None):
    pos = pos or layout(graph)
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600">']
    for e in graph["edges"]:
        a, b = pos.get(e["a"], (0,0)), pos.get(e["b"], (0,0))
        parts.append(f'<line x1="{400+a[0]*200}" y1="{300+a[1]*200}" x2="{400+b[0]*200}" y2="{300+b[1]*200}" stroke="#5A665C"/>')
    for k, (x, y) in pos.items():
        parts.append(f'<circle cx="{400+x*200}" cy="{300+y*200}" r="8" fill="#2F5D50"/>')
    parts.append("</svg>")
    return "".join(parts)
