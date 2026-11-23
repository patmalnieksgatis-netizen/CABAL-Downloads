"""No-VM tests: source-hash and anti-deployment gates for offline v14 builder."""
import importlib.util
import hashlib
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
            with self.assertRaisesRegex(RuntimeError,"original v291 baseline lib.so SHA mismatch"):
                mod.run(self.fake(src,root/"missing.so",output))
            self.assertFalse(output.exists())
    def test_output_overlap_and_install_dirs_rejected_first(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp)
            src=root/"src";src.mkdir()
            with self.assertRaisesRegex(RuntimeError,"output must be an isolated /tmp directory"):
                mod.run(self.fake(src,root/"missing.so",
                                  pathlib.Path("/usr/lib/cabal/diamond_bad.so")))
            with self.assertRaisesRegex(RuntimeError,"source/output overlap"):
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
    def test_dispatch_bytes_extracted_from_compiled_cpp(self):
        import subprocess
        import shutil
        if not shutil.which("g++") or not shutil.which("objdump"):
            self.skipTest("compiler or objdump unavailable")
        with tempfile.TemporaryDirectory() as temp:
            base=pathlib.Path(temp)
            src=base/"proc.cpp"
            src.write_text(
                'struct PROCESSDATACONTEXT {};\\n'
                'struct ProcSystem { int DoProcessDataCtx(void*,PROCESSDATACONTEXT*); };\\n'
                'int ProcSystem::DoProcessDataCtx(void*,PROCESSDATACONTEXT*) { return 42; }\\n'
            .replace('\\\\n','\\n'))
            so=base/"fixture.so"
            subprocess.run(["g++","-std=c++17","-O2","-shared","-fPIC",
                            str(src),"-o",str(so)],check=True)
            body=mod.dispatch_bytes(so)
            self.assertGreater(len(body),1)
            self.assertLess(len(body),256)
    def test_gcc_nm_export_parser_and_status(self):
        data="0000000000002220 W _ZNSt6vectorIPvSaIS0_EE17_M_realloc_appendIJRKS0_EEEvDpOT_\n0000000000001010 T _Z10CriticalFnv\n                 U puts@GLIBC_2.2.5\n"
        symbols=mod.compiled_exports(data)
        self.assertEqual(len(symbols),2)
        self.assertEqual(symbols["_Z10CriticalFnv"],("T",0x1010))
        self.assertEqual(mod.RECONSTRUCTED_NAME,
                         "libDiamondV14_ORIGINAL_RECONSTRUCTED_OFFLINE.so")
    def test_0bda_passive_getter_export_and_dispatch_machine_code_required(self):
        source=FILE.read_text()
        self.assertIn('OBSERVER_EXPORT="cabal_diamond_0bda_passive_hits_v1"',source)
        self.assertIn('observer_dispatch=dispatch_bytes(observer)',source)
        self.assertIn('if not observer_bytes_differ:',source)
        self.assertIn('observer_new_losses or observer_strong_losses',source)
        self.assertIn('"observer_changes_world_inventory_sql":False',source)
        self.assertIn('"observer_forwards_all_packets_to_original_dispatch":True',source)
        self.assertIn("OUTPUT",source.upper())
        self.assertNotIn("dlopen(",source)
    def test_minimal_0bda_patch_adds_no_cpp_and_keeps_original_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            original=root/"original"
            original.mkdir()
            proc=original/"hooks/Handlers/ProcSystem.cpp"
            proc.parent.mkdir(parents=True)
            source=(
                '#include "../Packets/OpCodes.h"\n'
                'int ProcSystem::DoProcessDataCtx(void* pProcessLayer, PROCESSDATACONTEXT* pProcessDataCtx) {\n'
                '    UINT16 opcode = header->wMainCmd;\n'
                '    return ((int(*)(void*, PROCESSDATACONTEXT*))oDoProcessDataCtx)(pProcessLayer, pProcessDataCtx);\n'
                '}\n'
            )
            proc.write_text(source)
            types_file=original/"include/Types.h"
            types_file.parent.mkdir(parents=True)
            t="struct PROCESSDATACONTEXT {\n    char* cpPacket;\n    // ... other fields\n};\n"
            types_file.write_text(t)
            for i in range(10):
                (original/f"one{i}.cpp").write_text("void foo() {}\n")
            def sha(data):
                return hashlib.sha256(data).hexdigest()
            def replace_one(before,old,new):
                if before.count(old)!=1:raise RuntimeError("anchor mismatch")
                return before.replace(old,new)
            fake=types.SimpleNamespace(
                V14_FILE_COUNT=12,V14_TREE_SHA="dummy",
                PROC_SHA=sha(source.encode()),TYPES_SHA=sha(t.encode()),
                sha_bytes=sha,manifest=lambda _: (12,"dummy"),
                replace_one=replace_one
            )
            staged=root/"patched"
            mod.minimal_pure_0bda_patch(original,staged,fake)
            observer=root/"observer"
            mod.passive_observer_patch(staged,observer)
            self.assertEqual(len(mod.source_list(observer)),
                             len(mod.source_list(original)))
            observed=(observer/"hooks/Handlers/ProcSystem.cpp").read_text()
            self.assertEqual(observed.count(
                "cabal_diamond_0bda_passive_hits_v1"),1)
            self.assertEqual(observed.count(
                "__atomic_fetch_add(&g_diamond0bda_passive_hits"),1)
            self.assertEqual(observed.count(
                "__atomic_load_n(&g_diamond0bda_passive_hits"),1)
            self.assertIn("return ((int(*)(void*, PROCESSDATACONTEXT*))oDoProcessDataCtx)",observed)
            self.assertNotIn("GameData",observed)
            self.assertNotIn("sqlcmd",observed)
            self.assertNotIn("LD_PRELOAD",observed)
            self.assertNotIn("supervisorctl",observed)
            self.assertEqual(len(mod.source_list(original)),
                             len(mod.source_list(staged)))
            self.assertEqual(len(mod.source_list(staged)),11)
            output=(staged/"hooks/Handlers/ProcSystem.cpp").read_text()
            self.assertEqual(output.count("DiamondReal0BDAIngressPort::Process"),1)
            self.assertIn("return ((int(*)(void*, PROCESSDATACONTEXT*))oDoProcessDataCtx)",output)
            self.assertNotIn("DiamondBoundIngress",output)
            self.assertNotIn("DiamondIngress::",output)
            self.assertIn("static_assert(offsetof(PROCESSDATACONTEXT,iLen)==16",
                          (staged/"include/Types.h").read_text())
            self.assertEqual(source,proc.read_text())
            self.assertFalse((original/"hooks/Handlers/DiamondReal0BDAIngressPort.h").exists())
            self.assertTrue((staged/"hooks/Handlers/DiamondReal0BDAIngressPort.h").exists())
    def test_name_and_includes(self):
        text=(HERE/"Apply-DiamondV14Real0BDAClone.py").read_text()
        self.assertIn("BASE=HERE/\"Apply-DiamondV14BoundClone.py\"",text)
        self.assertIn("base.manifest(source)",text)
        self.assertIn("base.patch(source,stage)",text)
        self.assertIn("DiamondReal0BDAIngressPort::Process",text)
        self.assertIn("BINDER_ENABLED=NO",text)

if __name__=="__main__":
    unittest.main()
