"""Read-only unit tests for exact-source WorldSvr clone header packaging."""
import importlib.util
import pathlib
import tempfile
import unittest

HERE=pathlib.Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location(
    "diamond_bound_clone_patcher",HERE/"Apply-DiamondBoundClone.py")
PATCHER=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCHER)

HEADERS=(
    "DiamondBoundIngress.h",
    "diamond_abi.h",
    "diamond_world_bridge.h",
    "diamond_merit_world_entry.h",
)

class ClonePatcherHeaderTests(unittest.TestCase):
    def test_exact_native_header_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            dest=pathlib.Path(folder)
            PATCHER.copy_native_headers(dest)
            for name in HEADERS:
                expected=(HERE/name if name=="DiamondBoundIngress.h"
                          else HERE.parent/"native"/name)
                self.assertTrue((dest/name).is_file())
                self.assertEqual((dest/name).read_bytes(),expected.read_bytes())
            self.assertIn("kBindingABI=2u",
                          (dest/"DiamondBoundIngress.h").read_text())
            self.assertIn("CABAL_DIAMOND_MERIT_PROOF_VERSION 2u",
                          (dest/"diamond_merit_world_entry.h").read_text())

    def test_refuse_preexisting_header_without_partial_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            dest=pathlib.Path(folder)
            (dest/"diamond_abi.h").write_text("preexisting",encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError,"already installed"):
                PATCHER.copy_native_headers(dest)
            self.assertEqual([x.name for x in dest.iterdir()],["diamond_abi.h"])
            self.assertEqual((dest/"diamond_abi.h").read_text(),"preexisting")

    def test_bind_symbol_is_v2_only(self):
        script=(HERE/"Apply-DiamondBoundClone.py").read_text()
        self.assertIn("cabal_diamond_proc_bind_shadow_clone_v2",script)
        self.assertNotIn("cabal_diamond_proc_bind_shadow_clone_v1",script)

if __name__=="__main__":
    unittest.main()
