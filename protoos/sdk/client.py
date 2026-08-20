"""Minimal in-process / loopback SDK client.

For local use the client simply wraps a live ProtoOS instance.
A future remote transport can swap the transport without changing callers.
"""
from __future__ import annotations

from typing import Any

from ..core import ProtoOS, PendingApproval
from ..commerce import Catalog


class ProtoOSClient:
    """High-level SDK surface for agent builders."""

    def __init__(self, os: ProtoOS | None = None):
        self.os = os or ProtoOS()

    def create_user(self, name: str):
        return self.os.create_user(name)

    def create_agent(self, name: str, description: str, handler=None, cost: dict | None = None):
        return self.os.create_agent(name, description, handler=handler, cost=cost)

    def discover(self, query: str, k: int = 5, max_cost: float | None = None):
        return self.os.discover(query, k=k, max_cost=max_cost)

    def call_tool(self, agent_did: str, tool: str, arguments: dict, budget_id: str | None = None):
        return self.os.call_tool(agent_did, tool, arguments, budget_id=budget_id)

    def delegate(self, from_did: str, to_did: str, message: str, budget_id: str | None = None):
        return self.os.delegate(from_did, to_did, message, budget_id=budget_id)

    def purchase(self, buyer_did: str, catalog: Catalog, items: list,
                 intent_text: str, max_amount: float, budget_id: str,
                 categories: list | None = None) -> Any:
        return self.os.purchase(buyer_did, catalog, items, intent_text=intent_text,
                                max_amount=max_amount, budget_id=budget_id,
                                categories=categories)

    def approve(self, approval_id: str, actor_did: str, approved: bool = True):
        return self.os.approve(approval_id, actor_did, approved)

    def verify_integrity(self) -> dict:
        return self.os.verify_integrity()

    def export(self) -> dict:
        return self.os.export()
