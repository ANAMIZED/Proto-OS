#!/usr/bin/env python3
"""End-to-end ProtoOS demo: discovery, delegation, purchases (with human approval),
kill-switch, constellation + Obsidian vault export.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from protoos import ProtoOS, Catalog
from protoos.graph import build_graph, layout, to_svg
from protoos.vault import write_vault_zip


def main() -> None:
    os_ = ProtoOS()
    print(f"== ProtoOS booted (crypto backend: {os_.ids.backend.name}) ==\n")

    # Policy: small payments auto, large require human
    os_.engine.add_rule("user", "allow", ["payment.settle"], "amount <= 50")
    os_.engine.add_rule("org", "require_approval", ["payment.settle"], "amount > 50")
    os_.engine.add_rule("platform", "allow", ["tool.call", "delegate"], "True")

    casey = os_.create_user("casey")
    shop = os_.create_merchant("shop")
    budget = os_.wallet.create_budget(casey.did, 500.0, window=(300.0, 86400))

    # Agents
    def researcher_handler(task, message, ctx):
        ctx.emit_text("researching…")
        # paid tool under budget
        result = ctx.call_tool("research.search", {"q": message}, budget_id=budget.id)
        return {"summary": f"summary about {message}", "raw": result}

    def supervisor_handler(task, message, ctx):
        hits = ctx.discover("paid research on any topic", max_cost=1.0)
        print("1) discover('paid research on any topic', max_cost=$1)")
        for h in hits:
            print(f"   -> {h.name}  cost/task=${h.cost.get('per_task', 0):.2f}  {h.did[:30]}…")
        researcher = next(h for h in hits if "research" in h.name.lower())
        print("\n2) supervisor delegates to researcher with a $1.00 budget slice")
        slice_id = os_.wallet.create_budget(casey.did, 1.0, parent=budget.id).id
        task = ctx.delegate(researcher.did, message, budget_id=slice_id)
        print(f"   task {task['id'][:12]}… state={task['state']}")
        print(f"   artifact: {task.get('artifact', {}).get('summary', task.get('artifact'))}")
        print(f"   budget spent so far: ${os_.wallet.spent(budget.id):.2f}")
        return task

    researcher = os_.create_agent(
        "researcher", "paid research on any topic",
        handler=researcher_handler, cost={"per_task": 0.25}
    )
    supervisor = os_.create_agent(
        "supervisor", "coordinates research",
        handler=supervisor_handler, cost={"per_task": 0.0}
    )

    # MCP paid tool
    mcp = os_.make_mcp_server("research", payee_did=shop.did)
    mcp.add_tool("search", "search the literature", {"type": "object"},
                 price=0.10, currency="USD")
    os_.mount_mcp("research", mcp)

    # Run supervisor
    run_id = "demo-run"
    os_.ui.start_run(run_id)
    supervisor_handler(None, "unified agent protocols", type("C", (), {"os": os_, "agent_did": supervisor.did, "run_id": run_id, "emit_text": lambda t: os_.ui.emit(run_id, "TEXT_MESSAGE", {"text": t}), "call_tool": lambda *a, **k: os_.call_tool(supervisor.did, *a, run_id=run_id, **k), "discover": os_.discover, "delegate": lambda *a, **k: os_.delegate(supervisor.did, *a, run_id=run_id, **k)})())

    # Catalog + purchases
    catalog = Catalog(shop.did, "shop")
    catalog.add("bk1", "Distributed Systems 101", 10.00, "USD", "digital")
    catalog.add("bk2", "Agents in Production", 60.00, "USD", "digital")

    print("\n3) buy 2x 'Distributed Systems 101' ($20) — auto-allowed")
    receipt = os_.purchase(casey.did, catalog, [{"sku": "bk1", "qty": 2}],
                           intent_text="buy two intro ebooks", max_amount=100,
                           budget_id=budget.id, categories=["digital"], run_id=run_id)
    if hasattr(receipt, "approval_id"):
        print("   (unexpected approval)")
    else:
        print(f"   receipt {receipt.id[:12]}… ${receipt.amount} via {receipt.rail} [{receipt.status}]")

    print("\n4) buy 2x 'Agents in Production' ($120) — needs human approval")
    pending = os_.purchase(casey.did, catalog, [{"sku": "bk2", "qty": 2}],
                           intent_text="buy advanced books", max_amount=200,
                           budget_id=budget.id, categories=["digital"], run_id=run_id)
    print(f"   … casey approves {pending.approval_id[:12]}…")
    receipt2 = os_.approve(pending.approval_id, casey.did, True)
    print(f"   receipt {receipt2.id[:12]}… ${receipt2.amount} via {receipt2.rail} [{receipt2.status}]")

    print("\n5) engage global kill switch, try a tool call")
    os_.killswitch.engage()
    try:
        os_.call_tool(casey.did, "research.search", {"q": "x"}, budget_id=budget.id)
    except Exception as e:
        print(f"   halted as expected: {e}")

    print("\n6) ledger:")
    for entry in os_.wallet.ledger():
        print(f"   ${entry['amount']:<6} {entry.get('category', ''):<8} rail={entry.get('rail')}")

    integrity = os_.verify_integrity()
    print(f"\n== integrity: audit_chain_ok={integrity['audit_chain_ok']} entries={integrity['audit_entries']} spans={integrity['spans']} ==")
    export = os_.export()
    print(f"== exported audit.jsonl + traces.jsonl to {export['dir']} ==")

    print("\nlast 5 audit actions:", [e["action"] for e in os_.audit.entries[-5:]])

    # Constellation + vault
    g = build_graph(os_)
    pos = layout(g, seed=42)
    out_dir = Path(tempfile.mkdtemp(prefix="protoos_demo_"))
    svg_path = out_dir / "constellation.svg"
    to_svg(g, pos, svg_path)
    vault_path = out_dir / "obsidian-vault.zip"
    write_vault_zip(os_, vault_path)
    print(f"\n7) constellation: {len(g['nodes'])} nodes / {len(g['edges'])} edges -> constellation.svg; vault: {len(list((out_dir / 'notes').glob('*.md') if (out_dir / 'notes').exists() else []))} notes -> obsidian-vault.zip")
    # actual note count from vault
    import zipfile
    with zipfile.ZipFile(vault_path) as zf:
        notes = [n for n in zf.namelist() if n.endswith(".md")]
    print(f"   (vault contains {len(notes)} markdown notes)")


if __name__ == "__main__":
    main()
