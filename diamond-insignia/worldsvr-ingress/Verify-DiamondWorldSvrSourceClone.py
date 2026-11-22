#!/usr/bin/env python3
"""Build-check a copy of the exact archived CABAL WorldSvr lib source.

Never installs, loads, injects, executes WorldSvr, touches SQL or changes
the original source. The trial object is *not linked* to a game executable.
"""
import argparse
import hashlib
import pathlib
import shutil
import subprocess
import sys

HERE=pathlib.Path(__file__).resolve().parent
ORIGINAL={
    "hooks/Handlers/ProcSystem.cpp":
        "b687c3bb9607aa886f37bcf203dcf4fb1a315cf6e9a23d4e67adea69e1486d88",
    "include/Types.h":
        "c32a66118f439cf1a1279f703c3a9a1e272a4dfbb89a0745c93983ce5a2e3b61",
}
ABI_V2_SYMBOL="cabal_diamond_proc_bind_shadow_clone_v3"
OLD_BIND_SYMBOL="cabal_diamond_proc_bind_shadow_clone_v1"

def digest(path):
    value=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            value.update(block)
    return value.hexdigest()

def insist_original(source):
    for rel, expected in ORIGINAL.items():
        path=source/rel
        if not path.is_file() or digest(path)!=expected:
            raise RuntimeError("STOP: source missing or incompatible: "+rel)

def object_symbols(obj):
    response=subprocess.run(["nm","-g",str(obj)],capture_output=True,text=True,check=True)
    defined=set()
    for row in response.stdout.splitlines():
        fields=row.split()
        if len(fields)>=3 and fields[-2] in ("T","W"):
            defined.add(fields[-1])
    return defined

def run(source,output,compiler):
    source=source.resolve()
    output=output.resolve()
    if not source.is_dir() or output.exists() or output==source or (
        source in output.parents or output in source.parents):
        raise RuntimeError("STOP: source invalid or output overlaps or exists")
    insist_original(source)
    compiler_path=shutil.which(compiler)
    if not compiler_path:
        raise RuntimeError("STOP: C++ compiler unavailable")
    command=[sys.executable,str(HERE/"Apply-DiamondBoundClone.py"),
             "--source",str(source),"--output",str(output)]
    subprocess.run(command,check=True)
    insist_original(source)
    proc=output/"hooks"/"Handlers"/"ProcSystem.cpp"
    if not proc.is_file() or digest(proc)==ORIGINAL["hooks/Handlers/ProcSystem.cpp"]:
        raise RuntimeError("STOP: patched ProcSystem.cpp not produced")
    for name in ("DiamondIngress.h","DiamondBoundIngress.h","diamond_abi.h",
                 "diamond_world_bridge.h","diamond_merit_world_entry.h"):
        if not (proc.parent/name).is_file():
            raise RuntimeError("STOP: clone source header missing: "+name)
    objects={}
    for enabled in (False,True):
        label="trial" if enabled else "default"
        target=output/("ProcSystem_Diamond_"+label+".o")
        build=[compiler_path,"-std=c++17","-fPIC","-I"+str(output/"include"),
               "-Wno-unused-function"]
        if enabled:
            build.append("-DDIAMOND_ENABLE_SHADOW_TRIAL")
        build+=["-c",str(proc),"-o",str(target)]
        subprocess.run(build,check=True)
        symbols=object_symbols(target)
        if (ABI_V2_SYMBOL in symbols)!=enabled or OLD_BIND_SYMBOL in symbols:
            raise RuntimeError("STOP: wrong default/clone binder ABI: "+label)
        objects[label]=target.name
    insist_original(source)
    print("DIAMOND_EXACT_ARCHIVED_SOURCE_CLONE_BUILD=PASS")
    print("DEFAULT_BIND_EXPORT=ABSENT")
    print("TRIAL_BIND_EXPORT="+ABI_V2_SYMBOL)
    print("ORIGINAL_SOURCE_HASHES=UNCHANGED")
    print("LIVE_WORLDSVR_CLIENT_SQL=UNTOUCHED")
    print("LINK_OR_GAMEPLAY_TEST=NOT_PERFORMED")
    print("OUTPUT="+str(output))

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=pathlib.Path,required=True,
                        help="Archived original lib.so source root, not the live server")
    parser.add_argument("--output",type=pathlib.Path,required=True,
                        help="New isolated path, must not exist")
    parser.add_argument("--compiler",default="g++")
    args=parser.parse_args()
    try:
        run(args.source,args.output,args.compiler)
    except (Exception,subprocess.CalledProcessError) as exc:
        print("DIAMOND_EXACT_ARCHIVED_SOURCE_CLONE_BUILD=STOP: "+str(exc),
              file=sys.stderr)
        sys.exit(1)
