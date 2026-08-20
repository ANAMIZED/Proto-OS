"""UCP/ACP-style catalog and checkout (reference-shaped).
"""
from __future__ import annotations

from .canonical import new_id


class Product:
    def __init__(self, sku: str, title: str, price: float, currency: str = "USD",
                 category: str = "general"):
        self.sku, self.title, self.price, self.currency, self.category = (
            sku, title, price, currency, category
        )

    def to_dict(self) -> dict:
        return {
            "sku": self.sku, "title": self.title, "price": self.price,
            "currency": self.currency, "category": self.category,
        }


class Catalog:
    def __init__(self, merchant_did: str, name: str):
        self.merchant_did, self.name = merchant_did, name
        self._products: dict[str, Product] = {}

    def add(self, sku: str, title: str, price: float, currency: str = "USD",
            category: str = "general") -> Product:
        p = Product(sku, title, price, currency, category)
        self._products[sku] = p
        return p

    def search(self, query: str = "") -> list[Product]:
        q = query.lower()
        return [p for p in self._products.values()
                if not q or q in p.title.lower() or q in p.sku.lower()]

    def checkout(self, items: list[dict]) -> dict:
        lines = []
        total = 0.0
        currency = "USD"
        categories = set()
        for it in items:
            p = self._products.get(it["sku"])
            if not p:
                raise ValueError(f"unknown sku {it['sku']}")
            qty = int(it.get("qty", 1))
            line_total = p.price * qty
            total += line_total
            currency = p.currency
            categories.add(p.category)
            lines.append({
                "sku": p.sku, "title": p.title, "qty": qty,
                "unit_price": p.price, "line_total": line_total,
                "category": p.category,
            })
        return {
            "id": new_id("cart"),
            "merchant": self.merchant_did,
            "lines": lines,
            "total": total,
            "currency": currency,
            "categories": sorted(categories),
        }
