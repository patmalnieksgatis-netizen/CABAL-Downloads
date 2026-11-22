#!/usr/bin/env python3
"""Strict link preflight for exact-source CABAL v291 Diamond *offline clone*.

This never loads a game library or starts a server. It does NOT verify a
production WorldSvr, player inventory, MSSQL, client reply or gameplay. The
required native library is an already built synthetic/offline Diamond engine.
Output is deliberately NOT named lib.so and has a clone-only SONAME.
"""
import argparse
import hashlib
import pathlib
import shutil
import subprocess
import sys

SONAME="libDiamondWorldCloneOffline.so"
V2_BIND="cabal_diamond_proc_bind_shadow_clone_v3"
V1_BIND="cabal_diamond_proc_bind_shadow_clone_v1"
V2_MERIT="cabal_diamond_merit_verified_shadow_route"
CURRENT_LIB_SO_SHA256="6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab"
TEST_INGRESS="cabal_diamond_proc_test_ingress_clone_v3"

def exports(path):
    output=subprocess.run(["nm","-D","--defined-only",str(path)],
                          text=True,capture_output=True,check=True).stdout
    return {fields[-1] for row in output.splitlines()
            if (fields:=row.split()) and len(fields)>=3 and
               fields[-2] in ("T","W","D","B","V","u")}

def require(condition,message):
    if not condition:
        raise RuntimeError("STOP: "+message)

def run(root: pathlib.Path,native_lib: pathlib.Path,merit_cpp: pathlib.Path,
        output: pathlib.Path,compiler="g++",baseline_lib=None):
    root=root.resolve()
    native_lib=native_lib.resolve()
    merit_cpp=merit_cpp.resolve()
    output=output.resolve()
    require(root.is_dir(),"clone source absent")
    require(output.name==SONAME,"output must have clone-only SONAME")
    require(not output.exists(),"refuse overwrite")
    require(output!=native_lib and output!=merit_cpp and output not in root.parents
            and root not in output.parents,"output must be outside input trees")
    if baseline_lib is not None:
        baseline_lib=baseline_lib.resolve()
        require(baseline_lib.is_file(),"baseline lib.so absent")
        require(hashlib.sha256(baseline_lib.read_bytes()).hexdigest()==
                CURRENT_LIB_SO_SHA256,"baseline current lib.so SHA changed")
    require(native_lib.is_file() and native_lib.name=="libDiamondNative.so",
            "offline native library not found")
    require(merit_cpp.is_file(),"native verified Merit entry source absent")
    require(shutil.which(compiler) is not None,"C++ compiler not found")
    for util in ("nm","readelf"):
        require(shutil.which(util) is not None,util+" unavailable")
    proc=root/"hooks/Handlers/ProcSystem.cpp"
    bind=root/"hooks/Handlers/DiamondBoundIngress.h"
    state=root/"include/Types.h"
    require(proc.is_file() and bind.is_file() and state.is_file(),
            "source clone missing critical files")
    require(V2_BIND in proc.read_text() and TEST_INGRESS in proc.read_text() and
            V1_BIND not in proc.read_text() and
            "kBindingABI=3u" in bind.read_text(),
            "source clone must use new WorldSvr ABI v2")
    require(V2_MERIT in merit_cpp.read_text() and
            "DIAMOND_ENABLE_SHADOW_TRIAL" in merit_cpp.read_text(),
            "verified native Merit bridge is missing or not gated")

    native_symbols=subprocess.run(
        ["nm","-D","--defined-only",str(native_lib)],
        text=True,capture_output=True,check=True).stdout
    require("cabal_diamond_world_execute" in native_symbols and
            "cabal_diamond_evaluate" in native_symbols,
            "native rules library missing required world bridge and evaluator")

    sources=sorted(root.rglob("*.cpp"))
    require(len(sources)>=10,"incomplete archived source clone")
    # V14 source patcher copies the exact native Merit implementation directly
    # into the clone; the archived-source variant keeps it externally. NEVER
    # compile the same translation unit twice.
    extra_merit=[] if merit_cpp in sources else [merit_cpp]
    if extra_merit:
        require(not any(p.name in ("diamond_merit_world_entry.cpp",
                                  "diamond_merit_world_entry_v2.cpp")
                        for p in sources),
                "refuse ambiguous duplicate Merit bridge implementation")
    # Object/list order matters: libraries MUST follow the compiled sources.
    # -z defs refuses missing SQL ODBC and native gate dependencies.
    cmd=[compiler,"-std=c++17","-O2","-fPIC",
         "-DDIAMOND_ENABLE_SHADOW_TRIAL","-I"+str(root/"include"),
         "-shared","-Wl,-z,defs","-Wl,-soname,"+SONAME,
         "-o",str(output)]
    cmd.extend(str(source) for source in sources)
    cmd.extend([*(str(p) for p in extra_merit),"-L"+str(native_lib.parent),
                "-lDiamondNative","-lodbc","-Wl,-rpath,$ORIGIN"])
    output.parent.mkdir(parents=True,exist_ok=True)
    try:
        subprocess.run(cmd,check=True)
        symbols=subprocess.run(
            ["nm","-D","--defined-only",str(output)],
            text=True,capture_output=True,check=True).stdout
        deps=subprocess.run(["readelf","-d",str(output)],
                            text=True,capture_output=True,check=True).stdout
        if baseline_lib is not None:
            missing=exports(baseline_lib)-exports(output)
            require(not missing,"candidate loses current v291 extension exports: "+
                    ",".join(sorted(missing)[:12]))
        require(V2_BIND in symbols and V2_MERIT in symbols and
                TEST_INGRESS in symbols and V1_BIND not in symbols,
                "missing/new and stale exported ABI mismatch")
        require("Library soname: ["+SONAME+"]" in deps and
                "Shared library: [libDiamondNative.so]" in deps and
                "Shared library: [libodbc.so.2]" in deps and
                "Shared library: [lib.so]" not in deps,
                "unexpected ELF identity or dependencies")
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    print("DIAMOND_OFFLINE_WORLDSVR_SOURCE_LINK=PASS")
    print("BINDER="+V2_BIND+";MERIT_ROUTE="+V2_MERIT)
    print("SYNTHETIC_ONLY_DLOPEN_ENTRY="+TEST_INGRESS)
    print("STRICT_UNDEFINED_SYMBOL_CHECK=PASS;ODBC_LINKED=YES")
    print("CURRENT_EXTENSION_EXPORTED_ABI_PRESERVED="+
          ("PASS" if baseline_lib is not None else "NOT_CHECKED"))
    print("SONAME="+SONAME+";PRODUCTION_LIB_SO=UNTOUCHED")
    print("WORLD_SERVER_EXECUTION=NO;CLIENT_MSSQL_INVENTORY=NO")
    print("OUTPUT="+str(output))

if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--clone-source",type=pathlib.Path,required=True)
    ap.add_argument("--native-lib",type=pathlib.Path,required=True)
    ap.add_argument("--merit-cpp",type=pathlib.Path,required=True)
    ap.add_argument("--output",type=pathlib.Path,required=True)
    ap.add_argument("--compiler",default="g++")
    ap.add_argument("--baseline-current-lib",type=pathlib.Path,default=None)
    args=ap.parse_args()
    try:
        run(args.clone_source,args.native_lib,args.merit_cpp,args.output,
            args.compiler,args.baseline_current_lib)
    except (Exception,subprocess.CalledProcessError) as exc:
        print("DIAMOND_OFFLINE_WORLDSVR_SOURCE_LINK=STOP: "+str(exc),file=sys.stderr)
        sys.exit(1)
