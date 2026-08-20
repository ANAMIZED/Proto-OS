"""Wallet / Spending Controller + multi-rail settlement (x402, MPP, traditional)."""
from __future__ import annotations

from dataclasses import dataclass, field
from .audit import AuditLog
from .canonical import BudgetExceeded, Clock, ProtoError, new_id
from .identity import IdentityService
from .policy import MandateStore, PolicyEngine

@dataclass
class Budget:
    id: str
    owner: str
    limit_total: float
    spent_total: float = 0.0
    parent: str | None = None
    categories_allow: list[str] = field(default_factory=list)
    categories_deny: list[str] = field(default_factory=list)
    window: tuple[float, float] | None = None  # (amount, seconds)

@dataclass
class Receipt:
    receipt_id: str
    rail: str
    amount: float
    currency: str
    payer: str
    payee: str
    ts: float
    status: str = "settled"
    ref: str = ""
    meta: dict = field(default_factory=dict)
    def to_json(self):
        return {"receipt_id": self.receipt_id, "rail": self.rail, "amount": self.amount,
                "currency": self.currency, "payer": self.payer, "payee": self.payee,
                "ts": self.ts, "status": self.status, "ref": self.ref, "meta": self.meta}

class X402Rail:
    name = "x402"
    def __init__(self, ids, audit, clock):
        self.ids, self.audit, self.clock = ids, audit, clock
        self._nonces = set()
        self._receipts = {}
    def settle(self, payment: dict) -> Receipt:
        ch = payment.get("challenge", {})
        r = Receipt(new_id("rcpt"), self.name, ch.get("amount", 0), ch.get("currency", "USD"),
                    payment.get("payer", ""), ch.get("payee", ""), self.clock.now(),
                    ref=ch.get("resource", ""))
        self._receipts[r.receipt_id] = r
        self.audit.append("x402", "payment.settled", r.to_json())
        return r

class MPPRail:
    name = "mpp"
    def __init__(self, audit, clock):
        self.audit, self.clock = audit, clock
        self.sessions = {}
        self._receipts = {}
    def open_session(self, payer, payee, deposit, currency="USD"):
        sid = new_id("mppsess")
        self.sessions[sid] = {"payer": payer, "payee": payee, "balance": deposit}
        return {"session_id": sid}
    def charge(self, session_id, amount):
        s = self.sessions[session_id]
        if s["balance"] < amount: raise BudgetExceeded("mpp session")
        s["balance"] -= amount
        r = Receipt(new_id("rcpt"), self.name, amount, "USD", s["payer"], s["payee"], self.clock.now())
        self._receipts[r.receipt_id] = r
        return r

class TraditionalRail:
    name = "traditional"
    def __init__(self, audit, clock):
        self.audit, self.clock = audit, clock
        self._receipts = {}
    def settle(self, payer, payee, amount, currency="USD") -> Receipt:
        r = Receipt(new_id("rcpt"), self.name, amount, currency, payer, payee, self.clock.now())
        self._receipts[r.receipt_id] = r
        self.audit.append("traditional", "payment.settled", r.to_json())
        return r

class SpendingController:
    def __init__(self, engine, mandates, ids, audit, clock):
        self.engine, self.mandates, self.ids, self.audit, self.clock = engine, mandates, ids, audit, clock
        self.budgets: dict[str, Budget] = {}
        self.ledger = []
        self.x402 = X402Rail(ids, audit, clock)
        self.mpp = MPPRail(audit, clock)
        self.traditional = TraditionalRail(audit, clock)

    def create_budget(self, owner, limit, window=None, categories_allow=None, parent=None):
        b = Budget(new_id("bud"), owner, limit, window=window,
                   categories_allow=categories_allow or [], parent=parent)
        self.budgets[b.id] = b
        return b

    def spent(self, budget_id):
        b = self.budgets.get(budget_id)
        return b.spent_total if b else 0.0

    def check_budget(self, budget_id, amount, category=None):
        b = self.budgets.get(budget_id)
        if not b: raise BudgetExceeded("unknown budget")
        if b.spent_total + amount > b.limit_total + 1e-9:
            raise BudgetExceeded("over limit")
        if category and b.categories_allow and category not in b.categories_allow:
            raise BudgetExceeded("category not allowed")

    def settle(self, payer, cart, budget_id=None, rail="x402"):
        amount = cart.get("total", 0)
        if budget_id:
            self.check_budget(budget_id, amount)
            self.budgets[budget_id].spent_total += amount
        if rail == "x402":
            r = self.x402.settle({"challenge": {"amount": amount, "currency": cart.get("currency", "USD"),
                                               "payee": cart.get("merchant", ""), "resource": cart.get("cart_id", "")},
                                 "payer": payer})
        else:
            r = self.traditional.settle(payer, cart.get("merchant", ""), amount)
        self.ledger.append({"amount": amount, "category": "purchase", "rail": r.rail})
        return r
