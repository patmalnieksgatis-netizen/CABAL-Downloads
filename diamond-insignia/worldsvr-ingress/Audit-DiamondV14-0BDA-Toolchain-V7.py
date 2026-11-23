#!/usr/bin/env python3
"""CABAL Diamond v291 0BDA V7: hash-locked, read-only ELF/toolchain audit.

Inspects offline V4 artifacts and a saved baseline. Never dlopen/execute
the libraries, write files, build, install, or touch SQL/game services.
"""
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys

OUT=pathlib.Path("/tmp/cabal_diamond_v291_0bda_offline_build_20261123_v4")
ARTIFACTS={
  "live_backup":("/root/cabal_diamond_backup/lib.so_before_diamond_20261122",
    "6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab"),
  "reconstructed":(str(OUT/"libDiamondV14_ORIGINAL_RECONSTRUCTED_OFFLINE.so"),
    "702832acabab93835d2b0489f2957e7ebaeb3d4a5b18d7eb82e501fe1e3a1782"),
  "minimal":(str(OUT/"libDiamondV14_MINIMAL_0BDA_OFFLINE.so"),
    "7745cad9246488df7a48b7611a1057dc19ae4713c35fc253c81aa20e5d929cba"),
  "observer":(str(OUT/"libDiamondV14_OBSERVE_0BDA_OFFLINE.so"),
    "950d9f075b34dcae33b9e969048b312fd95265e6c084834a8eb1256a7ab7ace8"),
  "full_hook":(str(OUT/"libDiamondV14_0BDA_UNINSTALLED.so"),
    "d8f366cd36d118b032712bc31cd02c92562629444b4d66fd0f0762eb2bf50074")
}
WATCH=("__isoc23_strtoull","strtoull","_M_realloc_append","_M_realloc_insert")
def command(argv, allow_fail=False):
    proc=subprocess.run(argv,capture_output=True,text=True,timeout=30,check=False)
    if proc.returncode and not allow_fail:
        raise RuntimeError("STOP: command failed "+repr(argv)+": "+proc.stderr[-240:])
    return proc.stdout if proc.returncode==0 else ""

def sections(path):
    # readelf -SW output, including "[12]" and "[ 2]" forms; use whitespace
    # token parsing so .text remains visible even when readelf column spacing varies.
    out={}
    for line in command(["readelf","-SW",str(path)]).splitlines():
        m=re.match(r"^\s*\[\s*(\d+)\]\s+(\.\S+)\s+(\S+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+(\S+)\s+(.+)$",line)
        if not m: continue
        name=m.group(2)
        if name not in (".text",".plt",".init",".fini",".rodata",".eh_frame",".dynsym",".comment"): continue
        rest=m.group(8).split()
        if len(rest)<3: continue
        try:align=int(rest[-1])
        except ValueError:continue
        out[name]={"address_hex":m.group(4),"offset_hex":m.group(5),
                   "size":int(m.group(6),16),"alignment":align}
    return out

def relevant_symbols(path):
    rows=[]
    for line in command(["readelf","--dyn-syms","-W",str(path)]).splitlines():
        if any(word in line for word in WATCH):
            rows.append(line.strip()[:400])
    return rows

def relocations(path):
    rows=[]
    for line in command(["readelf","-rW",str(path)]).splitlines():
        if "strtoull" in line:
            rows.append(line.strip()[:400])
    return rows[:30]

def callsites(path):
    # Static disassembly; no binary is executed.
    lines=command(["objdump","-d","-C",str(path)]).splitlines()
    matches=[]
    for idx,line in enumerate(lines):
        if "strtoull@plt" in line and ("call" in line or "jmp" in line):
            matches.append({"line":idx+1,
              "context":[s.strip()[:240] for s in lines[max(0,idx-3):idx+3]]})
    return matches[:16]

def main():
    for tool in ("readelf","objdump"):
        if shutil.which(tool) is None:raise RuntimeError("STOP: missing "+tool)
    result={"status":"V7_READ_ONLY_TARGETED_AUDIT_COMPLETE",
            "baseline_unmodified":True,"game_sql_unmodified":True,
            "installation_allowed":False,"artifacts":{}}
    for key,(name,expected_sha) in ARTIFACTS.items():
        path=pathlib.Path(name)
        if not path.is_file():raise RuntimeError("STOP: missing "+name)
        if key!="live_backup" and OUT not in path.parents:
            raise RuntimeError("STOP: unexpected artifact location "+name)
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        if sha!=expected_sha:raise RuntimeError("STOP: hash mismatch "+key)
        result["artifacts"][key]={
            "sha256":sha,"sections":sections(path),
            "strtoull_relocations":relocations(path),
            "strtoull_callsites":callsites(path),
            "selected_dynamic_symbols":relevant_symbols(path),
            "compiler_comment":command(["readelf","-p",".comment",str(path)],True)[-1500:]
        }
    print("BEGIN_DIAMOND_V7_TOOLCHAIN_AUDIT")
    print(json.dumps(result,indent=2,sort_keys=True))
    print("END_DIAMOND_V7_TOOLCHAIN_AUDIT")
if __name__=="__main__":
    try:main()
    except (RuntimeError,OSError,subprocess.SubprocessError) as e:
        print("DIAMOND_V7_TOOLCHAIN_AUDIT=STOP: "+str(e),file=sys.stderr)
        sys.exit(2)
