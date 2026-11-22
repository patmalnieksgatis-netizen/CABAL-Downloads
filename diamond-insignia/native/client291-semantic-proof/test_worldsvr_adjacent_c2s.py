import struct
import unittest
from verify_worldsvr_adjacent_c2s import ENTRIES, REGISTRY, verify_entry, verify_merit_dispatch

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
class MeritServerRouteTests(unittest.TestCase):
    def test_two_distinct_server_paths(self):
        anchors={
            0xa40dc0:"8b700a", 0xa40dca:"8b400e", 0xa40dda:"488d4de8",
            0xa40deb:"7513", 0xa3ca58:"488b9730010000",
            0xa3ca8c:"394820", 0xa3caef:"83782401",
        }
        data={site:bytes.fromhex(value) for site,value in anchors.items()}
        for site,dst in ((0xa40dd3,0xa3ca50),(0xa40ded,0xa3b2d0),
                         (0xa40e00,0xa3c3a0)):
            data[site]=bytes.fromhex("e8")+struct.pack("<i",dst-site-5)
        def read(addr,length):return data[addr][:length]
        report=verify_merit_dispatch(read)
        self.assertEqual(report["branch_if_selector_zero"],"0xa3b2d0")
        self.assertEqual(report["branch_if_selector_nonzero"],"0xa3c3a0")
        self.assertFalse(report["mastery_159_474_accepted_proven"])
        broken=dict(data)
        broken[0xa40ded]=bytes.fromhex("e800000000")
        with self.assertRaisesRegex(ValueError,"CALL"):
            verify_merit_dispatch(lambda a,n:broken[a][:n])
        broken=dict(data)
        broken[0xa3caef]=bytes.fromhex("90909090")
        with self.assertRaisesRegex(ValueError,"instruction"):
            verify_merit_dispatch(lambda a,n:broken[a][:n])

if __name__=="__main__":
    unittest.main()
