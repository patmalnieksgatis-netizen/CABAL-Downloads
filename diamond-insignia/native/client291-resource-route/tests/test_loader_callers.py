"""Tests use synthetic fixtures; real executable is intentionally NOT in GitHub."""
import importlib.util
from pathlib import Path
import struct
import unittest

src=Path(__file__).resolve().parents[1]/"src"/"verify_all_resource_loader_callers.py"
spec=importlib.util.spec_from_file_location("loaderproof",src)
proof=importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)

class Tests(unittest.TestCase):
    def test_direct_calls(self):
        data=bytearray(38)
        for i in (7,30):
            data[i:i+5]=b"\xe8"+struct.pack("<i",0x2178e0-(0x1000+i+5))
        self.assertEqual(proof.scan_direct_calls(data,0x1000,0x2178e0),[0x1007,0x101e])
        self.assertEqual(proof.scan_direct_calls(data,0x1000,0x2178e1),[])
    def test_pdata_boundaries(self):
        funcs=[(0x100,0x120),(0x130,0x160)]
        self.assertEqual(proof.owning_function(0x100,funcs),(0x100,0x120))
        self.assertEqual(proof.owning_function(0x11f,funcs),(0x100,0x120))
        self.assertIsNone(proof.owning_function(0x120,funcs))
        self.assertIsNone(proof.owning_function(0x128,funcs))
        self.assertEqual(proof.owning_function(0x150,funcs),(0x130,0x160))
    def test_wrong_client_never_accepted(self):
        with self.assertRaisesRegex(proof.ProofError,"WRONG_CLIENT_SHA_OR_SIZE"):
            proof.sections_and_pdata(b"not an exact client")

if __name__=="__main__":
    unittest.main()
