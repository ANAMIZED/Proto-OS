"""Policy, Governance & Safety + AP2-style Mandates."""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from fnmatch import fnmatch

from .audit import AuditLog
from .canonical import Clock, MandateInvalid, ProtoError, cjson, new_id
from .identity import IdentityService

_ALLOWED_NODES = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub,
    ast.Compare, ast.Name, ast.Load, ast.Constant, ast.List, ast.Tuple,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
)

def safe_eval(expr: str, ctx: dict) -> bool:
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ProtoError(f"policy expression: disallowed syntax {type(node).__name__!r}")
    def ev(node):
        if isinstance(node, ast.Expression): return ev(node.body)
        if isinstance(node, ast.Constant): return node.value
        if isinstance(node, (ast.List, ast.Tuple)): return [ev(e) for e in node.elts]
        if isinstance(node, ast.Name):
            if node.id in ctx: return ctx[node.id]
            raise ProtoError(f"policy expression: unknown variable {node.id!r}")
        if isinstance(node, ast.UnaryOp):
            v = ev(node.operand)
            return (not v) if isinstance(node.op, ast.Not) else -v
        if isinstance(node, ast.BoolOp):
            vals = [ev(v) for v in node.values]
            return all(vals) if isinstance(node.op, ast.And) else any(vals)
        if isinstance(node, ast.Compare):
            left = ev(node.left)
            for op, comp in zip(node.ops, node.comparators):
                right = ev(comp)
                ok = (left == right if isinstance(op, ast.Eq) else
                      left != right if isinstance(op, ast.NotEq) else
                      left < right if isinstance(op, ast.Lt) else
                      left <= right if isinstance(op, ast.LtE) else
                      left > right if isinstance(op, ast.Gt) else
                      left >= right if isinstance(op, ast.GtE) else
                      left in right if isinstance(op, ast.In) else
                      left not in right if isinstance(op, ast.NotIn) else None)
                if ok is None: raise ProtoError("policy expression: unsupported comparator")
                if not ok: return False
                left = right
            return True
        raise ProtoError(f"policy expression: unsupported node {type(node).__name__!r}")
    return bool(ev(tree))

@dataclass
class Rule:
    layer: str
    effect: str
    actions: list[str]
    condition: str = "True"
    description: str = ""
    id: str = field(default_factory=lambda: new_id("rule"))

class PolicyEngine:
    LAYERS = ("platform", "legal", "org", "user")
    def __init__(self, audit: AuditLog):
        self.audit = audit
        self.rules: list[Rule] = []

    def add_rule(self, layer: str, effect: str, actions: list[str], condition: str = "True", description: str = ""):
        r = Rule(layer, effect, actions, condition, description)
        self.rules.append(r)
        return r

    def evaluate(self, action: str, ctx: dict) -> dict:
        matched = []
        for r in self.rules:
            if any(fnmatch(action, a) for a in r.actions):
                try:
                    if safe_eval(r.condition, ctx):
                        matched.append(r)
                except Exception:
                    pass
        # deny overrides
        for r in matched:
            if r.effect == "deny":
                self.audit.append("policy", "decision", {"action": action, "effect": "deny", "rule": r.id})
                return {"effect": "deny", "reason": r.description or r.condition, "rule_id": r.id}
        for r in matched:
            if r.effect == "require_approval":
                self.audit.append("policy", "decision", {"action": action, "effect": "require_approval", "rule": r.id})
                return {"effect": "require_approval", "rule_id": r.id}
        for r in matched:
            if r.effect == "allow":
                self.audit.append("policy", "decision", {"action": action, "effect": "allow", "rule": r.id})
                return {"effect": "allow", "rule_id": r.id}
        # default deny for sensitive
        if action.startswith("payment.") or action == "delegate":
            self.audit.append("policy", "decision", {"action": action, "effect": "deny", "rule": "default"})
            return {"effect": "deny", "reason": "default-deny"}
        return {"effect": "allow"}

class MandateStore:
    def __init__(self, ids: IdentityService, audit: AuditLog, clock: Clock):
        self.ids, self.audit, self.clock = ids, audit, clock
        self._mandates: dict[str, dict] = {}

    def store(self, m: dict) -> str:
        mid = m.get("id") or new_id("mnd")
        m["id"] = mid
        self._mandates[mid] = m
        self.audit.append("mandates", "mandate.stored", {"id": mid, "type": m.get("type")})
        return mid

    def verify_chain(self, intent_id: str, cart_id: str, payment_id: str) -> bool:
        # simplified chain check
        return intent_id in self._mandates and cart_id in self._mandates and payment_id in self._mandates
