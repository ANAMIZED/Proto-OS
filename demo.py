#!/usr/bin/env python3
"""ProtoOS end-to-end demo: one scenario touching every subsystem.

Run:  python3 demo.py
"""
from protoos import Catalog, PendingApproval, ProtoHalted, ProtoOS

os_ = ProtoOS()
print(f"== ProtoOS booted (crypto backend: {os_.ids.backend.name}) ==\n")

# Four-layer policy stack ----------------------------------------------------
os_.engine.add_rule("platform", "deny", ["payment.settle"], "amount > 1000",
                    description="platform hard cap")
os_.engine.add_rule("org", "require_approval", ["payment.settle"],
                    "50 < amount <= 200", description="human approves large spend")
os_.engine.add_rule("user", "allow", ["payment.settle"], "amount <= 200")
os_.engine.add_rule("user", "allow", ["delegate"])

# People, merchants, budgets --------------------------------------------------
casey = os_.create_user("casey")
shop = os_.create_merchant("ebook-shop")
budget = os_.wallet.create_budget(casey.did, 500.0, window=(300.0, 86400),
                                  categories_allow=["digital", "tool"])

catalog = Catalog(shop.did, "ebook-shop")
catalog.add("bk1", "Distributed Systems 101", 10.00, "USD", "digital")
catalog.add("bk2", "Agents in Production", 60.00, "USD", "digital")

# MCP tools (one free, one x402-paid) -----------------------------------------
srv = os_.make_mcp_server("util", payee_did=shop.did)
srv.add_tool("echo", "echo", {"type": "object",
                              "properties": {"t": {"type": "string"}}},
             lambda t="": {"echo": t})
srv.add_tool("premium", "paid research lookup",
             {"type": "object", "properties": {"q": {"type": "string"}}},
             lambda q="": {"answer": f"summary about {q}"}, price=0.10)
os_.mount_mcp("util", srv)

# Agents + open (ANP-style) publication ----------------------------------------
def researcher(task, msg, ctx):
    ctx.emit_text(f"researching '{msg}'…")
    out = ctx.call_tool("util.premium", {"q": msg}, budget_id=task.meta["budget"])
    ctx.state(progress="complete")
    return out["structuredContent"]["answer"]

worker = os_.create_agent("researcher", "paid research lookups on any topic",
                          handler=researcher, cost={"per_task": 0.25},
                          publish_open_host="researcher.agents.local")
boss = os_.create_agent("supervisor", "delegates research and buys books",
                        cost={"per_task": 0.0})

# Live AG-UI stream to this "terminal client" ----------------------------------
def show(ev):
    data = {k: v for k, v in ev["data"].items() if k != "ctx"}
    print(f"  [AG-UI] {ev['type']:<22} {data}")

# 1) Discovery ---------------------------------------------------------------
print("1) discover('paid research on any topic', max_cost=$1)")
for card in os_.discover("paid research on any topic", k=3, max_cost=1.0):
    print(f"   -> {card.name}  cost/task=${card.cost.get('per_task', 0):.2f}  {card.did[:26]}…")

# 2) Delegation with a budget slice -> paid tool via x402 ----------------------
print("\n2) supervisor delegates to researcher with a $1.00 budget slice")
task = os_.delegate(boss.did, worker.did, "unified agent protocols",
                    budget_id=budget.id, budget_slice=1.00)
print(f"   task {task.id[:14]}… state={task.state}")
print(f"   artifact: {task.artifacts[0]['parts'][0]['text']}")
print(f"   budget spent so far: ${os_.wallet.spent(budget.id):.2f}")

# 3) Small purchase: full AP2 chain, auto-settled on x402 ----------------------
print("\n3) buy 2x 'Distributed Systems 101' ($20) — auto-allowed")
os_.ui.subscribe("run-small", show)
r = os_.purchase(casey.did, catalog, [{"sku": "bk1", "qty": 2}],
                 "buy two intro ebooks", max_amount=100, budget_id=budget.id,
                 categories=["digital"], run_id="run-small")
print(f"   receipt {r.receipt_id[:14]}… ${r.amount} via {r.rail} [{r.status}]")

# 4) Large purchase: policy demands a human -----------------------------------
print("\n4) buy 2x 'Agents in Production' ($120) — needs human approval")
os_.ui.subscribe("run-big", show)
pending = os_.purchase(casey.did, catalog, [{"sku": "bk2", "qty": 2}],
                       "buy the pricey book twice", max_amount=200,
                       budget_id=budget.id, categories=["digital"], run_id="run-big")
assert isinstance(pending, PendingApproval)
print(f"   … casey approves {pending.approval_id[:14]}…")
r2 = os_.approve(pending.approval_id, casey.did, True)
print(f"   receipt {r2.receipt_id[:14]}… ${r2.amount} via {r2.rail} [{r2.status}]")

# 5) Kill switch --------------------------------------------------------------
print("\n5) engage global kill switch, try a tool call")
os_.killswitch.engage()
try:
    os_.call_tool(worker.did, "util.echo", {"t": "hi"})
except ProtoHalted as e:
    print(f"   halted as expected: {e}")
os_.killswitch.release()

# 6) Ledger, audit chain, traces ------------------------------------------------
print("\n6) ledger:")
for e in os_.wallet.ledger:
    print(f"   ${e['amount']:<6} {e['category']:<8} rail={e['rail']}")
summary = os_.verify_integrity()
out = os_.export()
print(f"\n== integrity: audit_chain_ok={summary['audit_chain_ok']} "
      f"entries={summary['audit_entries']} spans={summary['spans']} ==")
print(f"== exported audit.jsonl + traces.jsonl to {out['dir']} ==")
print("\nlast 5 audit actions:",
      [e["action"] for e in os_.audit.entries[-5:]])

# 7) Constellation + Obsidian vault --------------------------------------------
from pathlib import Path

from protoos.graph import build_graph, layout, to_svg
from protoos.vault import write_vault_zip

g = build_graph(os_)
pos = layout(g)
Path(out["dir"], "constellation.svg").write_text(to_svg(g, pos))
n_notes = write_vault_zip(os_, Path(out["dir"], "obsidian-vault.zip"))
print(f"\n7) constellation: {len(g['nodes'])} nodes / {len(g['edges'])} edges"
      f" -> constellation.svg; vault: {n_notes} notes -> obsidian-vault.zip")
