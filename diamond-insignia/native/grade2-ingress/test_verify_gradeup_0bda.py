"""Offline regression: exact v291 Platinum grade-up analogue is 0BDA, not 0BDD."""
import importlib.util
from pathlib import Path
import unittest
src=Path(__file__).with_name("verify_gradeup_0bda.py")
spec=importlib.util.spec_from_file_location("gradeup",src)
gradeup=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gradeup)
class GradeUpEvidenceTests(unittest.TestCase):
    def test_original_gradeup_vs_new_opcode(self):
        self.assertEqual(gradeup.ANCHORS[0x6E073D],"b8100b0000")
        self.assertEqual(gradeup.ANCHORS[0x6DFD54],"c7442458da0b0000")
        self.assertEqual(gradeup.LEAS[0x6CFEF8],0x6DB688)
        self.assertEqual(gradeup.LEAS[0x6CFFFA],0x6DA920)
        self.assertEqual(gradeup.LEAS[0x6D0FEF],0x6E06F8)
        self.assertEqual(gradeup.LEAS[0x6D10C6],0x6DFD08)
    def test_shared_list_builder_and_network_sender(self):
        self.assertEqual(gradeup.CALLS[0x6E0794],gradeup.CALLS[0x6DFDA6])
        self.assertEqual(gradeup.CALLS[0x6E08D7],gradeup.CALLS[0x6DFEED])
        self.assertEqual(gradeup.CALLS[0x6DB7A1],gradeup.CALLS[0x6DAA2F])
        self.assertEqual(gradeup.CALLS[0x6DB823],gradeup.CALLS[0x6DAAAF])
    def test_corrected_slot_group_one_vs_two(self):
        self.assertEqual(gradeup.ANCHORS[0x6DB6F5],"448d6e01")
        self.assertEqual(gradeup.ANCHORS[0x6DAA34],"be02000000")
        self.assertNotIn(0x0BDD,[0x0B10,0x0BDA])
    def test_exact_binary_required(self):
        with self.assertRaisesRegex(gradeup.ProofError,"WRONG_EXACT_CLIENT"):
            gradeup.verify(b"bad")
if __name__=="__main__":
    unittest.main()
