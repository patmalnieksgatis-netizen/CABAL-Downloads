"""Offline tests for bounded single-use GDB 951 header capture; no gdb/VM needed."""
import importlib.util
from pathlib import Path
import struct
import unittest

P=Path(__file__).resolve().parents[1]/"Probe-Opcode951-Live.py"
spec=importlib.util.spec_from_file_location("liveprobe",P)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def packet(declared=143, core=1, escape=2):
    payload=bytearray(48)
    struct.pack_into("<H",payload,2,declared)
    struct.pack_into("<H",payload,14,9)
    payload[16]=core
    struct.pack_into("<H",payload,17,escape)
    return bytes(payload)

def gdb_print(data):
    parts=[]
    for i in range(0,len(data),8):
        items="\t".join(f"0x{v:02x}" for v in data[i:i+8])
        parts.append(f"0x7fffff00{i:02x}:\t{items}")
    return "Reading symbols...\nOPCODE_951_HEADER_BEGIN\n"+"\n".join(parts)+"\nOPCODE_951_HEADER_END\n"

class LiveProbeParserTests(unittest.TestCase):
    def test_extract_48_raw_bytes_ignores_gdb_addresses(self):
        buf=packet()
        self.assertEqual(mod.extract_header(gdb_print(buf)),buf)
    def test_short_header_capture(self):
        buf=packet()[:19]
        self.assertEqual(mod.extract_header(gdb_print(buf)),buf)
    def test_never_claim_bytes_if_incomplete(self):
        self.assertIsNone(mod.extract_header("OPCODE_951_HEADER_BEGIN\n0x7fff:\t0x00\nOPCODE_951_HEADER_END"))
    def test_legacy_valid_length(self):
        r=mod.infer_layout(packet())
        self.assertEqual(r["status"],"LEGACY_LENGTH_MATCH")
        self.assertEqual(r["length_delta"],0)
    def test_detect_length_mismatch(self):
        r=mod.infer_layout(packet(declared=151))
        self.assertEqual(r["status"],"V291_HEADER_MISMATCH")
        self.assertEqual(r["length_delta"],8)
    def test_correctly_handles_short_header(self):
        self.assertEqual(mod.infer_layout(None)["status"],"NO_HEADER")

if __name__=="__main__":unittest.main()
