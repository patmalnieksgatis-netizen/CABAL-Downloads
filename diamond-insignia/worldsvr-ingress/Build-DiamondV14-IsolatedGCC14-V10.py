#!/usr/bin/env python3
"""Diamond V10: reconstruct unmodified V14 with isolated Debian 13 GCC 14.2.

Changes allowed: Docker image cache + a fresh /tmp result directory only.
Never starts/stops cabal_main/sql_main, accesses live game/SQL data,
replaces lib.so, or installs packages on the VM host.
"""
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys

SRC=pathlib.Path("/root/CABAL_V282_LIVE_MERGE_CANDIDATE_v14/source_tree/src")
LIVE=pathlib.Path("/root/cabal_diamond_backup/lib.so_before_diamond_20261122")
OUT=pathlib.Path("/tmp/cabal_diamond_v291_gcc14_isolated_v10")
LIVE_SHA="6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab"
IMAGE="cabal-diamond-gcc14-v10:local"
LIBNAME="libDiamondV14_GCC14_REBUILT_OFFLINE.so"
EXCLUDED={"hooks/Handlers/C2SHandler.cpp","hooks/Packets/EventPassInventoryPersistV282.cpp"}
DOCKERFILE="""FROM debian:trixie-slim
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends g++-14 binutils unixodbc-dev ca-certificates && rm -rf /var/lib/apt/lists/*
"""
def command(args,timeout=600,stdin=None):
    proc=subprocess.run(args,input=stdin,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                        text=True,timeout=timeout,check=False)
    if proc.returncode:
        raise RuntimeError("STOP command rc="+str(proc.returncode)+": "+repr(args[:6])+
                           " stderr="+proc.stderr[-1200:])
    return proc.stdout
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def exports(path):
    d={}
    for line in command(["nm","-D","--defined-only",str(path)],timeout=30).splitlines():
        tok=line.split()
        if len(tok)!=3 or tok[1] not in ("T","W","D","B","V","u"):continue
        try:d[tok[2]]=(tok[1],int(tok[0],16))
        except ValueError:pass
    return d
def text_info(path):
    for line in command(["readelf","-SW",str(path)],timeout=30).splitlines():
        m=re.match(r"^\s*\[\s*\d+\]\s+\.text\s+\S+\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+\S+\s+(.+)$",line)
        if m:
            return {"rva":int(m.group(1),16),"size":int(m.group(3),16),
                    "align":int(m.group(4).split()[-1])}
    raise RuntimeError("STOP: missing .text section")
def report(status,**kwargs):
    print("BEGIN_DIAMOND_V10_GCC14_RESULT")
    print(json.dumps({"status":status,"active_game_untouched":True,
                      "sql_untouched":True,"install_allowed":False,**kwargs},
                     indent=2,sort_keys=True))
    print("END_DIAMOND_V10_GCC14_RESULT")

def main():
    if shutil.which("docker") is None:raise RuntimeError("STOP: Docker missing")
    if not LIVE.is_file() or sha(LIVE)!=LIVE_SHA:
        raise RuntimeError("STOP: baseline fingerprint changed")
    if not SRC.is_dir():raise RuntimeError("STOP: original source missing")
    units=sorted(x for x in SRC.rglob("*.cpp")
                 if x.relative_to(SRC).as_posix() not in EXCLUDED)
    if len(units)!=33:raise RuntimeError("STOP: expected 33 C++ units; got "+str(len(units)))
    if OUT.exists():raise RuntimeError("STOP: output already exists "+str(OUT))
    # IMPORTANT: Docker builds only a tagged compiler image; no live container changes.
    try:
        command(["docker","image","inspect",IMAGE],timeout=25)
    except RuntimeError:
        command(["docker","build","--pull=false","--tag",IMAGE,"-"],timeout=1200,stdin=DOCKERFILE)
    version=command(["docker","run","--rm","--network","none","--entrypoint","g++-14",IMAGE,
                     "-dumpfullversion","-dumpversion"],timeout=90).strip()
    if not version.startswith("14.2."):
        raise RuntimeError("STOP: wrong GCC version in isolated image: "+version)
    OUT.mkdir(parents=False,exist_ok=False)
    source_before={str(p.relative_to(SRC)):sha(p) for p in SRC.rglob("*") if p.is_file()}
    target=OUT/LIBNAME
    guest_units=["/source/"+str(p.relative_to(SRC)) for p in units]
    compile_command=["g++-14","-std=c++17","-O2","-fPIC","-shared",
       "-Wl,--no-undefined","-Wl,-soname,"+LIBNAME,"-Wl,-rpath,/usr/lib/cabal",
       "-o","/result/"+LIBNAME,*guest_units,"-ldl","-lpthread","-lodbc"]
    try:
        command(["docker","run","--rm","--network","none",
             "--read-only","--tmpfs","/tmp:rw,nosuid,size=512m",
             "--mount","type=bind,src="+str(SRC)+",dst=/source,readonly",
             "--mount","type=bind,src="+str(OUT)+",dst=/result",
             "--workdir","/source",IMAGE,*compile_command],timeout=1200)
        if not target.is_file():raise RuntimeError("STOP: offline output absent")
        source_after={str(p.relative_to(SRC)):sha(p) for p in SRC.rglob("*") if p.is_file()}
        if source_before!=source_after or sha(LIVE)!=LIVE_SHA:
            raise RuntimeError("STOP: source or baseline changed during compilation")
        original=exports(LIVE)
        rebuilt=exports(target)
        missing=sorted(set(original)-set(rebuilt))
        moved=sorted(name for name in set(original)&set(rebuilt)
            if original[name][0] in ("T","W") and rebuilt[name][0] in ("T","W")
            and original[name][1]!=rebuilt[name][1])
        needs=command(["readelf","--dyn-syms","-W",str(target)],timeout=30)
        report("GCC14_OFFLINE_COMPARISON_COMPLETE",compiler_version=version,
               original_sha256=LIVE_SHA,candidate_sha256=sha(target),
               source_cpp_units=len(units),missing_live_exports=missing,
               changed_function_rvas=len(moved),moved_function_examples=moved[:15],
               original_text=text_info(LIVE),rebuilt_text=text_info(target),
               original_export_count=len(original),rebuilt_export_count=len(rebuilt),
               has_isoc23_strtoull="__isoc23_strtoull@GLIBC_2.38" in needs,
               candidate_path=str(target),strict_export_parity=(len(missing)==0))
    except Exception:
        target.unlink(missing_ok=True)
        raise
if __name__=="__main__":
    try:main()
    except (RuntimeError,OSError,subprocess.SubprocessError) as err:
        print("DIAMOND_V10_GCC14=STOP: "+str(err),file=sys.stderr)
        sys.exit(2)
