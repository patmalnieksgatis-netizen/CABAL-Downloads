#!/usr/bin/env python3
"""Diagnose an exact-source 0BDA offline module build without modifying WorldSvr.

Build TWO isolated libraries using the SAME current compiler/linker settings:
1. untouched v14 sources, to measure reconstruction/toolchain differences,
2. patched 0BDA v14 source COPY, to measure differences added by the hook.

Do not confuse compiler-generated weak C++ template export drift with a
demonstrated loss of a host ABI. However, *never* claim deployment-safe
parity unless every original dynamic exported symbol is present.
This tool NEVER installs, loads, or activates the library.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys

HERE=pathlib.Path(__file__).resolve().parent
BASELINE_SHA="6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab"
OFFLINE_NAME="libDiamondV14_0BDA_UNINSTALLED.so"
RECONSTRUCTED_NAME="libDiamondV14_ORIGINAL_RECONSTRUCTED_OFFLINE.so"
MINIMAL_NAME="libDiamondV14_MINIMAL_0BDA_OFFLINE.so"
OBSERVER_NAME="libDiamondV14_OBSERVE_0BDA_OFFLINE.so"
OBSERVER_EXPORT="cabal_diamond_0bda_passive_hits_v1"
DISPATCH_SYMBOL="_ZN10ProcSystem16DoProcessDataCtxEPvP18PROCESSDATACONTEXT"
RESULT_MARKER="DIAMOND_WORLD_0BDA_SOURCE_COMPILE_OFFLINE_ONLY"
EXCLUDED={
    "hooks/Handlers/C2SHandler.cpp",
    "hooks/Packets/EventPassInventoryPersistV282.cpp",
}
# The actual user's first audit yielded this one weak C++ template. It is
# reported as TOOLCHAIN_DRIFT only if the unchanged v14 reconstruction
# ALSO lacks it. This exception NEVER authorizes active deployment.
KNOWN_WEAK_TEMPLATE_DRIFT={
    "_ZNSt6vectorIPvSaIS0_EE17_M_realloc_appendIJRKS0_EEEvDpOT_"
}

def script(name):
    path=HERE/name
    spec=importlib.util.spec_from_file_location(name.replace("-","_"),path)
    if spec is None or spec.loader is None:
        raise RuntimeError("STOP: patch script missing: "+name)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_list(root):
    paths=sorted(p for p in root.rglob("*.cpp")
                 if p.relative_to(root).as_posix() not in EXCLUDED)
    if len(paths)<10:
        raise RuntimeError("STOP: exact v14 source missing compile units")
    return [str(p) for p in paths]

def compiled_exports(nm_output):
    result={}
    for row in nm_output.splitlines():
        pieces=row.split()
        if len(pieces)<3 or pieces[-2] not in ("T","W","D","B","V","u"):
            continue
        try:
            address=int(pieces[0],16)
        except ValueError:
            continue
        result[pieces[-1]]=(pieces[-2],address)
    return result

def compare_exports(live,base,patched):
    """Show drift separately from explicit source hook changes.

    Strong ABI differences are always fatal. Missing weak exports are
    captured as incompatibility; only the exact historically observed weak
    symbol is categorized as probable build/toolchain drift, and ONLY when
    unchanged v14 is missing it too. No missing symbols are concealed.
    """
    live_names=set(live)
    base_names=set(base)
    patched_names=set(patched)
    missing_in_base=sorted(live_names-base_names)
    missing_in_patch=sorted(live_names-patched_names)
    new_patch_losses=sorted(base_names-patched_names)
    strong={"T","D","B","V"}
    strong_base=sorted(n for n in missing_in_base if live[n][0] in strong)
    strong_patch=sorted(n for n in missing_in_patch if live[n][0] in strong)
    weak_reconstruction=sorted(n for n in missing_in_base
                              if live[n][0] in ("W","u"))
    weak_patched=sorted(n for n in missing_in_patch
                       if live[n][0] in ("W","u"))
    recognized_toolchain_weak=sorted(n for n in weak_patched
        if n in KNOWN_WEAK_TEMPLATE_DRIFT and n in weak_reconstruction)
    unexplained_weak=sorted(set(weak_patched)-set(recognized_toolchain_weak))
    changed_source_rvas=sorted(n for n in
        (base_names & patched_names)
        if base[n][0] in ("T","W") and patched[n][0] in ("T","W")
        and base[n][1]!=patched[n][1])
    changed_live_rvas=sorted(n for n in
        (live_names & patched_names)
        if live[n][0] in ("T","W") and patched[n][0] in ("T","W")
        and live[n][1]!=patched[n][1])
    return {
        "live_exported_symbols":len(live),
        "reconstructed_exported_symbols":len(base),
        "patched_exported_symbols":len(patched),
        "missing_live_exports_in_reconstructed":missing_in_base,
        "missing_live_exports_in_patched":missing_in_patch,
        "patch_lost_reconstructed_exports":new_patch_losses,
        "missing_strong_exports_reconstructed":strong_base,
        "missing_strong_exports_patched":strong_patch,
        "known_weak_template_missing_in_both":recognized_toolchain_weak,
        "unexplained_weak_exports_missing":unexplained_weak,
        "source_hook_changed_exported_function_rvas":len(changed_source_rvas),
        "source_hook_changed_symbol_examples":changed_source_rvas[:10],
        "changed_exported_function_rvas_vs_live":len(changed_live_rvas),
        "changed_live_symbol_examples":changed_live_rvas[:10],
        "strict_live_export_parity":not missing_in_patch,
        "no_new_export_loss_caused_by_hook":not new_patch_losses,
    }

def minimal_pure_0bda_patch(original,staged,base):
    """No extra translation unit, no 09F3 observer; only passive 0BDA.

    Verifies the same original 64-file manifest as the full patch.
    This port is deliberately UNBOUND: not a working Diamond handler.
    """
    if staged.exists():
        raise RuntimeError("STOP: minimal output already exists")
    if base.manifest(original)!=(base.V14_FILE_COUNT,base.V14_TREE_SHA):
        raise RuntimeError("STOP: minimal patch source is not original v14")
    if base.sha_bytes((original/"hooks/Handlers/ProcSystem.cpp").read_bytes())!=base.PROC_SHA:
        raise RuntimeError("STOP: unrecognized v14 ProcSystem.cpp")
    if base.sha_bytes((original/"include/Types.h").read_bytes())!=base.TYPES_SHA:
        raise RuntimeError("STOP: unrecognized v14 Types.h")
    shutil.copytree(original,staged)
    types=staged/"include/Types.h"
    t=types.read_text(encoding="utf-8")
    t=base.replace_one(t,"    char* cpPacket;\n    // ... other fields",
        "    char* cpPacket;\n"
        "    std::size_t iLen; // WorldSvr packet length, offset 16\n"
        "    // ... other fields")
    t+='\nstatic_assert(offsetof(PROCESSDATACONTEXT,iLen)==16, "packet context ABI changed");\n'
    types.write_text(t,encoding="utf-8")
    proc=staged/"hooks/Handlers/ProcSystem.cpp"
    source=proc.read_text(encoding="utf-8")
    source=base.replace_one(source,'#include "../Packets/OpCodes.h"',
        '#include "../Packets/OpCodes.h"\n#include "DiamondReal0BDAIngressPort.h"')
    source=base.replace_one(source,"    UINT16 opcode = header->wMainCmd;\n",
        """    UINT16 opcode = header->wMainCmd;
    // Minimal original-v14-only passive candidate. This 0BDA port
    // ALWAYS returns false; no WorldSvr/SQL mutation or S2C send.
    if (opcode == DiamondReal0BDAIngressPort::kOpcode &&
        pProcessDataCtx->pUserCtx &&
        DiamondReal0BDAIngressPort::IsCandidate(
            pProcessDataCtx->cpPacket,pProcessDataCtx->iLen)) {
        int unusedReturn=0;
        if (DiamondReal0BDAIngressPort::Process(
            pProcessDataCtx->pUserCtx,pProcessDataCtx->cpPacket,
            pProcessDataCtx->iLen,&unusedReturn)) {
            return unusedReturn;
        }
    }
""")
    if ("    return ((int(*)(void*, PROCESSDATACONTEXT*))oDoProcessDataCtx)"
        "(pProcessLayer, pProcessDataCtx);" not in source):
        raise RuntimeError("STOP: original WorldSvr dispatcher missing")
    proc.write_text(source,encoding="utf-8")
    port=HERE/"DiamondReal0BDAIngressPort.h"
    if not port.is_file():
        raise RuntimeError("STOP: no fail-closed 0BDA port header")
    shutil.copy2(port,proc.parent/port.name)
    if len(source_list(staged))!=len(source_list(original)):
        raise RuntimeError("STOP: minimal 0BDA stage added C++ translation units")
    if base.manifest(original)!=(base.V14_FILE_COUNT,base.V14_TREE_SHA):
        raise RuntimeError("STOP: minimal patch changed original source")
    return staged

def passive_observer_patch(minimal_source,observer_source):
    """Turn the optimized-away minimal no-op into a measurable passive hook.

    NO additional .cpp, threads, calls to SQL or game callback. The only
    side effect is an atomic counter private to the offline shared object.
    Its exported read-only getter permits verifying the code was retained.
    It never consumes a packet and forwards the ORIGINAL native dispatch.
    """
    if observer_source.exists():
        raise RuntimeError("STOP: observer output already exists")
    shutil.copytree(minimal_source,observer_source)
    proc=observer_source/"hooks/Handlers/ProcSystem.cpp"
    code=proc.read_text(encoding="utf-8")
    mark='#include "DiamondReal0BDAIngressPort.h"'
    declaration="""
// OFFLINE ONLY. Atomic counter contains NO player IDs, IP or packet bytes.
// Exported getter allows read-only verification without mutating gameplay.
static unsigned long long g_diamond0bda_passive_hits = 0;
extern "C" __attribute__((visibility("default")))
unsigned long long cabal_diamond_0bda_passive_hits_v1() noexcept {
    return __atomic_load_n(&g_diamond0bda_passive_hits, __ATOMIC_RELAXED);
}
"""
    hook="        int unusedReturn=0;\n"
    code=code.replace(mark,mark+declaration,1)
    if code.count(hook)!=1:
        raise RuntimeError("STOP: minimal passive hook marker missing")
    code=code.replace(hook,
      """        // Keep the minimal 0BDA branch observable; native dispatch still
        // always executes as before. No SQL/game state or response changes.
        __atomic_fetch_add(&g_diamond0bda_passive_hits, 1ULL,
                           __ATOMIC_RELAXED);
""" + hook,1)
    if code.count(OBSERVER_EXPORT)!=1 or code.count(
            "__atomic_fetch_add(&g_diamond0bda_passive_hits")!=1:
        raise RuntimeError("STOP: exactly one passive counter was not inserted")
    if ("    return ((int(*)(void*, PROCESSDATACONTEXT*))oDoProcessDataCtx)"
        "(pProcessLayer, pProcessDataCtx);" not in code):
        raise RuntimeError("STOP: observer would lose original native dispatch")
    proc.write_text(code,encoding="utf-8")
    if len(source_list(observer_source))!=len(source_list(minimal_source)):
        raise RuntimeError("STOP: observer introduced new translation units")
    return observer_source

def dispatch_bytes(path):
    """Extract dispatch function instruction BYTES (not relabeled offsets).

    Original and no-op minimal should be byte-identical; we require the
    counter-instrumented observer to differ, or STOP. Changes in relative
    jumps/calls can also differ with linker layout; this is a necessary,
    NOT sufficient, proof that an observable hook was compiled.
    """
    out=subprocess.run(["objdump","-d","--disassemble="+DISPATCH_SYMBOL,
                        str(path)],capture_output=True,text=True,
                       check=True,timeout=10).stdout
    body=[]
    seen=False
    for line in out.splitlines():
        if "<"+DISPATCH_SYMBOL+">:" in line:
            seen=True
            continue
        if not seen:
            continue
        if line and not line.startswith((" ","\t")) and line.endswith(":"):
            break
        # objdump often aligns hex-byte column with tabs.
        import re
        m=re.match(r'^\s*[0-9a-f]+:\s+((?:[0-9a-f]{2}\s+)+)',line)
        if m:
            body.extend(bytes.fromhex(m.group(1)))
    if not body:
        raise RuntimeError("STOP: could not disassemble "+DISPATCH_SYMBOL)
    return bytes(body)

def build(compiler,src,destination,name):
    cmd=[compiler,"-std=c++17","-O2","-fPIC","-shared",
         "-Wl,--no-undefined","-Wl,-soname,"+name,
         "-Wl,-rpath,/usr/lib/cabal",
         "-o",str(destination),*source_list(src),"-ldl","-lpthread","-lodbc"]
    proc=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
    if proc.returncode or not destination.is_file():
        raise RuntimeError("STOP: "+name+" offline compilation returned "+
                           str(proc.returncode)+": "+
                           proc.stderr[-1100:].replace("\n"," "))
    return len(source_list(src))

def run(a):
    original=a.source.resolve()
    saved=a.baseline_lib.resolve()
    output=a.output_dir.resolve()
    if output.exists():
        raise RuntimeError("STOP: destination already exists")
    if output==original or original in output.parents or output in original.parents:
        raise RuntimeError("STOP: source/output overlap")
    if output==saved.parent or output in saved.parents:
        raise RuntimeError("STOP: output overlaps active/baseline module")
    if pathlib.Path("/tmp") not in output.parents:
        raise RuntimeError("STOP: output must be an isolated /tmp directory")
    if not saved.is_file() or sha256(saved)!=BASELINE_SHA:
        raise RuntimeError("STOP: original v291 baseline lib.so SHA mismatch")
    base=script("Apply-DiamondV14BoundClone.py")
    patch=script("Apply-DiamondV14Real0BDAClone.py")
    if not original.is_dir() or base.manifest(original)!=(
        base.V14_FILE_COUNT,base.V14_TREE_SHA):
        raise RuntimeError("STOP: wrong original v14 64-file source manifest")
    if not shutil.which(a.compiler):
        raise RuntimeError("STOP: missing C++ compiler")
    for executable in ("nm","readelf"):
        if not shutil.which(executable):
            raise RuntimeError("STOP: missing "+executable)
    output.mkdir(parents=True,exist_ok=False)
    reconstructed=output/RECONSTRUCTED_NAME
    minimal=output/MINIMAL_NAME
    observer=output/OBSERVER_NAME
    candidate=output/OFFLINE_NAME
    result_file=output/"OFFLINE_BUILD_RESULT.json"
    try:
        unit_count=build(a.compiler,original,reconstructed,RECONSTRUCTED_NAME)
        minimal_pure_0bda_patch(original,output/"minimal-source",base)
        minimal_count=build(a.compiler,output/"minimal-source",minimal,MINIMAL_NAME)
        if unit_count!=minimal_count:
            raise RuntimeError("STOP: 0BDA minimal variant changed compile units")
        passive_observer_patch(
            output/"minimal-source",output/"observer-source")
        observer_count=build(
            a.compiler,output/"observer-source",observer,OBSERVER_NAME)
        if observer_count!=unit_count:
            raise RuntimeError("STOP: observer added extra C++ files")
        patch.patch(original,output/"source")
        patched_units=build(a.compiler,output/"source",candidate,OFFLINE_NAME)
        if not (output/"source/hooks/Handlers/ProcSystem.cpp").read_text().count(
            "if (opcode == DiamondReal0BDAIngressPort::kOpcode")==1:
            raise RuntimeError("STOP: safe 0BDA port was not hooked once")
        for lib,soname in ((reconstructed,RECONSTRUCTED_NAME),
                           (minimal,MINIMAL_NAME),
                           (observer,OBSERVER_NAME),
                           (candidate,OFFLINE_NAME)):
            dynamic=subprocess.run(["readelf","-d",str(lib)],
                capture_output=True,text=True,timeout=10,check=True).stdout
            if "Library soname: ["+soname+"]" not in dynamic or (
                "Library soname: [lib.so]" in dynamic):
                raise RuntimeError("STOP: offline shared library SONAME mismatch")
        def nm(path):
            return compiled_exports(subprocess.run(
                ["nm","-D","--defined-only",str(path)],capture_output=True,
                text=True,timeout=10,check=True).stdout)
        live_exports=nm(saved)
        original_exports=nm(reconstructed)
        minimal_exports=nm(minimal)
        observer_exports=nm(observer)
        final_exports=nm(candidate)
        # Verify a real, *observable* branch survived compiler DCE.
        if OBSERVER_EXPORT not in observer_exports or (
            OBSERVER_EXPORT in original_exports or
            OBSERVER_EXPORT in minimal_exports):
            raise RuntimeError("STOP: 0BDA passive counter export collision")
        original_dispatch=dispatch_bytes(reconstructed)
        minimal_dispatch=dispatch_bytes(minimal)
        observer_dispatch=dispatch_bytes(observer)
        observer_bytes_differ=observer_dispatch!=original_dispatch
        if not observer_bytes_differ:
            raise RuntimeError("STOP: passive 0BDA observer optimized away")
        assessment=compare_exports(live_exports,original_exports,final_exports)
        minimal_assessment=compare_exports(
            live_exports,original_exports,minimal_exports)
        observer_assessment=compare_exports(
            live_exports,original_exports,observer_exports)
        observer_new_losses=observer_assessment["patch_lost_reconstructed_exports"]
        observer_strong_losses=observer_assessment["missing_strong_exports_patched"]
        minimal_new_losses=minimal_assessment["patch_lost_reconstructed_exports"]
        minimal_strong_losses=minimal_assessment["missing_strong_exports_patched"]
        strong_fail=(assessment["missing_strong_exports_reconstructed"] or
                     assessment["missing_strong_exports_patched"])
        source_new_loss=assessment["patch_lost_reconstructed_exports"]
        weak_other=assessment["unexplained_weak_exports_missing"]
        if strong_fail or source_new_loss or weak_other or (
            minimal_new_losses or minimal_strong_losses or
            observer_new_losses or observer_strong_losses):
            verdict="STOP_ABI_INCOMPATIBLE"
        elif assessment["strict_live_export_parity"]:
            verdict="OFFLINE_STRICT_EXPORT_PARITY_PASS"
        else:
            verdict="OFFLINE_RECONSTRUCTED_TOOLCHAIN_WEAK_DRIFT"
        result={
            "status":verdict,
            "real_game_runtime_verified":False,
            "active_worldsvr_modified":False,
            "sql_game_data_modified":False,
            "worldsvr_started":False,
            "s2c_0bda_reply_verified":False,
            "can_install_on_active_worldsvr":False,
            "diamond_gameplay_enabled":False,
            "original_lib_sha256":BASELINE_SHA,
            "reconstructed_sha256":sha256(reconstructed),
            "minimal_candidate_sha256":sha256(minimal),
            "candidate_sha256":sha256(candidate),
            "minimal_candidate_soname":MINIMAL_NAME,
            "minimal_source_cpp_units":minimal_count,
            "minimal_hook_newly_lost_exports":minimal_new_losses,
            "minimal_hook_missing_strong_exports":minimal_strong_losses,
            "minimal_vs_original_function_rva_moves":
                minimal_assessment["source_hook_changed_exported_function_rvas"],
            "minimal_vs_live_function_rva_moves":
                minimal_assessment["changed_exported_function_rvas_vs_live"],
            "minimal_strict_live_export_parity":
                minimal_assessment["strict_live_export_parity"],
            "minimal_hook_unused_by_game":True,
            "minimal_dispatch_bytes_equal_original":
                minimal_dispatch==original_dispatch,
            "observer_candidate_sha256":sha256(observer),
            "observer_soname":OBSERVER_NAME,
            "observer_compiled_cpp_units":observer_count,
            "observer_exported_counter":OBSERVER_EXPORT,
            "observer_counter_is_read_only":True,
            "observer_dispatch_bytes_differ_from_original":
                observer_bytes_differ,
            "observer_newly_lost_exports":observer_new_losses,
            "observer_missing_strong_exports":observer_strong_losses,
            "observer_rva_moves_vs_rebuilt_original":
                observer_assessment["source_hook_changed_exported_function_rvas"],
            "observer_rva_moves_vs_original_live_lib":
                observer_assessment["changed_exported_function_rvas_vs_live"],
            "observer_changes_world_inventory_sql":False,
            "observer_forwards_all_packets_to_original_dispatch":True,
            "candidate_soname":OFFLINE_NAME,
            "source_v14_manifest":base.V14_TREE_SHA,
            "unchanged_v14_cpp_units":unit_count,
            "patched_v14_cpp_units":patched_units,
            **assessment,
        }
        result_file.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",
                               encoding="utf-8")
        if base.manifest(original)!=(base.V14_FILE_COUNT,base.V14_TREE_SHA):
            raise RuntimeError("STOP: source changed during read-only build")
        print("DIAMOND_0BDA_OFFLINE_ABI_AUDIT="+verdict)
        print("MISSING_STRONG_EXPORTS="+
              str(len(assessment["missing_strong_exports_patched"])))
        print("KNOWN_WEAK_DRIFT="+
              str(len(assessment["known_weak_template_missing_in_both"])))
        print("HOOK_CREATED_NEW_EXPORT_LOSSES="+str(len(source_new_loss)))
        print("SOURCE_HOOK_FUNCTION_RVA_MOVES="+
              str(assessment["source_hook_changed_exported_function_rvas"]))
        print("MINIMAL_0BDA_UNCHANGED_CPP_UNITS="+str(minimal_count))
        print("MINIMAL_0BDA_FUNCTION_RVA_MOVES="+str(
            minimal_assessment["source_hook_changed_exported_function_rvas"]))
        print("MINIMAL_0BDA_NEW_EXPORT_LOSSES="+str(len(minimal_new_losses)))
        print("OBSERVER_0BDA_DISPATCH_CODE_RETAINED="+
              ("YES" if observer_bytes_differ else "NO"))
        print("OBSERVER_0BDA_ORIGINAL_CPP_UNITS="+str(observer_count))
        print("OBSERVER_0BDA_RVA_MOVES="+str(
            observer_assessment["source_hook_changed_exported_function_rvas"]))
        print("OBSERVER_0BDA_NEW_EXPORT_LOSSES="+str(len(observer_new_losses)))
        print("ALL_ACTIVE_GAME_AND_SQL_UNCHANGED=YES")
        print("BUILD_REPORT="+str(result_file))
        # ABI incompatibility is an analyzed, informative STOP outcome.
        return result
    except Exception:
        # An error must never leave a misleading candidate .so.
        candidate.unlink(missing_ok=True)
        minimal.unlink(missing_ok=True)
        observer.unlink(missing_ok=True)
        raise

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=pathlib.Path,required=True)
    p.add_argument("--baseline-lib",type=pathlib.Path,required=True)
    p.add_argument("--output-dir",type=pathlib.Path,required=True)
    p.add_argument("--compiler",default="g++")
    args=p.parse_args()
    try:
        run(args)
    except (RuntimeError,OSError,subprocess.SubprocessError) as exc:
        print("DIAMOND_0BDA_OFFLINE_ABI_AUDIT=STOP: "+str(exc),file=sys.stderr)
        raise SystemExit(2)
