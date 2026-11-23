"""No-VM tests: source-hash and anti-deployment gates for offline v14 builder."""
import importlib.util
import pathlib
import tempfile
import types
import unittest

HERE=pathlib.Path(__file__).resolve().parents[1]
FILE=HERE/"Build-DiamondV14Real0BDAOffline.py"
spec=importlib.util.spec_from_file_location("diamond_offline_0bda_builder",FILE)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class Safety(unittest.TestCase):
    def fake(self,source,baseline,output):
        return types.SimpleNamespace(source=source,baseline_lib=baseline,
            output_dir=output,compiler="g++")
    def test_offline_artifact_cannot_masquerade_as_original_library(self):
        self.assertEqual(mod.OFFLINE_NAME,"libDiamondV14_0BDA_UNINSTALLED.so")
        self.assertNotEqual(mod.OFFLINE_NAME,"lib.so")
        self.assertEqual(len(mod.BASELINE_SHA),64)
        self.assertIn("hooks/Handlers/C2SHandler.cpp",mod.EXCLUDED)
        self.assertIn("hooks/Packets/EventPassInventoryPersistV282.cpp",mod.EXCLUDED)
        source=FILE.read_text()
        for unsafe in ("supervisorctl","docker exec","LD_PRELOAD=",
                       "os.replace(","os.rename(","shutil.move(",
                       "systemctl restart","sqlcmd "):
            self.assertNotIn(unsafe,source.replace(
                "Never runs Docker, supervisorctl, SQL, LD_PRELOAD, or a WorldSvr process.",""))
    def test_missing_baseline_rejected_before_staging_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp)
            src=root/"src";src.mkdir()
            output=pathlib.Path("/tmp")/("diamond_real0bda_nonexistent_source_"+root.name)
            if output.exists():self.skipTest("test output exists from another run")
            with self.assertRaisesRegex(RuntimeError,"original exact v291"):
                mod.run(self.fake(src,root/"missing.so",output))
            self.assertFalse(output.exists())
    def test_output_overlap_and_install_dirs_rejected_first(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp)
            src=root/"src";src.mkdir()
            with self.assertRaisesRegex(RuntimeError,"destination MUST be inside /tmp"):
                mod.run(self.fake(src,root/"missing.so",
                                  pathlib.Path("/usr/lib/cabal/diamond_bad.so")))
            with self.assertRaisesRegex(RuntimeError,"source/output paths overlap"):
                mod.run(self.fake(src,root/"missing.so",src/"clone"))
            self.assertFalse((src/"clone").exists())
    def test_real_weak_cpp_symbol_needs_same_loss_in_unpatched_rebuild(self):
        # Actual observed symbol from the user's 2026-11-23 VM log.
        weak="_ZNSt6vectorIPvSaIS0_EE17_M_realloc_appendIJRKS0_EEEvDpOT_"
        old={"_ZN4Game8HandleEv":("T",0x1110),weak:("W",0x2220)}
        base={"_ZN4Game8HandleEv":("T",0x1110)}
        patch={"_ZN4Game8HandleEv":("T",0x1230)}
        a=mod.compare_exports(old,base,patch)
        self.assertEqual(a["missing_live_exports_in_patched"],[weak])
        self.assertEqual(a["known_weak_template_missing_in_both"],[weak])
        self.assertEqual(a["missing_strong_exports_patched"],[])
        self.assertEqual(a["patch_lost_reconstructed_exports"],[])
        self.assertFalse(a["strict_live_export_parity"])
        self.assertTrue(a["no_new_export_loss_caused_by_hook"])
        self.assertEqual(a["source_hook_changed_exported_function_rvas"],1)
        # If unchanged source HAD the weak export, losing it during
        # the hook compile is a NEW and unapproved source-change loss.
        base_with_weak=dict(old)
        b=mod.compare_exports(old,base_with_weak,patch)
        self.assertEqual(b["patch_lost_reconstructed_exports"],[weak])
        self.assertEqual(b["known_weak_template_missing_in_both"],[])
        self.assertEqual(b["unexplained_weak_exports_missing"],[weak])
    def test_strong_export_loss_not_reclassified_as_toolchain_difference(self):
        live={"_Z10CriticalFnv":("T",0x1010),
              "_ZNSt6vectorIPvSaIS0_EE17_M_realloc_appendIJRKS0_EEEvDpOT_":("W",0x2020)}
        rebuilt={}
        patched={}
        c=mod.compare_exports(live,rebuilt,patched)
        self.assertIn("_Z10CriticalFnv",c["missing_strong_exports_patched"])
        self.assertFalse(c["strict_live_export_parity"])
    def test_gcc_nm_export_parser_and_status(self):
        data="0000000000002220 W _ZNSt6vectorIPvSaIS0_EE17_M_realloc_appendIJRKS0_EEEvDpOT_\n0000000000001010 T _Z10CriticalFnv\n                 U puts@GLIBC_2.2.5\n"
        symbols=mod.compiled_exports(data)
        self.assertEqual(len(symbols),2)
        self.assertEqual(symbols["_Z10CriticalFnv"],("T",0x1010))
        self.assertEqual(mod.RECONSTRUCTED_NAME,
                         "libDiamondV14_ORIGINAL_RECONSTRUCTED_OFFLINE.so")
    def test_name_and_includes(self):
        text=(HERE/"Apply-DiamondV14Real0BDAClone.py").read_text()
        self.assertIn("BASE=HERE/\"Apply-DiamondV14BoundClone.py\"",text)
        self.assertIn("base.manifest(source)",text)
        self.assertIn("base.patch(source,stage)",text)
        self.assertIn("DiamondReal0BDAIngressPort::Process",text)
        self.assertIn("BINDER_ENABLED=NO",text)

if __name__=="__main__":
    unittest.main()
