"""Adapter surface tests (MCP, A2A, commerce, http)."""
import unittest
from protoos import ProtoOS, Catalog

class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.os = ProtoOS()
        self.user = self.os.create_user("u")
        self.shop = self.os.create_merchant("shop")
        self.budget = self.os.wallet.create_budget(self.user.did, 50.0)

    def test_mcp_echo(self):
        srv = self.os.make_mcp_server("util")
        srv.add_tool("echo", "echo", {"type": "object", "properties": {"t": {"type": "string"}}},
                     lambda t="": {"echo": t})
        self.os.mount_mcp("util", srv)
        agent = self.os.create_agent("a", "agent")
        out = self.os.call_tool(agent.did, "util.echo", {"t": "hi"})
        self.assertIn("echo", str(out))

    def test_catalog_checkout(self):
        cat = Catalog(self.shop.did, "shop")
        cat.add("sku1", "widget", 1.0, "USD", "digital")
        cart = cat.checkout([{"sku": "sku1", "qty": 1}])
        self.assertEqual(cart["total"], 1.0)

if __name__ == "__main__":
    unittest.main()
