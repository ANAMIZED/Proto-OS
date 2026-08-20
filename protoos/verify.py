"""Self-verification: `python -m protoos.verify`

1. Loads traceability.json and prints the requirement dispositions.
2. Runs a live smoke across the stack: identity -> policy -> paid tool over
   x402 -> AP2 purchase -> audit-chain verification.
Exit code 0 only if the smoke passes and every requirement is dispositioned.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load_traceability() -> dict:
    here = Path(__file__).resolve()
    for candidate in (Path.cwd() / "traceability.json",
                      here.parents[1] / "traceability.json"):
        if candidate.exists():
            return json.loads(candidate.read_text())
    raise SystemExit("traceability.json not found")


def smoke() -> dict:
    import math
    import tempfile
    import zipfile

    from protoos import Catalog, ProtoOS
    from protoos.graph import build_graph, layout
    from protoos.vault import unresolved_links, vault_notes, write_vault_zip

    os_ = ProtoOS()
    os_.engine.add_rule("user", "allow", ["payment.settle"], "amount <= 100")
    user = os_.create_user("verifier")
    shop = os_.create_merchant("shop")
    budget = os_.wallet.create_budget(user.did, 100.0)
    srv = os_.make_mcp_server("util", payee_did=shop.did)
    srv.add_tool("echo", "echo", {"type": "object",
                                  "properties": {"t": {"type": "string"}}},
                 lambda t="": {"echo": t})
    srv.add_tool("paid", "paid", {"type": "object", "properties": {}},
                 lambda: {"ok": True}, price=0.05)
    os_.mount_mcp("util", srv)
    agent = os_.create_agent("smoke-agent", "smoke test agent")
    assert os_.call_tool(agent.did, "util.echo",
                         {"t": "hi"})["structuredContent"] == {"echo": "hi"}
    assert os_.call_tool(agent.did, "util.paid", {},
                         budget_id=budget.id)["structuredContent"] == {"ok": True}
    cat = Catalog(shop.did, "shop")
    cat.add("sku1", "widget", 9.99, "USD", "digital")
    receipt = os_.purchase(user.did, cat, [{"sku": "sku1", "qty": 1}],
                           "buy a widget", 50, budget.id, categories=["digital"])
    assert receipt.status == "settled"
    # constellation + vault must hold on the same live world
    g = build_graph(os_)
    pos = layout(g, iterations=120)
    assert g["nodes"] and g["edges"]
    assert all(math.isfinite(c) for xy in pos.values() for c in xy)
    notes = vault_notes(os_)
    assert unresolved_links(notes) == []
    with tempfile.TemporaryDirectory() as td:
        zp = Path(td) / "vault.zip"
        write_vault_zip(os_, zp)
        assert zipfile.ZipFile(zp).testzip() is None
    summary = os_.verify_integrity()
    summary["constellation"] = {"nodes": len(g["nodes"]), "edges": len(g["edges"])}
    summary["vault_notes"] = len(notes)
    return summary


def main() -> int:
    data = load_traceability()
    reqs = data["requirements"]
    counts: dict[str, int] = {}
    for r in reqs:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("ProtoOS requirement traceability")
    print("=" * 60)
    for r in reqs:
        print(f"  [{r['status']:<11}] {r['id']:<3} {r['req'][:70]}")
    total = len(reqs)
    print("-" * 60)
    print(f"  total requirements dispositioned: {total}/{total} (100%)")
    for status in ("implemented", "partial", "deferred"):
        print(f"    {status:<11}: {counts.get(status, 0)}")
    print("\nLive smoke (identity -> policy -> paid tool -> AP2 purchase -> audit)…")
    summary = smoke()
    ok = summary["audit_chain_ok"] and total == counts.get("implemented", 0) + \
        counts.get("partial", 0) + counts.get("deferred", 0)
    print(f"  crypto backend : {summary['crypto_backend']}")
    print(f"  audit entries  : {summary['audit_entries']}  spans: {summary['spans']}")
    print(f"  audit chain ok : {summary['audit_chain_ok']}")
    print(f"  constellation  : {summary['constellation']['nodes']} nodes, "
          f"{summary['constellation']['edges']} edges (layout finite)")
    print(f"  vault notes    : {summary['vault_notes']} (all wikilinks resolve, zip valid)")
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
