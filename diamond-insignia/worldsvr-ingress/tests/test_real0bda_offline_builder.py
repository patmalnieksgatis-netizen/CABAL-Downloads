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
    def test_name_and_includes(self):
        text=(HERE/"Apply-DiamondV14Real0BDAClone.py").read_text()
        self.assertIn("BASE=HERE/\"Apply-DiamondV14BoundClone.py\"",text)
        self.assertIn("base.manifest(source)",text)
        self.assertIn("base.patch(source,stage)",text)
        self.assertIn("DiamondReal0BDAIngressPort::Process",text)
        self.assertIn("BINDER_ENABLED=NO",text)

if __name__=="__main__":
    unittest.main()
