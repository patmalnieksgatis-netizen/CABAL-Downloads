"""Synthetic metadata address and safe ELF mapping; no proprietary ELF in CI."""
import importlib.util
from pathlib import Path
import struct
import unittest
p=Path(__file__).with_name("verify_world_48_ticket_helper.py")
s=importlib.util.spec_from_file_location("stack_helper",p)
stack=s.loader.create_module(s) if hasattr(s.loader,"create_module") else None
if stack is None:
    stack=importlib.util.module_from_spec(s)
s.loader.exec_module(stack)

def fake_elf():
    data=bytearray(512)
    data[:6]=b"\x7fELF\x02\x01"
    struct.pack_into("<Q",data,0x20,0x40)
    struct.pack_into("<HH",data,0x36,56,1)
    struct.pack_into("<IIQQQQQQ",data,0x40,1,5,0x100,0x5000,0,0x40,0x100,0x1000)
    data[0x118:0x11b]=bytes.fromhex("488b07")
    return bytes(data)
class Tests(unittest.TestCase):
    def test_known_item_runtime_metadata_key(self):
        self.assertEqual(stack.ITEM_ID,0x02000211)
        self.assertEqual(stack.ITEM_ID&0xFFF,529)
        self.assertEqual((stack.ITEM_ID>>25)&3,1)
        self.assertEqual(stack.metadata_address(stack.ITEM_ID),0x13CAB48)
    def test_elf_file_mapping_not_runtime_bss(self):
        raw=fake_elf()
        segments=stack.segments(raw)
        self.assertEqual(stack.mapped(raw,segments,0x5018,3),bytes.fromhex("488b07"))
        with self.assertRaisesRegex(stack.EvidenceError,"UNMAPPED_FILE_RVA"):
            stack.mapped(raw,segments,0x5080,4)
    def test_wrong_sha_never_succeeds(self):
        with self.assertRaisesRegex(stack.EvidenceError,"WRONG_WORLD_FILE"):
            stack.evidence(fake_elf())
    def test_all_encoding_branch_anchors(self):
        self.assertEqual(stack.ANCHORS[0xAE0EFF],"83e07f")
        self.assertEqual(stack.ANCHORS[0xAE0F10],"c1e816")
        self.assertEqual(stack.ANCHORS[0xAE0EE9],"0fb7c0")
        self.assertEqual(stack.ANCHORS[0xA413AF],"e8dcfa0900")
        self.assertGreaterEqual(len(stack.ANCHORS),22)
if __name__=="__main__":unittest.main()
