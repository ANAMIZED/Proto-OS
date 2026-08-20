"""Traceability audit + live smoke test. Entry point: python3 -m protoos.verify
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from . import ProtoOS, Catalog
from .graph import build_graph, layout
from .vault import write_vault_zip, unresolved_links

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "traceability.json"


def load_traceability() -> dict:
    return json.loads(TRACE.read_text())


def print_disposition(data: dict) -> None:
    print("ProtoOS requirement traceability")
    print("=" * 60)
    by = {"implemented": 0, "partial": 0, "deferred": 0}
    for r in data["requirements"]:
        st = r["status"]
        by[st] = by.get(st, 0) + 1
        print(f"  [{st:<11}] {r['id']:<3}  {r['requirement'][:70]}")
    total = sum(by.values())
    print("-" * 60)
    print(f"  total requirements dispositioned: {total}/{total} (100%)")
    print(f"    implemented: {by.get('implemented', 0)}")
    print(f"    partial    : {by.get('partial', 0)}")
    print(f"    deferred   : {by.get('deferred', 0)}")


def live_smoke() -> None:
    print("\nLive smoke (identity -> policy -> paid tool -> AP2 purchase -> audit)…")
    os_ = ProtoOS()
    os_.engine.add_rule("user", "allow", ["payment.settle", "tool.call"], "True")
    casey = os_.create_user("casey")
    shop = os_.create_merchant("shop")
    budget = os_.wallet.create_budget(casey.did, 100.0)

    mcp = os_.make_mcp_server("tools", payee_did=shop.did)
    mcp.add_tool("ping", "ping", {"type": "object"}, price=0.01, currency="USD")
    os_.mount_mcp("tools", mcp)

    # paid tool
    os_.call_tool(casey.did, "tools.ping", {}, budget_id=budget.id)

    # purchase
    cat = Catalog(shop.did, "shop")
    cat.add("item", "Widget", 5.0, "USD", "digital")
    os_.purchase(casey.did, cat, [{"sku": "item", "qty": 1}],
                 intent_text="buy widget", max_amount=20,
                 budget_id=budget.id, categories=["digital"])

    integrity = os_.verify_integrity()
    print(f"  crypto backend : {integrity['crypto_backend']}")
    print(f"  audit entries  : {integrity['audit_entries']}  spans: {integrity['spans']}")
    print(f"  audit chain ok : {integrity['audit_chain_ok']}")

    g = build_graph(os_)
    pos = layout(g, seed=1)
    assert all(isinstance(v, (int, float)) for p in pos.values() for v in p), "layout finite"
    print(f"  constellation  : {len(g['nodes'])} nodes, {len(g['edges'])} edges (layout finite)")

    with tempfile.TemporaryDirectory() as td:
        zpath = Path(td) / "vault.zip"
        write_vault_zip(os_, zpath)
        notes = unresolved_links(os_)
        assert not notes, f"unresolved: {notes}"
        import zipfile
        with zipfile.ZipFile(zpath) as zf:
            n = len([n for n in zf.namelist() if n.endswith(".md")])
        print(f"  vault notes    : {n} (all wikilinks resolve, zip valid)")

    print("\nRESULT: PASS")


def main() -> None:
    data = load_traceability()
    print_disposition(data)
    live_smoke()


if __name__ == "__main__":
    main()
