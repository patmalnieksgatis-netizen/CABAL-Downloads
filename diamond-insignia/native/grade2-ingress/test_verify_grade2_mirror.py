"""Regression assertions for corrected Platinum 0B13 / new 0BDD pairing."""
import importlib.util
from pathlib import Path
import unittest

source=Path(__file__).with_name("verify_grade2_mirror.py")
spec=importlib.util.spec_from_file_location("grade2mirror",source)
mirror=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mirror)

class MirrorTests(unittest.TestCase):
    def test_original_gradeup_does_not_use_slot_cancel_handler(self):
        self.assertEqual(mirror.S2C_BINDINGS[0x6CFEF8],0x6DB688)
        self.assertEqual(mirror.S2C_BINDINGS[0x6CFF79],0x6DBDA0)
        self.assertEqual(mirror.S2C_BINDINGS[0x6D007B],0x6DB0FC)
        self.assertNotEqual(mirror.S2C_BINDINGS[0x6CFEF8],
                            mirror.S2C_BINDINGS[0x6CFF79])

    def test_0b13_and_0bdd_are_similar_cancel_shape(self):
        self.assertEqual(mirror.ANCHORS[0x6E0DEB],"b8130b0000")
        self.assertEqual(mirror.ANCHORS[0x6E0DFA],"8b8874010000")
        self.assertEqual(mirror.ANCHORS[0x6E0414],"b8dd0b0000")
        self.assertEqual(mirror.ANCHORS[0x6E0423],"8b8878010000")
        self.assertEqual(mirror.CALLS[0x6DBDB9],mirror.CALLS[0x6DB115])
        self.assertEqual(mirror.CALLS[0x6E0E21],mirror.CALLS[0x6E044A])

    def test_success_slot_state_is_1_vs_2(self):
        self.assertEqual(mirror.ANCHORS[0x6DBDB1],"ba01000000")
        self.assertEqual(mirror.ANCHORS[0x6DB10D],"ba02000000")
        self.assertEqual(mirror.ANCHORS[0x6DBDDE],"b901000000")
        self.assertEqual(mirror.ANCHORS[0x6DB13A],"b902000000")

    def test_wrong_binary_refused(self):
        with self.assertRaisesRegex(mirror.ProofError,"EXACT_CLIENT_SHA_OR_SIZE"):
            mirror.verify(b"wrong-client")

if __name__=="__main__":
    unittest.main()
