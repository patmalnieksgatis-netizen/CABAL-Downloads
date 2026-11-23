"""Offline-only regression tests for SHA-pinned v291 Merit-adjacent packet shapes."""
import importlib.util
import struct
from pathlib import Path
import unittest

src=Path(__file__).resolve().parents[1]/"evidence"/"verify_merit_family_c2s.py"
spec=importlib.util.spec_from_file_location("family",src)
family=importlib.util.module_from_spec(spec)
spec.loader.exec_module(family)

def frame(opcode:int,payload:bytes,length=None,transport=0):
    packet=bytearray(b"\xE2\xB7\x00\x00"
                     + struct.pack("<I",transport)
                     + struct.pack("<H",opcode)+payload)
    struct.pack_into("<H",packet,2,len(packet) if length is None else length)
    return bytes(packet)

class MeritFamilyTests(unittest.TestCase):
    def ok(self,packet):
        actual=family.classify_c2s(packet)
        self.assertTrue(actual["verified_sender_shape"],actual)
        self.assertFalse(actual["diamond_action_proven"])
        self.assertEqual(actual["reason"],"client_sender_shape_only")
        return actual["raw_fields"]

    def rejects(self,packet,reason):
        actual=family.classify_c2s(packet)
        self.assertFalse(actual["verified_sender_shape"],actual)
        self.assertEqual(actual["reason"],reason,actual)

    def test_0bda_zero_and_two_list_items(self):
        self.assertEqual(self.ok(frame(0x0BDA,b"\0"*4))["count_u16"],0)
        fields=self.ok(frame(0x0BDA,struct.pack("<HHH",2,3,33)))
        self.assertEqual(fields["entries_u16_raw"],[3,33])
        self.rejects(frame(0x0BDA,struct.pack("<HH",2,3)),
                     "entry_count_size_mismatch")

    def test_0bdb_two_counted_lists(self):
        payload=struct.pack("<IHHHHH",0x12345678,2,1,9,10,11)
        fields=self.ok(frame(0x0BDB,payload))
        self.assertEqual(fields["field_10_u32_raw"],0x12345678)
        self.assertEqual(fields["first_entries_u16_raw"],[9,10])
        self.assertEqual(fields["second_entries_u16_raw"],[11])
        self.assertEqual(self.ok(frame(0x0BDB,b"\0"*10))["first_count_u16"],0)
        self.rejects(frame(0x0BDB,struct.pack("<IHH",1,2,0)+b"\0"*2),
                     "entry_count_size_mismatch")
        self.rejects(frame(0x0BDB,struct.pack("<IHH",1,254,2)+b"\0"*2),
                     "ambiguous_8bit_total_count")

    def test_0bdd_fixed_dword_conditional(self):
        value=self.ok(frame(0x0BDD,struct.pack("<I",123)))["field_10_u32_raw"]
        self.assertEqual(value,123)
        self.rejects(frame(0x0BDD,b"\xff"*4),"sender_does_not_send_sentinel")
        self.rejects(frame(0x0BDD,b"\0"*5),"expected_14_bytes")

    def test_0bdf_fixed_nonzero_byte(self):
        fields=self.ok(frame(0x0BDF,b"\x07"))
        self.assertEqual(fields["field_10_u8_raw"],7)
        self.rejects(frame(0x0BDF,b"\0"),"sender_requires_nonzero_byte")
        self.rejects(frame(0x0BDF,b"\x01\x00"),"expected_11_bytes")

    def test_0be0_counted_u16_items(self):
        self.assertEqual(self.ok(frame(0x0BE0,struct.pack("<IHH",7,0,0)))
                         ["count_u16"],0)
        fields=self.ok(frame(0x0BE0,struct.pack("<IHHHH",77,3,10,11,12)))
        self.assertEqual(fields["field_10_u32_raw"],77)
        self.assertEqual(fields["entries_u16_raw"],[10,11,12])
        self.rejects(frame(0x0BE0,struct.pack("<IHH",77,2,10)),
                     "entry_count_size_mismatch")

    def test_magic_header_size_unknown(self):
        self.rejects(b"bad","missing_or_invalid_header")
        self.rejects(b"\0"*20,"missing_or_invalid_header")
        self.rejects(frame(0x0BDD,struct.pack("<I",4),length=15),
                     "header_size_mismatch")
        self.rejects(frame(0x0BE1,b"\0"*8),"not_this_merit_family")

    def test_missing_client_is_rejected(self):
        with self.assertRaisesRegex(family.EvidenceError,"EXACT_CLIENT_SHA_OR_SIZE_MISMATCH"):
            family.verify_exact_client(b"fake")

    def test_anchored_sender_set_and_calls(self):
        self.assertEqual(sorted(family.ANCHORS),[0x0BDA,0x0BDB,0x0BDD,0x0BDF,0x0BE0])
        self.assertEqual(set(family.SEND_RVAS),set(family.ANCHORS))
        self.assertEqual(family.SEND_TARGET,0x2B7A40)

if __name__=="__main__":
    unittest.main()
