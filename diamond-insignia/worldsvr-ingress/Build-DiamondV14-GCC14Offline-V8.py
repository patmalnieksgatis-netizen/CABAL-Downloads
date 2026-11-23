#!/usr/bin/env python3
"""V8: optional isolated GCC 14.2 rebuild of untouched Diamond V14.

Never installs, loads, or activates a library. Only touches a fresh /tmp output.
If GCC 14.2 is unavailable, report BLOCKED rather than changing the machine.
"""
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys

SOURCE=pathlib.Path("/root/CABAL_V282_LIVE_MERGE_CANDIDATE_v14/source_tree/src")
LIVE=pathlib.Path("/root/cabal_diamond_backup/lib.so_before_diamond_20261122")
OUT=pathlib.Path("/tmp/cabal_diamond_v291_0bda_gcc14_v8")
LIVE_SHA="6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab"
EXCLUDED={"hooks/Handlers/C2SHandler.cpp","hooks/Packets/EventPassInventoryPersistV282.cpp"}
def invoke(command,timeout=35):
    p=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
    if p.returncode:
        raise RuntimeError("STOP: command "+repr(command[:4])+" exit="+str(p.returncode)+": "+p.stderr[-1000:])
    return p.stdout
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def exported(path):
    result={}
    for line in invoke(["nm","-D","--defined-only",str(path)]).splitlines():
        v=line.split()
        if len(v)==3 and v[1] in ("T","W","D","B","V","u"):
            try:result[v[2]]={"kind":v[1],"rva":int(v[0],16)}
            except ValueError:pass
    return result
def section(path):
    for line in invoke(["readelf","-SW",str(path)]).splitlines():
        m=re.match(r"^\s*\[\s*\d+\]\s+\.text\s+\S+\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+\S+\s+(.+)$",line)
        if m:
            return {"rva":int(m.group(1),16),"size":int(m.group(3),16),"alignment":int(m.group(4).split()[-1])}
    raise RuntimeError("STOP: .text section could not be parsed")
def run():
    if not LIVE.is_file() or sha(LIVE)!=LIVE_SHA:
        raise RuntimeError("STOP: baseline missing/hash mismatch")
    if not SOURCE.is_dir():raise RuntimeError("STOP: V14 source missing")
    cpp=sorted(p for p in SOURCE.rglob("*.cpp") if p.relative_to(SOURCE).as_posix() not in EXCLUDED)
    if len(cpp)!=33:raise RuntimeError("STOP: unexpected CPP count "+str(len(cpp)))
    compiler=shutil.which("g++-14")
    if compiler is None:
        print("BEGIN_DIAMOND_V8_GCC14_RESULT")
        print(json.dumps({"status":"BLOCKED_GCC14_NOT_INSTALLED","source_cpp_units":len(cpp),
                          "live_unchanged":True,"install_allowed":False,
                          "next_action":"Use matching GCC 14.2 compiler in isolated build environment; do not modify current VM toolchain"},indent=2))
        print("END_DIAMOND_V8_GCC14_RESULT")
        return
    version=invoke([compiler,"-dumpfullversion","-dumpversion"]).strip()
    if not version.startswith("14.2."):
        raise RuntimeError("STOP: GCC 14.2 required, found "+version)
    if OUT.exists():raise RuntimeError("STOP: V8 output already exists")
    OUT.mkdir(parents=False,exist_ok=False)
    target=OUT/"libDiamondV14_RECONSTRUCTED_GCC14_OFFLINE.so"
    try:
        command=[compiler,"-std=c++17","-O2","-fPIC","-shared","-Wl,--no-undefined",
             "-Wl,-soname,libDiamondV14_RECONSTRUCTED_GCC14_OFFLINE.so",
             "-Wl,-rpath,/usr/lib/cabal","-o",str(target),*[str(p) for p in cpp],
             "-ldl","-lpthread","-lodbc"]
        invoke(command,timeout=300)
        base=exported(LIVE);new=exported(target)
        lost=sorted(set(base)-set(new))
        moved=sorted(n for n in set(base)&set(new)
                     if base[n]["kind"] in ("T","W") and new[n]["kind"] in ("T","W")
                     and base[n]["rva"]!=new[n]["rva"])
        result={"status":"GCC14_OFFLINE_REBUILD_COMPLETE",
                "compiler":version,"source_cpp_units":len(cpp),
                "candidate":str(target),"candidate_sha256":sha(target),
                "original_sha256":LIVE_SHA,
                "missing_live_exports":lost,
                "moved_function_count":len(moved),
                "moved_function_examples":moved[:12],
                "original_text":section(LIVE),
                "candidate_text":section(target),
                "strict_export_parity":not lost,
                "install_allowed":False,"game_sql_untouched":True}
        print("BEGIN_DIAMOND_V8_GCC14_RESULT")
        print(json.dumps(result,indent=2,sort_keys=True))
        print("END_DIAMOND_V8_GCC14_RESULT")
    except Exception:
        target.unlink(missing_ok=True)
        raise
if __name__=="__main__":
    try:run()
    except (RuntimeError,OSError,subprocess.SubprocessError) as e:
        print("DIAMOND_V8_GCC14=STOP: "+str(e),file=sys.stderr)
        sys.exit(2)
