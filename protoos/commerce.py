"""UCP/ACP-style commerce adapter: product discovery and checkout flows.

A merchant publishes a catalog; agents search it and check out, producing a
cart that the merchant signs into an AP2 Cart Mandate via the MandateStore.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .canonical import ProtoError, new_id


@dataclass
class Product:
    sku: str
    title: str
    price: float
    currency: str
    category: str
    merchant: str
    stock: int = 1_000_000
    attrs: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return dict(self.__dict__)


class Catalog:
    def __init__(self, merchant_did: str, name: str):
        self.merchant = merchant_did
        self.name = name
        self._products: dict[str, Product] = {}

    def add(self, sku: str, title: str, price: float, currency: str, category: str,
            stock: int = 1_000_000, **attrs) -> Product:
        p = Product(sku, title, round(float(price), 2), currency, category,
                    self.merchant, stock, attrs)
        self._products[sku] = p
        return p

    def get(self, sku: str) -> Product:
        if sku not in self._products:
            raise ProtoError(f"catalog {self.name}: unknown sku {sku}")
        return self._products[sku]

    def search(self, query: str = "", category: str | None = None,
               max_price: float | None = None) -> list[Product]:
        q = query.lower()
        out = []
        for p in self._products.values():
            if q and q not in p.title.lower() and q not in p.category.lower():
                continue
            if category and p.category != category:
                continue
            if max_price is not None and p.price > max_price:
                continue
            out.append(p)
        return sorted(out, key=lambda p: p.price)

    def checkout(self, items: list[dict], currency: str | None = None) -> dict:
        """items: [{"sku": ..., "qty": n}] -> UCP-shaped cart dict."""
        lines, total, cur = [], 0.0, currency
        for it in items:
            p = self.get(it["sku"])
            qty = int(it.get("qty", 1))
            if qty < 1 or qty > p.stock:
                raise ProtoError(f"checkout: bad quantity for {p.sku}")
            if cur is None:
                cur = p.currency
            if p.currency != cur:
                raise ProtoError("checkout: mixed currencies in one cart")
            line_total = round(p.price * qty, 2)
            total = round(total + line_total, 2)
            lines.append({"sku": p.sku, "title": p.title, "qty": qty,
                          "unit_price": p.price, "line_total": line_total,
                          "category": p.category})
        return {"cart_id": new_id("cart"), "merchant": self.merchant,
                "items": lines, "total": total, "currency": cur or "USD",
                "status": "ready_for_payment"}
