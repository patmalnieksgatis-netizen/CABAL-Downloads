#!/usr/bin/env python3
"""Read-only ELF/toolchain audit for CABAL v291 Diamond 0BDA offline candidates.

Does not import/load .so files, touch game files, or invoke game processes.
Run on the TEST VM with: python3 Audit-DiamondV14-0BDA-ELF-V5.py
"""
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys

BASE=pathlib.Path("/root/cabal_diamond_backup/lib.so_before_diamond_20261122")
OUT=pathlib.Path("/tmp/cabal_diamond_v291_0bda_offline_build_20261123_v4")
FILES={
    "live_backup": BASE,
    "reconstructed": OUT/"libDiamondV14_ORIGINAL_RECONSTRUCTED_OFFLINE.so",
    "minimal": OUT/"libDiamondV14_MINIMAL_0BDA_OFFLINE.so",
    "observer": OUT/"libDiamondV14_OBSERVE_0BDA_OFFLINE.so",
    "full_hook": OUT/"libDiamondV14_0BDA_UNINSTALLED.so",
}
BASE_SHA="6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab"
EXPECT={
    "reconstructed":"702832acabab93835d2b0489f2957e7ebaeb3d4a5b18d7eb82e501fe1e3a1782",
    "minimal":"7745cad9246488df7a48b7611a1057dc19ae4713c35fc253c81aa20e5d929cba",
    "observer":"950d9f075b34dcae33b9e969048b312fd95265e6c084834a8eb1256a7ab7ace8",
    "full_hook":"d8f366cd36d118b032712bc31cd02c92562629444b4d66fd0f0762eb2bf50074",
}
def run(cmd):
    x=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,check=False)
    if x.returncode: raise RuntimeError("STOP: "+repr(cmd)+" exited "+str(x.returncode)+": "+x.stderr[-250:])
    return x.stdout

def rows_with(lines, regex):
    return sorted(set(re.findall(regex,lines,re.MULTILINE)))

def details(path):
    dyn=run(["readelf","-dW",str(path)])
    hdr=run(["readelf","-hW",str(path)])
    vers=run(["readelf","--version-info","-W",str(path)])
    sections=run(["readelf","-SW",str(path)])
    symbols=run(["nm","-D","--defined-only",str(path)])
    return {
        "elf_class":(re.search(r"Class:\\s*(\\S+)",hdr) or [None,None])[1],
        "machine":(re.search(r"Machine:\\s*(.+)",hdr) or [None,None])[1],
        "needed":rows_with(dyn,r"\\(NEEDED\\).*?\\[(.*?)\\]"),
        "rpath":rows_with(dyn,r"\\((?:RUNPATH|RPATH)\\).*?\\[(.*?)\\]"),
        "soname":rows_with(dyn,r"\\(SONAME\\).*?\\[(.*?)\\]"),
        "version_requirements":rows_with(vers,r"Name:\\s*(\\S+)\\s+Flags:"),
        "version_names":rows_with(vers,r"Name:\\s*(\\S+)"),
        "build_id":rows_with(run(["readelf","-nW",str(path)]),r"Build ID:\\s*([a-f0-9]+)"),
        "text_section": next((line.strip() for line in sections.splitlines() if re.search(r"\\s\\.text\\s",line)),None),
        "dynamic_export_count":sum(1 for x in symbols.splitlines() if x.strip()),
    }

def main():
    for cmd in ("readelf","nm","g++","ld","objdump"):
        if not shutil.which(cmd): raise RuntimeError("STOP: missing "+cmd)
    if not OUT.is_dir(): raise RuntimeError("STOP: V4 offline output not found")
    found={}
    for key,path in FILES.items():
        if not path.is_file() or not path.is_relative_to(OUT) and key!="live_backup":
            raise RuntimeError("STOP: missing or unexpected file "+str(path))
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        if sha!=(BASE_SHA if key=="live_backup" else EXPECT[key]):
            raise RuntimeError("STOP: SHA drift for "+key+": "+sha)
        found[key]={"sha256":sha,"size":path.stat().st_size,**details(path)}
    reference=found["live_backup"]
    differences={}
    for key,data in found.items():
        if key=="live_backup": continue
        differences[key]={field:{"baseline":reference[field],"candidate":data[field]}
                          for field in ("elf_class","machine","needed","rpath","version_requirements","version_names")
                          if reference[field]!=data[field]}
    compiler=run(["g++","--version"]).splitlines()[0]
    linker=run(["ld","--version"]).splitlines()[0]
    result={"status":"READ_ONLY_ELF_AUDIT_COMPLETE","live_unchanged":True,
            "compiler":compiler,"linker":linker,"candidates":found,
            "differences_vs_live":differences,
            "strict_compatibility_proven":False,
            "recommend_installation":False}
    print("BEGIN_DIAMOND_V5_ELF_AUDIT")
    print(json.dumps(result,indent=2,sort_keys=True))
    print("END_DIAMOND_V5_ELF_AUDIT")
if __name__=="__main__":
    try: main()
    except Exception as exc:
        print("DIAMOND_V5_ELF_AUDIT=STOP: "+str(exc),file=sys.stderr)
        sys.exit(2)
