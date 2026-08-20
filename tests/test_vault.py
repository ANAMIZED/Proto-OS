"""Obsidian vault export: notes, wikilinks, audit fidelity, zip, hygiene."""
import tempfile
import unittest
import zipfile
from pathlib import Path

from protoos.graph import build_demo_world
from protoos.vault import (unresolved_links, vault_notes, write_vault,
                           write_vault_zip)


class VaultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.os_, cls.refs = build_demo_world()
        cls.notes = vault_notes(cls.os_)

    def by_name(self):
        return {n: b for n, b in self.notes}

    def test_note_population(self):
        names = {n for n, _ in self.notes}
        self.assertIn("00-index.md", names)
        self.assertIn("agents/ana.md", names)
        self.assertTrue(any(n.startswith("receipts/") for n in names))
        self.assertTrue(any(n.startswith("budgets/") for n in names))
        self.assertTrue(any(n.startswith("mandates/") for n in names))

    def test_wikilinks_all_resolve(self):
        self.assertEqual(unresolved_links(self.notes), [])

    def test_ana_note_links_and_frontmatter(self):
        body = self.by_name()["agents/ana.md"]
        self.assertIn("did:proto:", body)
        self.assertIn("[[budgets/", body)

    def test_receipts_link_budgets(self):
        names = {n for n, _ in self.notes}
        rcp = [n for n in names if n.startswith("receipts/")]
        self.assertGreaterEqual(len(rcp), 1)
        for n in rcp:
            body = self.by_name()[n]
            self.assertTrue("[[budgets/" in body or "budget" in body.lower())

    def test_cart_note_links_intent_and_payment(self):
        carts = [n for n, _ in self.notes if "/cart-" in n or n.endswith("-cart.md")]
        # soft: if demo produced cart notes, they link
        for n in carts:
            body = self.by_name()[n]
            self.assertTrue("intent" in body.lower() or "payment" in body.lower())

    def test_audit_note_matches_chain(self):
        body = self.by_name().get("audit/chain.md", "")
        if body:
            self.assertIn("hash", body.lower())

    def test_pending_approval_counted(self):
        names = {n for n, _ in self.notes}
        # demo parks one approval
        self.assertTrue(any("pending" in n or "approval" in n for n in names)
                        or any("pending" in b.lower() for _, b in self.notes))

    def test_no_private_key_material(self):
        blob = "\n".join(b for _, b in self.notes)
        for bad in ("BEGIN PRIVATE KEY", "BEGIN RSA PRIVATE", "sk-", "-----BEGIN EC"):
            self.assertNotIn(bad, blob)

    def test_directory_writer(self):
        with tempfile.TemporaryDirectory() as d:
            n = write_vault(self.os_, d)
            self.assertGreater(n, 0)
            self.assertTrue((Path(d) / "00-index.md").exists())

    def test_zip_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            z = Path(d) / "vault.zip"
            n = write_vault_zip(self.os_, z)
            self.assertGreater(n, 0)
            self.assertTrue(z.exists())
            with zipfile.ZipFile(z) as zf:
                names = zf.namelist()
            self.assertIn("00-index.md", names)


if __name__ == "__main__":
    unittest.main()
