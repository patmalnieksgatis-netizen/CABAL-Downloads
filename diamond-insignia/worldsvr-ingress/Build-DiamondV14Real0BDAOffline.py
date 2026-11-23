#!/usr/bin/env python3
"""Build a strictly NON-INSTALLABLE CABAL v291 0x0BDA source integration.

Runs ONLY a source-copy patch + offline C++ shared-object build using the
owner's exact 64-file v14 source tree and matching original lib.so backup.

Never runs Docker, supervisorctl, SQL, LD_PRELOAD, or a WorldSvr process.
Never edits the original source, active .so, game client or existing configs.
The result has a NON-game SONAME and cannot be used as a direct lib.so
replacement. The safe 0BDA port forwards all packets to original dispatch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys

HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import importlib.util

def load_script(name):
    path=HERE/name
    spec=importlib.util.spec_from_file_location(name.replace("-","_"),path)
    if not spec or not spec.loader:raise RuntimeError("STOP: missing patcher "+name)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

PATCH=load_script("Apply-DiamondV14Real0BDAClone.py")
BASE=load_script("Apply-DiamondV14BoundClone.py")
BASELINE_SHA="6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab"
OFFLINE_NAME="libDiamondV14_0BDA_UNINSTALLED.so"
EXCLUDED={
    "hooks/Handlers/C2SHandler.cpp",
    "hooks/Packets/EventPassInventoryPersistV282.cpp",
}
# A successful build is NEVER proof of gameplay/WorldSvr startup compatibility.
RESULT_MARKER="DIAMOND_WORLD_0BDA_SOURCE_COMPILE_OFFLINE_ONLY"

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(args):
    src=args.source.resolve()
    output=args.output_dir.resolve()
    baseline=args.baseline_lib.resolve()
    if output.exists():
        raise RuntimeError("STOP: output directory already exists")
    if output==src or src in output.parents or output in src.parents:
        raise RuntimeError("STOP: source/output paths overlap")
    if output==baseline.parent or output in baseline.parents:
        raise RuntimeError("STOP: output overlaps baseline game module")
    # Deliberately write only to a fresh /tmp tree; never a game mount.
    if output!=pathlib.Path("/tmp") and pathlib.Path("/tmp") not in output.parents:
        raise RuntimeError("STOP: staging destination MUST be inside /tmp")
    if not baseline.is_file() or sha256(baseline)!=BASELINE_SHA:
        raise RuntimeError("STOP: original exact v291 lib.so SHA mismatch")
    if not src.is_dir() or BASE.manifest(src)!=(
            BASE.V14_FILE_COUNT,BASE.V14_TREE_SHA):
        raise RuntimeError("STOP: exact 64-file v14 input is unavailable")
    if shutil.which(args.compiler) is None:
        raise RuntimeError("STOP: no C++ compiler")
    for utility in ("nm","readelf"):
        if shutil.which(utility) is None:
            raise RuntimeError("STOP: "+utility+" not installed")

    patch_root=output/"source"
    lib_path=output/OFFLINE_NAME
    try:
        output.mkdir(parents=True,exist_ok=False)
        PATCH.patch(src,patch_root)
        included=[]
        for file in sorted(patch_root.rglob("*.cpp")):
            relative=file.relative_to(patch_root).as_posix()
            if relative not in EXCLUDED:
                included.append(str(file))
        if len(included)<10:
            raise RuntimeError("STOP: insufficient exact source input units")
        cmd=[args.compiler,"-std=c++17","-O2","-fPIC","-shared",
             "-Wl,--no-undefined","-Wl,-soname,"+OFFLINE_NAME,
             "-Wl,-rpath,/usr/lib/cabal",
             "-o",str(lib_path),*included,"-ldl","-lpthread","-lodbc"]
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=240)
        if p.returncode or not lib_path.is_file():
            # Do not print shell command, credentials or arbitrary logs.
            raise RuntimeError("STOP: offline C++ link failed (exit="+
                               str(p.returncode)+"); compiler tail: "+
                               (p.stderr[-1400:].replace("\n"," ") or "none"))
        original=subprocess.run(
            ["nm","-D","--defined-only",str(baseline)],
            capture_output=True,text=True,check=True,timeout=10).stdout
        built=subprocess.run(
            ["nm","-D","--defined-only",str(lib_path)],
            capture_output=True,text=True,check=True,timeout=10).stdout
        def symbols(data):
            found=set()
            for line in data.splitlines():
                fields=line.split()
                if len(fields)>=3 and fields[-2] in ("T","W","D","B","V","u"):
                    found.add(fields[-1])
            return found
        old_symbols=symbols(original)
        candidate_symbols=symbols(built)
        missing=sorted(old_symbols-candidate_symbols)
        # The earlier source-matched lib.so replacement moved over 100
        # exported RVAs and failed startup with exit 78. This static
        # audit quantifies the same risk but NEVER approves deployment.
        def addresses(data):
            parsed={}
            for line in data.splitlines():
                fields=line.split()
                if len(fields)>=3 and fields[-2] in ("T","W"):
                    try:parsed[fields[-1]]=int(fields[0],16)
                    except ValueError:pass
            return parsed
        orig_addresses=addresses(original)
        new_addresses=addresses(built)
        changed_rvas=sorted(n for n in orig_addresses.keys() &
                            new_addresses.keys()
                            if orig_addresses[n]!=new_addresses[n])
        if missing or len(old_symbols)<100:
            raise RuntimeError("STOP: exported ABI loss: "+
                               ",".join(missing[:8]))
        elf=subprocess.run(
            ["readelf","-d",str(lib_path)],
            capture_output=True,text=True,check=True,timeout=10).stdout
        if "Library soname: ["+OFFLINE_NAME+"]" not in elf:
            raise RuntimeError("STOP: offline SONAME mismatch")
        if "Library soname: [lib.so]" in elf:
            raise RuntimeError("STOP: candidate would masquerade as game lib.so")
        if "    if (opcode == DiamondReal0BDAIngressPort::kOpcode" not in (
                patch_root/"hooks/Handlers/ProcSystem.cpp").read_text():
            raise RuntimeError("STOP: original dispatch hook was not inserted")
        report={
            "status":"OFFLINE_SOURCE_LINK_PASS",
            "source_hash_manifest":BASE.V14_TREE_SHA,
            "original_lib_sha256":BASELINE_SHA,
            "candidate_sha256":sha256(lib_path),
            "candidate_soname":OFFLINE_NAME,
            "baseline_exported_symbols":len(old_symbols),
            "candidate_exported_symbols":len(candidate_symbols),
            "missing_original_exports":0,
            "changed_exported_function_rvas":len(changed_rvas),
            "rva_layout_matches_original":len(changed_rvas)==0,
            "example_changed_symbol_names":changed_rvas[:12],
            "source_cpp_units_compiled":len(included),
            "disabled_binder":True,
            "worldsvr_process_started":False,
            "live_so_replaced":False,
            "sql_or_game_data_changed":False,
            "client_response_abi_verified":False,
            "in_game_diamond_enabled":False,
        }
        (output/"OFFLINE_BUILD_RESULT.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        if BASE.manifest(src)!=(BASE.V14_FILE_COUNT,BASE.V14_TREE_SHA):
            raise RuntimeError("STOP: input source changed during offline build")
    except Exception:
        # No potentially misleading half-built replacement artifact.
        if lib_path.exists():lib_path.unlink()
        raise
    print(RESULT_MARKER+"=PASS")
    print("ORIGINAL_EXPORTS_PRESERVED="+str(len(old_symbols)))
    print("CHANGED_EXPORTED_FUNCTION_RVAS="+str(len(changed_rvas)))
    print("RUNTIME_ABI_OR_STARTUP_VERIFIED=NO")
    print("OFFLINE_BUNDLE="+str(output))
    print("ACTIVE_LIB_AND_WORLDSVR_CHANGED=NO")
    print("DIAMOND_GAMEPLAY_ENABLED=NO")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",required=True,type=pathlib.Path)
    p.add_argument("--baseline-lib",required=True,type=pathlib.Path)
    p.add_argument("--output-dir",required=True,type=pathlib.Path)
    p.add_argument("--compiler",default="g++")
    a=p.parse_args()
    try:
        run(a)
    except (RuntimeError,OSError,subprocess.SubprocessError) as exc:
        print(RESULT_MARKER+"=STOP: "+str(exc),file=sys.stderr)
        raise SystemExit(2)
