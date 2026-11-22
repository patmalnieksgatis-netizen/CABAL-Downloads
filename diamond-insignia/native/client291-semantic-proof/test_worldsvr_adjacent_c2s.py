import struct
import unittest
from verify_worldsvr_adjacent_c2s import ENTRIES, REGISTRY, verify_entry

def fixture(opcode):
    site,store,label_store,handler,name=ENTRIES[opcode]
    slot=REGISTRY+8*opcode
    label_va=0xc94000
    blobs={
        site:bytes.fromhex("48833d")+struct.pack("<i",slot-(site+8))+b"\x00",
        store:bytes.fromhex("48c700")+struct.pack("<I",handler),
        label_store:bytes.fromhex("48c74318")+struct.pack("<I",label_va),
        label_va:name.encode("ascii")+b"\x00"
    }
    def read(address,size):
        return blobs[address][:size]
    return blobs,read

class WorldSvrAdjacentCommandsTests(unittest.TestCase):
    def test_exact_four_registration_contracts(self):
        for op in ENTRIES:
            with self.subTest(opcode=op):
                _,read=fixture(op)
                r=verify_entry(read,op,ENTRIES[op])
                self.assertEqual(r["slot_va"],hex(REGISTRY+op*8))
                self.assertEqual(r["handler_label"],ENTRIES[op][4])
    def test_wrong_slot_rejected(self):
        op=0x09fd
        blobs,read=fixture(op)
        site=ENTRIES[op][0]
        x=bytearray(blobs[site]);x[3]^=1;blobs[site]=bytes(x)
        with self.assertRaisesRegex(ValueError,"slot"):
            verify_entry(read,op,ENTRIES[op])
    def test_wrong_handler_rejected(self):
        op=0x09fb
        blobs,read=fixture(op)
        site=ENTRIES[op][1]
        x=bytearray(blobs[site]);x[3]^=1;blobs[site]=bytes(x)
        with self.assertRaisesRegex(ValueError,"pointer"):
            verify_entry(read,op,ENTRIES[op])
    def test_wrong_label_rejected(self):
        op=0x09f9
        blobs,read=fixture(op)
        blobs[0xc94000]=b"WrongSystem\0"
        with self.assertRaisesRegex(ValueError,"label"):
            verify_entry(read,op,ENTRIES[op])
    def test_preserves_merit_vs_dimension_distinction(self):
        self.assertIn("MERIT",ENTRIES[0x09f3][4])
        for op in (0x09f9,0x09fb,0x09fd):
            self.assertIn("DIMENSION_INVENTORY",ENTRIES[op][4])
            self.assertNotIn("DIAMOND",ENTRIES[op][4])
if __name__=="__main__":
    unittest.main()
