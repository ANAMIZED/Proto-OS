"""UCP/ACP-style commerce adapter: product discovery and checkout flows.

A merchant publishes a catalog; agents search it and check out, producing a
cart that the merchant signs into an AP2 Cart Mandate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .canonical import new_id


@dataclass
class Product:
    sku: str
    name: str
    price: float
    currency: str = "USD"
    category: str = "general"
    meta: dict = field(default_factory=dict)


class Catalog:
    def __init__(self, merchant_did: str, name: str):
        self.merchant_did = merchant_did
        self.name = name
        self.products: dict[str, Product] = {}

    def add(self, sku: str, name: str, price: float, currency: str = "USD",
            category: str = "general", **meta) -> Product:
        p = Product(sku, name, price, currency, category, meta)
        self.products[sku] = p
        return p

    def search(self, query: str = "", category: str | None = None) -> list[Product]:
        q = query.lower()
        out = []
        for p in self.products.values():
            if category and p.category != category:
                continue
            if q and q not in p.name.lower() and q not in p.sku.lower():
                continue
            out.append(p)
        return out

    def checkout(self, items: list[dict]) -> dict:
        """items: [{sku, qty}, ...] -> cart dict ready for Cart Mandate."""
        lines = []
        total = 0.0
        currency = "USD"
        for it in items:
            p = self.products[it["sku"]]
            qty = int(it.get("qty", 1))
            line_total = round(p.price * qty, 6)
            lines.append({"sku": p.sku, "name": p.name, "qty": qty,
                          "unit_price": p.price, "line_total": line_total,
                          "category": p.category})
            total += line_total
            currency = p.currency
        return {
            "cart_id": new_id("cart"),
            "merchant": self.merchant_did,
            "lines": lines,
            "total": round(total, 6),
            "currency": currency,
        }
