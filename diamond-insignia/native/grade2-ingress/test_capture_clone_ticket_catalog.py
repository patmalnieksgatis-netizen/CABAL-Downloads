"""No process memory is read in CI. Pure synthetic clone safety fixtures."""
import importlib.util
from pathlib import Path
import unittest

source=Path(__file__).with_name("capture_clone_ticket_catalog.py")
spec=importlib.util.spec_from_file_location("ticket_capture",source)
cap=importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)

MACHINE="a"*32
def valid_marker(pid=100):
    return {"purpose":cap.PURPOSE,"machine_id":MACHINE,"pid":pid,
            "world_sha256":cap.WORLD_SHA,"ticket_item_id":cap.TICKET}

class CaptureGateTests(unittest.TestCase):
    def test_exact_metadata_location(self):
        self.assertEqual(cap.TICKET,0x02000211)
        self.assertEqual(cap.METADATA_VA,0x13CAB48)
        self.assertEqual(cap.METADATA_KIND_VA,0x13CAB80)
        self.assertEqual(cap.METADATA_STACK_VA,0x13CAB84)
        self.assertEqual(cap.METADATA_STACK_VA-cap.METADATA_KIND_VA,4)

    def test_explicit_clone_pid_machine_hash_binding(self):
        self.assertTrue(cap.validate_marker(valid_marker(),MACHINE,100))
        for modify in (
            {"pid":101},{"machine_id":"b"*32},{"world_sha256":"0"*64},
            {"purpose":"LIVE"},{"ticket_item_id":1},{"pid":True}
        ):
            m=valid_marker();m.update(modify)
            with self.assertRaises(cap.Reject):
                cap.validate_marker(m,MACHINE,100)
        m=valid_marker();m["extra"]="never accept"
        with self.assertRaises(cap.Reject):
            cap.validate_marker(m,MACHINE,100)

    def test_no_unattested_vm_identity(self):
        self.assertEqual(cap.machine_id_text("a"*32+"\n"),MACHINE)
        for val in ("", "A"*32, "1"*16, "b"*31+"Z"):
            with self.assertRaises(cap.Reject):
                cap.machine_id_text(val)

    def test_memory_page_must_cover_both_fields(self):
        maps="13ca000-13cb000 rw-p 00000000 00:00 0\n"
        self.assertTrue(cap.mapped_readable(maps,cap.METADATA_KIND_VA,8))
        self.assertFalse(cap.mapped_readable("13ca000-13cb000 ---p 00000000 00:00 0\n",
                                           cap.METADATA_KIND_VA,8))
        self.assertFalse(cap.mapped_readable("13ca000-13cab84 rw-p 0 0 0\n",
                                           cap.METADATA_KIND_VA,8))
        self.assertFalse(cap.mapped_readable("",cap.METADATA_KIND_VA,8))

    def test_quantity_branch_selection_only(self):
        self.assertEqual(cap.classification(0x46,100),
                         "option_unsigned_upper_10_bits")
        self.assertEqual(cap.classification(0x43,100),
                         "option_unsigned_upper_10_bits")
        self.assertEqual(cap.classification(0xAF,100),
                         "option_unsigned_lower_16_bits")
        self.assertEqual(cap.classification(0xB8,100),
                         "option_unsigned_lower_16_bits")
        self.assertEqual(cap.classification(0x10,100),
                         "option_unsigned_lower_7_bits")
        self.assertEqual(cap.classification(0x1B,100),
                         "option_unsigned_lower_7_bits")
        self.assertEqual(cap.classification(0x66,100),
                         "option_unsigned_lower_7_bits")
        self.assertEqual(cap.classification(0x10,1),
                         "singleton_metadata_stack_le_1")
        self.assertEqual(cap.classification(0x10,0),
                         "singleton_metadata_stack_le_1")
        self.assertEqual(cap.classification(0x47,100),
                         "original_helper_fallback_one__NOT_verified_ticket_stack_quantity")
        # Exact WorldSvr live VM item 33554961 tag/stack, Nov 23.
        self.assertEqual(cap.classification(0xB0,999),
                         "original_helper_fallback_one__NOT_verified_ticket_stack_quantity")

    def test_process_start_time_parsing(self):
        # Kernel stat fields 3..22: a total of 20 fields here.
        line="1234 (WorldSvr (test)) "+" ".join(["S"]+["0"]*18+["23456"])
        self.assertEqual(cap.process_start_time(line),23456)
        with self.assertRaises(cap.Reject):
            cap.process_start_time("bad stat line")

    def test_no_optional_auto_attach(self):
        with self.assertRaises(SystemExit) as exit_state:
            cap.main([])
        self.assertEqual(exit_state.exception.code,2)

if __name__=="__main__":
    unittest.main()
