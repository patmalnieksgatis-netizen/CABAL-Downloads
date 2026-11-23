"""Synthetic static registry tests: no proprietary binary in public GitHub."""
import importlib.util
from pathlib import Path
import struct
import unittest

SRC=Path(__file__).with_name("verify_merit_client_server_gap.py")
spec=importlib.util.spec_from_file_location("gap",SRC)
gap=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gap)

class Tests(unittest.TestCase):
    def test_rip_relative_positive_control(self):
        slot=gap.WORLD_MAP_BASE+0x0B10*8
        va=0x5000
        cmp_bytes=bytes.fromhex("48833d")+struct.pack("<i",slot-(va+8))+b"\x00"
        load=bytes.fromhex("488b1d")+struct.pack("<i",slot-(va+8+7))
        hits=gap.registry_hits(cmp_bytes+load,va,slot)
        self.assertEqual([x["rva"] for x in hits],["0x5000","0x5008"])
        self.assertEqual(gap.registry_hits(cmp_bytes+load,va,slot+8),[])

    def test_negative_then_new_static_registration_finds_it(self):
        slot=gap.WORLD_MAP_BASE+0x0BDA*8
        va=0x8000
        data=bytes.fromhex("48891d")+struct.pack("<i",slot-(va+7))
        self.assertEqual(len(gap.registry_hits(data,va,slot)),1)
        self.assertEqual(gap.registry_hits(data,va,slot+8),[])

    def test_fail_closed_sha(self):
        with self.assertRaisesRegex(gap.ProofError,"CLIENT_SHA_MISMATCH"):
            gap.verify_client(b"fake")
        with self.assertRaisesRegex(gap.ProofError,"WORLD_SHA_MISMATCH"):
            gap.checked_sha(b"fake",gap.WORLD_SHA,"WORLD")

    def test_s2c_client_registration_map(self):
        self.assertEqual(list(gap.S2C),[0x0BDA,0x0BDB,0x0BDC,0x0BDD,0x0BDF,0x0BE0])
        self.assertEqual(gap.S2C[0x0BDC][2],0x6DB154)
        self.assertNotIn(0x0BDC,[row[4] for row in gap.CLIENT.values()])
        self.assertEqual(gap.S2C[0x0BDF][2],0x6DAD14)

    def test_distinct_s2c_read_paths_are_pinned(self):
        self.assertEqual(set(gap.S2C_READ_ANCHORS),{0x0BDB,0x0BDC,0x0BDD,0x0BDF})
        self.assertEqual(len(gap.S2C_READ_ANCHORS[0x0BDC]),5)
        self.assertEqual(gap.S2C_READ_ANCHORS[0x0BDF][-1],
                         (0x6DADBF,"448b4e07"))
        self.assertEqual(gap.S2C_READ_ANCHORS[0x0BDD][0],
                         (0x6DB102,"80790601"))

    def test_two_s2c_paths_write_slot2(self):
        anchors=gap.STATE_SLOT2_ANCHORS
        self.assertEqual(anchors[0x6DB10D],"ba02000000")
        self.assertEqual(anchors[0x6DB019],"bb02000000")
        self.assertEqual(anchors[0x6DB023],"e808e7b6ff")
        self.assertEqual(anchors[0x2428A4],"e8876e0000")
        self.assertEqual(len(anchors),12)

    def test_static_client_cluster_and_bad_elf(self):
        self.assertEqual([x[4] for x in gap.CLIENT.values()],
                         [0x0B10,0x0BDA,0x0BDB,0x0BDD,0x0BDF,0x0BE0])
        with self.assertRaisesRegex(gap.ProofError,"NOT_ELF64_LE"):
            gap.elf_text(b"invalid")

if __name__=="__main__":
    unittest.main()
