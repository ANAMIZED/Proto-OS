"""Registry + wallet tests."""
import unittest
from protoos import ProtoOS
from protoos.registry import UnifiedAgentCard

class RegistryWalletTests(unittest.TestCase):
    def setUp(self):
        self.os = ProtoOS()

    def test_budget_create(self):
        u = self.os.create_user("u")
        b = self.os.wallet.create_budget(u.did, 25.0)
        self.assertEqual(b.limit_total, 25.0)

    def test_registry_put(self):
        a = self.os.create_agent("a", "desc")
        cards = self.os.registry.list()
        self.assertTrue(any(c.did == a.did for c in cards))

if __name__ == "__main__":
    unittest.main()
