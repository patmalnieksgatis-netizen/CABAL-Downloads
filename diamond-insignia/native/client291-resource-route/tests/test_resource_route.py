#!/usr/bin/env python3
"""Run with the original uploaded ZIP available at -- archive path in tests directory.

For a local run:
  cp /path/CABAL_v291_Diamond_Client_exact.zip evidence/
  python3 -m unittest discover -s tests -v
The exact proprietary EXE/ENC are deliberately excluded from GitHub.
"""
import sys
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'src'))
from prove_resource_route import inspect, EvidenceError

class ResourceRouteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive=Path(__file__).parents[1]/'evidence'/'CABAL_v291_Diamond_Client_exact.zip'
        if not cls.archive.is_file():
            raise unittest.SkipTest('Exact original user upload not bundled; provide archive locally.')
        with zipfile.ZipFile(cls.archive) as z:
            cls.exe=z.read('CabalMain.exe')
            cls.enc=z.read('meritsystem.enc')

    def test_exact(self):
        got=inspect(self.exe,self.enc)
        self.assertEqual(got['selector_names']['52'],'meritsystem.enc')
        self.assertEqual(got['path_selector_flag']['52'],1)
        self.assertEqual(got['path_selector_flag']['53'],0)
        self.assertEqual(got['instruction_anchors'],17)
        self.assertEqual(got['verified_call_edges'],7)

    def test_tampered_exe_rejected(self):
        blob=bytearray(self.exe);blob[-5]^=1
        with self.assertRaisesRegex(EvidenceError,'EXACT_CLIENT_SHA_OR_SIZE_MISMATCH'):
            inspect(bytes(blob),self.enc)

    def test_tampered_enc_rejected(self):
        blob=bytearray(self.enc);blob[-5]^=1
        with self.assertRaisesRegex(EvidenceError,'EXACT_MERITSYSTEM_SHA_OR_SIZE_MISMATCH'):
            inspect(self.exe,bytes(blob))

if __name__=='__main__': unittest.main(verbosity=2)
