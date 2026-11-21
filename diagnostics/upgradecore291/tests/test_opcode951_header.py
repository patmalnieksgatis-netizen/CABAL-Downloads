"""Offline 951 v291 candidate-field inference tests; no game actions."""
import importlib.util
from pathlib import Path
import struct
import unittest

P=Path(__file__).resolve().parents[1]/"Analyze-Opcode951-Header.py"
spec=importlib.util.spec_from_file_location("header951",P)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def header(packetlen=139,offset=0x11,count=0,core=1,main=0):
    p=bytearray(64)
    struct.pack_into("<H",p,2,packetlen)
    struct.pack_into("<H",p,14,main)
    p[0x10]=core
    struct.pack_into("<H",p,offset,count)
    return bytes(p)

class PacketHeaderInferences(unittest.TestCase):
    def test_legacy_zero_escape_count(self):
        r=mod.analyze_header(139,header())
        self.assertEqual("LEGACY_951_HEADER_COMPATIBLE",r["status"])
    def test_shifted_count_is_only_a_candidate(self):
        r=mod.analyze_header(143,header(143,0x15,2))
        self.assertEqual("ONE_POSSIBLE_SHIFTED_COUNT_FIELD",r["status"])
        self.assertEqual("0x15",r["count_field_candidates"][0]["candidate_offset"])
    def test_fixed_header_extension_not_assumed_safe(self):
        r=mod.analyze_header(145,header(145,0x15,0))
        self.assertEqual("FIXED_SIZE_OR_LAYOUT_MISMATCH",r["status"])
    def test_ambiguous_candidates_require_more_evidence(self):
        b=bytearray(header(143,0x15,2));struct.pack_into("<H",b,0x19,2)
        r=mod.analyze_header(143,bytes(b))
        self.assertEqual("AMBIGUOUS_COUNT_FIELD_CANDIDATES",r["status"])
    def test_no_matching_shift(self):
        r=mod.analyze_header(143,header(143))
        self.assertEqual("NO_COUNT_FIELD_AT_EXPECTED_VALUE_IN_CAPTURED_HEADER",r["status"])
    def test_short_header(self):
        r=mod.analyze_header(143,b"\0"*18)
        self.assertEqual("header_too_short",r["error"])
    def test_invalid_declared_header_not_legacy(self):
        r=mod.analyze_header(141,header(139))
        self.assertNotEqual("LEGACY_951_HEADER_COMPATIBLE",r["status"])

if __name__=="__main__":
    unittest.main()
