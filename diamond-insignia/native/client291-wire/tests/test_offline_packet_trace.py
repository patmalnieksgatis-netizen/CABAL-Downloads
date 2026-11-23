"""Offline packet trace regressions, no game assets needed."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "evidence" / "classify_offline_packet_trace.py"
spec = importlib.util.spec_from_file_location("trace", SCRIPT)
trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace)


class TraceTests(unittest.TestCase):
    def test_verified_18_byte_c2s_is_not_diamond(self):
        frame = bytes.fromhex("e2 b7 12 00 00 00 00 00 f3 09 01 00 00 00 02 00 00 00")
        result = trace.classify("C2S", frame)
        self.assertEqual(result["classification"], "merit_c2s_shape_verified")
        self.assertEqual(result["state118_raw"], 1)
        self.assertEqual(result["state11C_raw"], 2)
        self.assertFalse(result["diamond_confirmed"])

    def test_legacy_7b_success_is_route_unobserved(self):
        result = trace.classify("S2C", bytes.fromhex("e2 b7 07 00 f3 09 01"))
        self.assertEqual(result["classification"], "merit_s2c_7b_route_unobserved")

    def test_adjacent_dimension_are_not_diamond(self):
        for opcode in (0x09F9, 0x09FB, 0x09FD):
            frame = bytes.fromhex("e2 b7 06 00") + opcode.to_bytes(2, "little")
            result = trace.classify("S2C", frame)
            self.assertEqual(result["classification"], "other_opcode")
            self.assertFalse(result["diamond_confirmed"])

    def test_reject_header_length_and_syntax(self):
        self.assertEqual(trace.classify("S2C", b"\x00")["reason"], "short_header")
        self.assertEqual(trace.classify("S2C", bytes.fromhex("e2 b7 09 00 f3 09 01"))["reason"], "length_mismatch")
        self.assertEqual(trace.parse_line("S2C nothex", 2)["reason"], "line_syntax")
        self.assertIsNone(trace.parse_line("# comment", 3))

    def test_success_dword_is_raw_only(self):
        result = trace.classify("S2C", bytes.fromhex("e2 b7 0b 00 f3 09 01 78 56 34 12"))
        self.assertEqual(result["payload_dword_plus7_raw"], 0x12345678)
        self.assertEqual(result["classification"], "merit_s2c_11plus_semantics_unverified")
        self.assertFalse(result["diamond_confirmed"])


if __name__ == "__main__":
    unittest.main()
