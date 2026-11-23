"""All tests use synthetic data; private client bytes stay out of GitHub."""
import importlib.util
from pathlib import Path
import struct
import unittest

src=Path(__file__).with_name("verify_merit_ui_0b10.py")
spec=importlib.util.spec_from_file_location("proof",src)
proof=importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)

class MeritUiTests(unittest.TestCase):
    def test_e8_relative_target(self):
        instr=b"\xe8"+struct.pack("<i",0x6B69C8-(0x6D0FFA+5))
        self.assertEqual(proof.direct_target(0x6D0FFA,instr,0xe8,5),0x6B69C8)
    def test_rip_relative_lea_target(self):
        instr=bytes.fromhex("488d1502f70000")
        self.assertEqual(proof.direct_target(0x6D0FEF,instr,0x48,7),0x6E06F8)
    def test_invalid_instruction(self):
        with self.assertRaises(proof.ProofError):
            proof.direct_target(0,b"\x90"*5,0xe8,5)
        with self.assertRaises(proof.ProofError):
            proof.direct_target(0,b"\xe8"*4,0xe8,5)
    def test_refuse_nonmatching_client(self):
        with self.assertRaisesRegex(proof.ProofError,"EXACT_CLIENT_HASH_OR_LENGTH_MISMATCH"):
            proof.audit(b"\x00"*200)

if __name__=="__main__":
    unittest.main()
