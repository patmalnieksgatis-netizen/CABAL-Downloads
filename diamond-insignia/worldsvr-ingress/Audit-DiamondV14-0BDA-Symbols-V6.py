#!/usr/bin/env python3
"""Diamond 0BDA V6: read-only, hash-locked ELF symbol and alignment differences."""
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys

BACKUP=pathlib.Path("/root/cabal_diamond_backup/lib.so_before_diamond_20261122")
OUT=pathlib.Path("/tmp/cabal_diamond_v291_0bda_offline_build_20261123_v4")
FILES={
    "live_backup":(BACKUP,"6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab"),
    "reconstructed":(OUT/"libDiamondV14_ORIGINAL_RECONSTRUCTED_OFFLINE.so","702832acabab93835d2b0489f2957e7ebaeb3d4a5b18d7eb82e501fe1e3a1782"),
    "minimal":(OUT/"libDiamondV14_MINIMAL_0BDA_OFFLINE.so","7745cad9246488df7a48b7611a1057dc19ae4713c35fc253c81aa20e5d929cba"),
    "observer":(OUT/"libDiamondV14_OBSERVE_0BDA_OFFLINE.so","950d9f075b34dcae33b9e969048b312fd95265e6c084834a8eb1256a7ab7ace8"),
    "full_hook":(OUT/"libDiamondV14_0BDA_UNINSTALLED.so","d8f366cd36d118b032712bc31cd02c92562629444b4d66fd0f0762eb2bf50074"),
}
def cmd(args):
    p=subprocess.run(args,text=True,capture_output=True,timeout=25)
    if p.returncode:
        raise RuntimeError("STOP: "+str(args)+" rc="+str(p.returncode)+" "+p.stderr[-200:])
    return p.stdout

def symbols(path):
    # Dynamic symbol names including GLIBC version and symbol binding/type.
    out=cmd(["readelf","--dyn-syms","-W",str(path)])
    imported={}
    exported={}
    for line in out.splitlines():
        parts=line.split()
        if len(parts)<8 or not parts[0].endswith(":") or not parts[0][:-1].isdigit():
            continue
        # Num Value Size Type Bind Vis Ndx Name
        _,value,size,typ,bind,vis,ndx,name=parts[:8]
        if name=="(null)": continue
        meta={"type":typ,"binding":bind,"visibility":vis}
        if ndx=="UND":
            imported[name]=meta
        elif bind in ("GLOBAL","WEAK","UNIQUE"):
            exported[name]=meta
    return imported,exported

def section_metrics(path):
    out=cmd(["readelf","-SW",str(path)])
    answer={}
    for line in out.splitlines():
        m=re.match(r"^\s*\[\s*\d+\]\s+(\.\S+)\s+\S+\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+([0-9a-fA-F]+)\s+\S+\s+\S+\s+\S+\s+(\d+)\s*$",line)
        if m and m.group(1) in (".text",".plt",".init",".fini",".rodata",".eh_frame",".dynsym"):
            answer[m.group(1)]={"size_bytes":int(m.group(2),16),"alignment":int(m.group(3))}
    return answer

def main():
    for executable in ("readelf","nm","objdump"):
        if not shutil.which(executable):
            raise RuntimeError("STOP: missing "+executable)
    data={}
    for key,(path,expected) in FILES.items():
        if not path.is_file(): raise RuntimeError("STOP: file missing: "+str(path))
        if key!="live_backup" and OUT not in path.parents:
            raise RuntimeError("STOP: candidate outside isolated output")
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        if sha!=expected: raise RuntimeError("STOP: changed binary "+key)
        imported,exported=symbols(path)
        data[key]={"imported":imported,"exported":exported,
                   "sections":section_metrics(path)}
    live=data["live_backup"]
    result={
        "status":"V6_READ_ONLY_SYMBOL_AUDIT_COMPLETE",
        "no_game_or_sql_changes":True,
        "deploy_approved":False,
        "glibc_2_38_imports_in_live":sorted(n for n in live["imported"] if "@GLIBC_2.38" in n),
        "glibc_2_38_imports_per_candidate":{
            k:sorted(n for n in d["imported"] if "@GLIBC_2.38" in n)
            for k,d in data.items() if k!="live_backup"
        },
        "text_sections":{k:v["sections"].get(".text") for k,v in data.items()},
        "other_sections":{k:{s:v for s,v in d["sections"].items() if s!=".text"}
                           for k,d in data.items()},
        "import_differences_vs_live":{},
        "export_differences_vs_live":{},
    }
    for key,d in data.items():
        if key=="live_backup": continue
        result["import_differences_vs_live"][key]={
            "only_live":sorted(set(live["imported"])-set(d["imported"])),
            "only_candidate":sorted(set(d["imported"])-set(live["imported"])),
        }
        result["export_differences_vs_live"][key]={
            "only_live":sorted(set(live["exported"])-set(d["exported"])),
            "only_candidate":sorted(set(d["exported"])-set(live["exported"])),
        }
    print("BEGIN_DIAMOND_V6_SYMBOL_AUDIT")
    print(json.dumps(result,indent=2,sort_keys=True))
    print("END_DIAMOND_V6_SYMBOL_AUDIT")
if __name__=="__main__":
    try:main()
    except (RuntimeError,OSError,subprocess.SubprocessError) as exc:
        print("DIAMOND_V6_SYMBOL_AUDIT=STOP: "+str(exc),file=sys.stderr)
        sys.exit(2)
