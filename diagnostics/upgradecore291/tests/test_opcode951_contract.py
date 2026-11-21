"""Verified old native 951 length/count guard synthetic tests (no game runtime)."""
import importlib.util
from pathlib import Path
import struct
import unittest

P=Path(__file__).resolve().parents[1]/"Opcode951-Contract.py"
spec=importlib.util.spec_from_file_location("contract951",P)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def packet(count=0,core=1,slot=0,declared=None):
    length=139+2*count
    b=bytearray(length)
    struct.pack_into("<H",b,2,length if declared is None else declared)
    struct.pack_into("<H",b,14,slot)
    b[16]=core
    struct.pack_into("<H",b,17,count)
    return bytes(b)

class Contract(unittest.TestCase):
    def test_zero_escape_slots_and_minimum_length(self):
        self.assertTrue(mod.read_shape(packet())["valid"])
    def test_two_escape_slots(self):
        d=mod.read_shape(packet(2))
        self.assertTrue(d["valid"]);self.assertEqual(d["expected_packet_length"],143)
    def test_declared_length_mismatch(self):
        self.assertIn("declared_length_mismatch",mod.read_shape(packet(1,declared=139))["reasons"])
    def test_truncated_capture(self):
        self.assertIn("captured_length_mismatch",mod.read_shape(packet(1)[:-1])["reasons"])
    def test_too_many_escape_slots(self):
        self.assertIn("escape_slot_count_invalid",mod.read_shape(packet(522))["reasons"])
    def test_zero_cores(self):
        self.assertIn("core_slot_count_invalid",mod.read_shape(packet(core=0))["reasons"])
    def test_invalid_main_slot(self):
        self.assertIn("main_slot_invalid",mod.read_shape(packet(slot=522))["reasons"])
    def test_short_header(self):
        self.assertFalse(mod.read_shape(b"\0"*18)["valid"])

if __name__=="__main__":unittest.main()
