"""Synthetic ELF mapping regression tests, no WorldSvr binary uploaded."""
import importlib.util
from pathlib import Path
import struct
import unittest
file=Path(__file__).with_name("verify_platinum_slot_list_worldsvr.py")
spec=importlib.util.spec_from_file_location("slotproof",file)
p=importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

def small_elf():
    data=bytearray(512)
    data[:6]=b"\x7fELF\x02\x01"
    struct.pack_into("<Q",data,0x20,0x40)
    struct.pack_into("<HH",data,0x36,56,1)
    struct.pack_into("<IIQQQQQQ",data,0x40,1,5,0x100,0x5000,0,0x80,0x80,0x1000)
    data[0x110:0x115]=b"\xE8"+struct.pack("<i",0x5030-(0x5010+5))
    data[0x130:0x134]=bytes.fromhex("488d045b")
    return bytes(data)

class Tests(unittest.TestCase):
    def test_elf_program_header_address_mapping(self):
        data=small_elf()
        self.assertEqual(p.elf_va_bytes(data,0x5030,4),bytes.fromhex("488d045b"))
        self.assertEqual(p.elf_va_bytes(data,0x5010,1),b"\xe8")
        with self.assertRaisesRegex(p.ProofError,"ELF_VA_UNMAPPED"):
            p.elf_va_bytes(data,0x5200,2)
    def test_static_relative_call_anchor(self):
        data=small_elf()
        ins=p.elf_va_bytes(data,0x5010,5)
        self.assertEqual(0x5010+5+struct.unpack_from("<i",ins,1)[0],0x5030)
    def test_wrong_world_rejected(self):
        with self.assertRaisesRegex(p.ProofError,"WORLD_SHA_OR_SIZE"):
            p.proof(b"not-original")
    def test_important_fixed_anchors(self):
        self.assertEqual(p.ANCHORS[0xA41067],"410fb754560c")
        self.assertEqual(p.ANCHORS[0x587E43],"4881fe09020000")
        self.assertEqual(p.ANCHORS[0x587EA6],"48c1e004")
        self.assertEqual(p.CALLS[0xA413F6],0x587E30)
        self.assertEqual(len(p.ANCHORS),15)
        self.assertEqual(len(p.CALLS),2)
if __name__=="__main__":
    unittest.main()
