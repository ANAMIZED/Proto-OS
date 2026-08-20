"""End-to-end OS tests."""
import unittest
from protoos import ProtoOS, Catalog

class E2ETests(unittest.TestCase):
    def setUp(self):
        self.os = ProtoOS()
        self.user = self.os.create_user("u")
        self.shop = self.os.create_merchant("shop")
        self.budget = self.os.wallet.create_budget(self.user.did, 100.0)

    def test_basic_flow(self):
        srv = self.os.make_mcp_server("util")
        srv.add_tool("echo", "echo", {"type": "object", "properties": {"t": {"type": "string"}}},
                     lambda t="": {"echo": t})
        self.os.mount_mcp("util", srv)
        agent = self.os.create_agent("a", "agent")
        out = self.os.call_tool(agent.did, "util.echo", {"t": "ok"})
        self.assertIsNotNone(out)

if __name__ == "__main__":
    unittest.main()
