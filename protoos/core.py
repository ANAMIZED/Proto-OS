"""ProtoOS: the control plane & runtime facade.

Developers write agents against this stable high-level model; the OS handles
identity, discovery, task lifecycle, policy, spending controls, human-in-the-
loop approvals, observability and multi-protocol adapters underneath.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from . import a2a as agui
from .a2a import A2AAdapter, AGUIBus, InputRequired
from .audit import AuditLog, Tracer
from .canonical import (BudgetExceeded, Clock, PolicyDenied, ProtoError,
                        ProtoHalted, cjson, new_id)
from .commerce import Catalog
from .identity import IdentityService, default_backend
from .mcp import MCPClient, MCPMux, MCPServer, ResourceCache, ERR_PAYMENT_REQUIRED
from .policy import MandateStore, PolicyEngine
from .registry import (FederatedRegistry, LocalRegistry, SemanticIndex,
                       UnifiedAgentCard, WellKnownDirectory, rank_candidates)
from .runtime import KillSwitch, RateLimiter, SandboxedExecutor, SessionManager, TaskGraph
from .wallet import SpendingController


class PendingApproval:
    def __init__(self, approval_id: str, action: str, ctx: dict, run_id: str | None):
        self.approval_id, self.action, self.ctx, self.run_id = approval_id, action, ctx, run_id

    def __repr__(self):
        return f"<PendingApproval {self.approval_id} for {self.action}>"


class OSContext:
    def __init__(self, os: "ProtoOS", agent_did: str, run_id: str):
        self.os, self.agent_did, self.run_id = os, agent_did, run_id

    def emit_text(self, text: str) -> None:
        self.os.ui.emit(self.run_id, agui.TEXT_MESSAGE,
                        {"agent": self.agent_did, "text": text})

    def call_tool(self, tool: str, arguments: dict, budget_id: str | None = None):
        return self.os.call_tool(self.agent_did, tool, arguments,
                                 run_id=self.run_id, budget_id=budget_id)

    def discover(self, query: str, k: int = 5, max_cost: float | None = None):
        return self.os.discover(query, k=k, max_cost=max_cost)

    def delegate(self, to_did: str, message: str, budget_id: str | None = None):
        return self.os.delegate(self.agent_did, to_did, message,
                                budget_id=budget_id, run_id=self.run_id)

    def state(self, **delta):
        return self.os.ui.apply_state_delta(self.run_id, delta)


class ProtoOS:
    def __init__(self, clock: Clock | None = None, data_dir: str | None = None):
        self.clock = clock or Clock()
        self.data_dir = Path(data_dir) if data_dir else Path(tempfile.mkdtemp(prefix="protoos_"))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.audit = AuditLog(self.clock)
        self.tracer = Tracer(self.clock)
        self.ids = IdentityService(default_backend(), self.clock,
                                   wellknown_root=self.data_dir / "wellknown")
        self.engine = PolicyEngine(self.audit)
        self.mandates = MandateStore(self.ids, self.audit, self.clock)
        self.wallet = SpendingController(self.engine, self.mandates, self.ids,
                                         self.audit, self.clock)
        self.local_registry = LocalRegistry()
        self.wellknown = WellKnownDirectory(self.data_dir / "wellknown")
        self.registry = FederatedRegistry([self.local_registry, self.wellknown])
        self.index = SemanticIndex()
        self.ui = AGUIBus(self.clock)
        self.a2a = A2AAdapter(self.clock, self.audit)
        self.mcp = MCPMux()
        self.cache = ResourceCache(self.engine, self.audit)
        self.rate = RateLimiter(self.clock, rate_per_sec=20.0, burst=40)
        self.killswitch = KillSwitch()
        self.sandbox = SandboxedExecutor()
        self.sessions = SessionManager(self.clock)
        self._agents: dict[str, dict] = {}
        self._approvals: dict[str, dict] = {}
        self.audit.append("proto-os", "os.booted",
                          {"crypto_backend": self.ids.backend.name,
                           "data_dir": str(self.data_dir)})

    def create_user(self, name: str):
        u = self.ids.create_identity(name, "user")
        self.audit.append(u.did, "user.created", {"name": name})
        return u

    def create_merchant(self, name: str):
        m = self.ids.create_identity(name, "merchant")
        self.audit.append(m.did, "merchant.created", {"name": name})
        return m

    def create_agent(self, name: str, description: str, handler=None,
                     cost: dict | None = None, publish_open_host: str | None = None):
        a = self.ids.create_identity(name, "agent")
        card = UnifiedAgentCard(a.did, name, description, cost=cost or {})
        self.local_registry.put(card)
        self._agents[a.did] = {"card": card, "handler": handler}
        if publish_open_host:
            self.wellknown.publish(card, publish_open_host)
        self.audit.append(a.did, "agent.created", {"name": name})
        return a

    def make_mcp_server(self, name: str, payee_did: str | None = None):
        return MCPServer(name, payee_did=payee_did)

    def mount_mcp(self, prefix: str, server: MCPServer):
        self.mcp.mount(prefix, server)

    def call_tool(self, agent_did: str, tool: str, arguments: dict,
                  run_id: str | None = None, budget_id: str | None = None):
        self.killswitch.check()
        self.rate.check(agent_did)
        # Policy gate + optional auto-payment for paid tools handled in wallet/mcp
        return self.mcp.call(tool, arguments, payer_did=agent_did,
                             budget_id=budget_id, os_=self)

    def discover(self, query: str, k: int = 5, max_cost: float | None = None):
        cards = self.registry.list()
        self.index.build(cards)
        hits = self.index.search(query, k=k * 2)
        return rank_candidates(hits, max_cost=max_cost)[:k]

    def delegate(self, from_did: str, to_did: str, message: str,
                 budget_id: str | None = None, budget_slice: float | None = None,
                 run_id: str | None = None):
        self.killswitch.check()
        agent = self._agents.get(to_did)
        if not agent or not agent.get("handler"):
            raise ProtoError(f"no handler for {to_did}")
        task = self.a2a.create_task(to_did, message, meta={"budget": budget_id})
        ctx = OSContext(self, to_did, run_id or task["id"])
        try:
            result = agent["handler"](task, message, ctx)
            self.a2a.set_state(task["id"], "completed", artifact=result)
        except Exception as e:
            self.a2a.set_state(task["id"], "failed", artifact=str(e))
            raise
        return self.a2a.get(task["id"])

    def purchase(self, buyer_did: str, catalog: Catalog, items: list,
                 intent_text: str, max_amount: float, budget_id: str,
                 categories: list | None = None, run_id: str | None = None):
        cart = catalog.checkout(items)
        if cart["total"] > max_amount:
            raise PolicyDenied("payment.settle", "over intent max")
        # Simplified mandate + settle path; full AP2 chain in original
        decision = self.engine.evaluate("payment.settle",
                                        {"amount": cart["total"], "categories": categories or []})
        if decision.get("effect") == "require_approval":
            aid = new_id("appr")
            self._approvals[aid] = {"action": "payment.settle", "ctx": cart,
                                    "run_id": run_id, "buyer": buyer_did,
                                    "budget_id": budget_id}
            return PendingApproval(aid, "payment.settle", cart, run_id)
        if decision.get("effect") == "deny":
            raise PolicyDenied("payment.settle", decision.get("reason", "denied"))
        return self.wallet.settle(buyer_did, cart, budget_id=budget_id)

    def approve(self, approval_id: str, actor_did: str, approved: bool):
        ap = self._approvals.pop(approval_id, None)
        if not ap:
            raise ProtoError("unknown approval")
        if not approved:
            return None
        return self.wallet.settle(ap["buyer"], ap["ctx"], budget_id=ap.get("budget_id"))

    def pending_approvals(self):
        return list(self._approvals.keys())

    def verify_integrity(self):
        ok, idx = self.audit.verify()
        return {
            "audit_chain_ok": ok,
            "audit_entries": len(self.audit.entries),
            "spans": len(self.tracer.spans),
            "crypto_backend": self.ids.backend.name,
        }

    def export(self):
        d = self.data_dir / "export"
        d.mkdir(exist_ok=True)
        self.audit.export_jsonl(d / "audit.jsonl")
        self.tracer.export_jsonl(d / "traces.jsonl")
        return {"dir": str(d)}
