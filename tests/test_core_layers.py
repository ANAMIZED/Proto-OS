"""Core layer tests (identity, policy, audit, runtime)."""
import unittest
from protoos import ProtoOS, PolicyDenied

class CoreLayerTests(unittest.TestCase):
    def setUp(self):
        self.os = ProtoOS()

    def test_identity_create(self):
        u = self.os.create_user("alice")
        self.assertTrue(u.did.startswith("did:"))

    def test_policy_allow(self):
        self.os.engine.add_rule("user", "allow", ["payment.settle"], "amount <= 10")
        d = self.os.engine.evaluate("payment.settle", {"amount": 5})
        self.assertEqual(d["effect"], "allow")

    def test_audit_chain(self):
        self.os.audit.append("test", "ping", {"x": 1})
        ok, _ = self.os.audit.verify()
        self.assertTrue(ok)

if __name__ == "__main__":
    unittest.main()
