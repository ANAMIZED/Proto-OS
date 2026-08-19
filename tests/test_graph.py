"""Constellation graph tests."""
import unittest
from protoos import ProtoOS
from protoos.graph import build_graph, layout, to_json, to_dot, to_svg, NODE_TYPES, EDGE_KINDS

class GraphTests(unittest.TestCase):
    def setUp(self):
        self.os = ProtoOS()
        u = self.os.create_user("u")
        self.os.wallet.create_budget(u.did, 100.0)

    def test_node_population(self):
        g = build_graph(self.os)
        types = {n["type"] for n in g["nodes"]}
        self.assertIn("id", types)
        self.assertIn("bud", types)

    def test_edge_kind_vocabulary(self):
        g = build_graph(self.os)
        for e in g["edges"]:
            self.assertIn(e["kind"], EDGE_KINDS)

    def test_layout_deterministic_and_finite(self):
        g = build_graph(self.os)
        p1 = layout(g, seed=42)
        p2 = layout(g, seed=42)
        self.assertEqual(p1, p2)
        for pos in p1.values():
            self.assertTrue(all(abs(x) < 1e6 for x in pos))

    def test_exports_wellformed(self):
        g = build_graph(self.os)
        pos = layout(g)
        j = to_json(g, pos)
        self.assertIn("nodes", j)
        d = to_dot(g, pos)
        self.assertIn("digraph", d)
        s = to_svg(g, pos)
        self.assertIn("<svg", s)

if __name__ == "__main__":
    unittest.main()
