"""Obsidian vault export tests."""
import unittest
import tempfile
from pathlib import Path
from protoos import ProtoOS
from protoos.vault import write_vault, write_vault_zip, unresolved_links

class VaultTests(unittest.TestCase):
    def setUp(self):
        self.os = ProtoOS()
        u = self.os.create_user("casey")
        self.os.wallet.create_budget(u.did, 200.0)

    def test_note_population(self):
        with tempfile.TemporaryDirectory() as d:
            n = write_vault(self.os, d)
            self.assertGreater(n, 0)

    def test_wikilinks_all_resolve(self):
        with tempfile.TemporaryDirectory() as d:
            write_vault(self.os, d)
            bad = unresolved_links(d)
            self.assertEqual(bad, [])

    def test_zip_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            z = Path(d) / "v.zip"
            n = write_vault_zip(self.os, z)
            self.assertGreater(n, 0)
            self.assertTrue(z.exists())

if __name__ == "__main__":
    unittest.main()
