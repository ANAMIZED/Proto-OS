"""Constellation: the live object graph of a ProtoOS world.

Mirrors the web console's Constellation view: nodes are principals, budgets,
MCP servers/tools, AP2 mandates, receipts, tasks, and pending approvals;
edges are structure, ownership, delegation, mandate chains, and money flow.

Exports: JSON (nodes/edges/positions), Graphviz DOT, and a standalone SVG
snapshot rendered in the ledger-room palette. The force layout is a pure,
seeded function, so identical worlds produce identical constellations.
"""
from __future__ import annotations

import json
import math
import random
from xml.sax.saxutils import escape as _x

NODE_TYPES = ("id", "bud", "srv", "tool", "mnd", "rcp", "task", "appr")
EDGE_KINDS = ("struct", "own", "vc", "chain", "money")
DEFAULT_INCLUDE = frozenset({"mandates", "receipts", "tasks", "tools"})

def build_graph(os_, include: frozenset = DEFAULT_INCLUDE) -> dict:
    """Derive the constellation from a live ProtoOS instance."""
    nodes: list[dict] = []
    edges: list[dict] = []
    seen: set[str] = set()

    def add(**n):
        k = n["key"]
        if k in seen:
            return
        seen.add(k)
        nodes.append(n)

    def link(a, b, kind):
        if a and b and a != b:
            edges.append({"a": a, "b": b, "kind": kind})

    idents = dict(getattr(getattr(os_, "ids", None), "_identities", {}) or {})
    for ident in idents.values():
        add(key=ident.did, type="id", sub=getattr(ident, "kind", ""),
            label=getattr(ident, "name", ident.did[-8:]))

    budgets = dict(getattr(getattr(os_, "wallet", None), "budgets", {}) or {})
    for b in budgets.values():
        spent = 0.0
        try:
            spent = os_.wallet.spent(b.id)
        except Exception:
            pass
        add(key=b.id, type="bud", label=f"budget {b.id[-4:]}",
            limit=getattr(b, "limit_total", None), spent=round(float(spent), 2))
        if getattr(b, "parent", None):
            link(b.id, b.parent, "struct")
        if getattr(b, "owner", None) in idents:
            link(b.owner, b.id, "own")

    if "tools" in include:
        servers = {}
        try:
            servers = dict(os_.mcp.servers()) if callable(getattr(os_.mcp, "servers", None)) else dict(getattr(os_.mcp, "servers", {}) or {})
        except Exception:
            servers = dict(getattr(os_.mcp, "_servers", {}) or {})
        for prefix, srv in servers.items():
            skey = f"srv:{prefix}"
            add(key=skey, type="srv", label=str(prefix))
            tools = getattr(srv, "tools", {}) or {}
            if callable(tools):
                tools = tools()
            for tname in tools:
                tkey = f"tool:{prefix}.{tname}"
                add(key=tkey, type="tool", label=str(tname))
                link(skey, tkey, "struct")

    if "mandates" in include:
        mstore = getattr(getattr(os_, "policy", None), "mandates", None) or getattr(os_, "mandates", None)
        mandates = {}
        if mstore is not None:
            try:
                mandates = dict(getattr(mstore, "_mandates", {}) or getattr(mstore, "all", lambda: {})())
            except Exception:
                pass
        for mid, m in (mandates.items() if isinstance(mandates, dict) else []):
            add(key=mid, type="mnd", label=f"mandate {str(mid)[-4:]}")
            owner = getattr(m, "principal", None) or getattr(m, "owner", None)
            if owner:
                link(owner, mid, "vc")
            parent = getattr(m, "parent", None)
            if parent:
                link(mid, parent, "chain")

    if "receipts" in include:
        receipts = {}
        try:
            receipts = dict(getattr(os_.wallet, "receipts", {}) or {})
        except Exception:
            pass
        for rid, r in (receipts.items() if isinstance(receipts, dict) else []):
            add(key=rid, type="rcp", label=f"rcp {str(rid)[-4:]}",
                amount=getattr(r, "amount", None))
            budget = getattr(r, "budget_id", None) or getattr(r, "budget", None)
            if budget:
                link(rid, budget, "money")

    if "tasks" in include:
        tasks = {}
        try:
            tg = getattr(os_, "tasks", None) or getattr(getattr(os_, "runtime", None), "tasks", None)
            tasks = dict(getattr(tg, "_tasks", {}) or {})
        except Exception:
            pass
        for tid, t in (tasks.items() if isinstance(tasks, dict) else []):
            add(key=tid, type="task", label=getattr(t, "name", f"task {str(tid)[-4:]}"))

    pending = getattr(os_, "pending", None) or getattr(getattr(os_, "core", None), "pending", None)
    if pending:
        try:
            for p in (pending.values() if hasattr(pending, "values") else pending):
                pid = getattr(p, "id", None) or str(id(p))
                add(key=pid, type="appr", label="pending")
        except Exception:
            pass

    return {"nodes": nodes, "edges": edges}


def layout(graph: dict, iterations: int = 300, seed: int = 7) -> dict:
    """Seeded force-directed layout. Returns {key: (x, y)} in [-1, 1]."""
    random.seed(seed)
    nodes = {n["key"]: n for n in graph["nodes"]}
    keys = list(nodes)
    if not keys:
        return {}
    pos = {k: (random.uniform(-1, 1), random.uniform(-1, 1)) for k in keys}
    # adjacency
    adj: dict[str, list[str]] = {k: [] for k in keys}
    for e in graph["edges"]:
        a, b = e["a"], e["b"]
        if a in adj and b in adj:
            adj[a].append(b)
            adj[b].append(a)
    for _ in range(iterations):
        force = {k: [0.0, 0.0] for k in keys}
        # repulsion
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                dx = pos[a][0] - pos[b][0]
                dy = pos[a][1] - pos[b][1]
                dist2 = dx * dx + dy * dy + 0.01
                dist = math.sqrt(dist2)
                f = 0.05 / dist2
                force[a][0] += f * dx / dist
                force[a][1] += f * dy / dist
                force[b][0] -= f * dx / dist
                force[b][1] -= f * dy / dist
        # attraction
        for a, neigh in adj.items():
            for b in neigh:
                dx = pos[b][0] - pos[a][0]
                dy = pos[b][1] - pos[a][1]
                force[a][0] += 0.02 * dx
                force[a][1] += 0.02 * dy
        for k in keys:
            x = pos[k][0] + max(-0.1, min(0.1, force[k][0]))
            y = pos[k][1] + max(-0.1, min(0.1, force[k][1]))
            pos[k] = (max(-1.0, min(1.0, x)), max(-1.0, min(1.0, y)))
    return pos


def to_json(graph: dict, pos: dict | None = None) -> str:
    return json.dumps({
        "nodes": graph["nodes"],
        "edges": graph["edges"],
        "pos": {k: list(v) for k, v in (pos or {}).items()},
    }, indent=2)


def to_dot(graph: dict) -> str:
    lines = ["digraph G {", "  rankdir=LR;", "  node [shape=box, style=rounded];"]
    for n in graph["nodes"]:
        label = _x(str(n.get("label", n["key"])))
        lines.append(f'  "{n["key"]}" [label="{label}"];')
    for e in graph["edges"]:
        lines.append(f'  "{e["a"]}" -> "{e["b"]}" [label="{e["kind"]}"];')
    lines.append("}")
    return "\n".join(lines)


def _node_svg(n: dict, x: float, y: float) -> str:
    colors = {
        "id": "#2F5D50", "bud": "#4A7C59", "srv": "#3D5A80",
        "tool": "#98C1D9", "mnd": "#EE6C4D", "rcp": "#E0FBFC",
        "task": "#293241", "appr": "#F4A261",
    }
    fill = colors.get(n.get("type", ""), "#5A665C")
    label = _x(str(n.get("label", n["key"])[:16]))
    return (
        f'<g transform="translate({x:.1f},{y:.1f})">' 
        f'<circle r="14" fill="{fill}" stroke="#1B1B1B" stroke-width="1.2"/>'
        f'<text y="28" text-anchor="middle" font-size="10" fill="#E8EDE9">{label}</text>'
        f'</g>'
    )


def to_svg(graph: dict, pos: dict, width: int = 900, height: int = 620) -> str:
    def P(k):
        x, y = pos.get(k, (0.0, 0.0))
        return  width / 2 + x * (width * 0.4), height / 2 + y * (height * 0.4)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<rect width="100%" height="100%" fill="#1A1F1C"/>',
        f'<desc>Proto constellation: {len(graph["nodes"])} nodes, '
        f'{len(graph["edges"])} edges</desc>',
    ]
    for e in graph["edges"]:
        ax, ay = P(e["a"])
        bx, by = P(e["b"])
        parts.append(
            f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
            f'stroke="#5A665C" stroke-width="1.2" opacity="0.7"/>'
        )
    for n in graph["nodes"]:
        x, y = P(n["key"])
        parts.append(_node_svg(n, x, y))
    parts.append("</svg>")
    return "".join(parts)


def build_demo_world():
    """Minimal world for standalone constellation demos / tests."""
    from .core import ProtoOS
    from .canonical import FixedClock
    os_ = ProtoOS(clock=FixedClock(1_700_000_000.0))
    # create a couple of identities and a budget so the graph is non-empty
    try:
        alice = os_.create_user("alice", kind="human")
        bob = os_.create_user("bob", kind="agent")
        os_.wallet.create_budget(owner=alice.did, limit_total=100.0, label="ops")
    except Exception:
        pass
    return os_, None


def main(argv: list[str]) -> int:
    from pathlib import Path
    out = Path(argv[1]) if len(argv) > 1 else Path("constellation_out")
    out.mkdir(parents=True, exist_ok=True)
    os_, _ = build_demo_world()
    g = build_graph(os_)
    pos = layout(g)
    (out / "constellation.json").write_text(to_json(g, pos))
    (out / "constellation.dot").write_text(to_dot(g))
    (out / "constellation.svg").write_text(to_svg(g, pos))
    print(f"constellation: {len(g['nodes'])} nodes, {len(g['edges'])} edges"
          f" -> {out}/constellation.{{json,dot,svg}}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys
    sys.exit(main(sys.argv))
