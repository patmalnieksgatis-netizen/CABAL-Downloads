"""Unit-test the exact-branch scanner without committing private game EXE."""
import importlib.util
from pathlib import Path
import struct
import unittest

HERE=Path(__file__).resolve().parents[1]/"evidence"
SPEC=importlib.util.spec_from_file_location("verify_09f3_response_branch",
                                             HERE/"verify_09f3_response_branch.py")
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class FakeReader:
    def __init__(self):
        self.range=(MODULE.HANDLER,MODULE.END)
        self.pieces={rva:bytes.fromhex(h) for rva,h in MODULE.SIGNATURES.items()}
        for rva,target in {**MODULE.REL_CALLS,**MODULE.STATE_WRITE_CALLS}.items():
            self.pieces[rva]=b"\xe8"+struct.pack("<i",target-rva-5)
        for rva,(opcode,target) in MODULE.JUMPS.items():
            delta=target-rva-(6 if len(opcode)==2 else 2)
            self.pieces[rva]=opcode+(
                struct.pack("<i",delta) if len(opcode)==2 else struct.pack("<b",delta))
    def bounds(self,rva):
        return self.range
    def read(self,rva,n):
        chunk=self.pieces.get(rva,b"")
        if len(chunk)!=n:raise ValueError("unexpected synthetic read")
        return chunk

class TestResponseBranches(unittest.TestCase):
    def test_branch_targets_and_lookups(self):
        result=MODULE.verify(FakeReader())
        self.assertEqual(result["lookup_callee_rva"],"0x24375C")
        self.assertFalse(result["7_byte_success_universally_truncated"])
        self.assertIn("0xAB6C",result["dword_route_zero_client_store"])
        self.assertIn("0x14",result["dword_route_one_or_two_client_store"])
        self.assertFalse(result["live_server_modified"])

    def test_fail_on_wrong_pdata(self):
        fake=FakeReader()
        fake.range=(MODULE.HANDLER,MODULE.END+1)
        with self.assertRaisesRegex(ValueError,"pdata"):
            MODULE.verify(fake)

    def test_fail_on_changed_status_instruction(self):
        fake=FakeReader()
        fake.pieces[0x6F851C]=b"\x80\x7d\x06\x00"
        with self.assertRaisesRegex(ValueError,"6F851C"):
            MODULE.verify(fake)

    def test_fail_on_wrong_jump_destination(self):
        fake=FakeReader()
        fake.pieces[0x6F85B2]=b"\x75\x22"
        with self.assertRaisesRegex(ValueError,"6F85B2"):
            MODULE.verify(fake)

    def test_fail_on_wrong_client_state_writer(self):
        fake=FakeReader()
        fake.pieces[0x37FA34]=b"\x90"*6
        with self.assertRaisesRegex(ValueError,"37FA34"):
            MODULE.verify(fake)

    def test_fail_on_wrong_secondary_writer_call(self):
        fake=FakeReader()
        fake.pieces[0x6F85D0]=b"\xe8\x00\x00\x00\x00"
        with self.assertRaisesRegex(ValueError,"6F85D0"):
            MODULE.verify(fake)

    def test_fail_on_wrong_lookup_target(self):
        fake=FakeReader()
        fake.pieces[0x6F85AA]=b"\xe8\x00\x00\x00\x00"
        with self.assertRaisesRegex(ValueError,"6F85AA"):
            MODULE.verify(fake)

if __name__=="__main__":
    unittest.main()
