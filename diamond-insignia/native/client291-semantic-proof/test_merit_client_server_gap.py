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

    def test_static_client_cluster_and_bad_elf(self):
        self.assertEqual([x[4] for x in gap.CLIENT.values()],
                         [0x0B10,0x0BDA,0x0BDB,0x0BDD,0x0BDF,0x0BE0])
        with self.assertRaisesRegex(gap.ProofError,"NOT_ELF64_LE"):
            gap.elf_text(b"invalid")

if __name__=="__main__":
    unittest.main()
