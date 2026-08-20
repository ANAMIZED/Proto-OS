"""Constellation graph: structure, deterministic layout, exports."""
import math
import unittest

from protoos.graph import (build_demo_world, build_graph, layout, to_dot,
                           to_json, to_svg, DEFAULT_INCLUDE, EDGE_KINDS,
                           NODE_TYPES)


class GraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.os_, cls.refs = build_demo_world()
        cls.g = build_graph(cls.os_)

    def counts(self, g=None):
        g = g or self.g
        by = {}
        for n in g["nodes"]:
            by[n["type"]] = by.get(n["type"], 0) + 1
        return by

    def test_node_population(self):
        c = self.counts()
        self.assertEqual(c["id"], 6)       # org, ana, shop, 2 agents, proto svc? no: +?  (see refs)
        self.assertEqual(c["bud"], 5)
        self.assertEqual(c["srv"], 1)
        self.assertEqual(c["tool"], 2)
        self.assertEqual(c["mnd"], 15)     # 5 chains x intent/cart/payment
        self.assertEqual(c["rcp"], 3)      # tool x402, cable traditional, hdp x402
        self.assertEqual(c["task"], 1)
        self.assertEqual(c["appr"], 1)     # the parked lamp purchase
        self.assertTrue(set(c) <= set(NODE_TYPES))

    def test_edges_reference_existing_nodes(self):
        keys = {n["key"] for n in self.g["nodes"]}
        for e in self.g["edges"]:
            self.assertIn(e["a"], keys)
            self.assertIn(e["b"], keys)
            self.assertIn(e["kind"], EDGE_KINDS)

    def test_edge_kind_vocabulary(self):
        kinds = {e["kind"] for e in self.g["edges"]}
        self.assertEqual(kinds, set(EDGE_KINDS))  # every kind exercised

    def test_delegation_edges_from_budget_slices(self):
        ana = self.refs["ana"].did
        vc = {(e["a"], e["b"]) for e in self.g["edges"] if e["kind"] == "vc"}
        self.assertIn((ana, self.refs["shopper"].did), vc)
        self.assertIn((ana, self.refs["research"].did), vc)

    def test_layout_deterministic_and_finite(self):
        p1 = layout(self.g, seed=7)
        p2 = layout(self.g, seed=7)
        self.assertEqual(p1, p2)
        for x, y in p1.values():
            self.assertTrue(math.isfinite(x) and math.isfinite(y))
        xs = [p[0] for p in p1.values()]
        self.assertGreater(max(xs) - min(xs), 120.0)
        self.assertNotEqual(p1, layout(self.g, seed=8))

    def test_include_filter(self):
        g = build_graph(self.os_, include=frozenset())
        c = self.counts(g)
        for t in ("mnd", "rcp", "task", "tool", "srv"):
            self.assertNotIn(t, c)
        self.assertIn("id", c)
        self.assertIn("bud", c)
        self.assertIn("appr", c)  # approvals always shown
        keys = {n["key"] for n in g["nodes"]}
        for e in g["edges"]:
            self.assertIn(e["a"], keys)
            self.assertIn(e["b"], keys)

    def test_exports_wellformed(self):
        pos = layout(self.g, seed=7)
        js = to_json(self.g, pos)
        self.assertIn('"positions"', js)
        dot = to_dot(self.g)
        self.assertTrue(dot.startswith("digraph"))
        self.assertEqual(dot.count("->"), len(self.g["edges"]))
        svg = to_svg(self.g, pos)
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("</svg>", svg)
        self.assertEqual(svg.count("<line"), len(self.g["edges"]))

    def test_budget_fill_reflects_spend(self):
        buds = {n["key"]: n for n in self.g["nodes"] if n["type"] == "bud"}
        b_ana = self.refs["budgets"][1]
        self.assertGreater(buds[b_ana.id]["spent"], 100.0)  # 129 + roll-ups

    def test_default_include_constant(self):
        self.assertEqual(DEFAULT_INCLUDE,
                         frozenset({"mandates", "receipts", "tasks", "tools"}))


if __name__ == "__main__":
    unittest.main()
