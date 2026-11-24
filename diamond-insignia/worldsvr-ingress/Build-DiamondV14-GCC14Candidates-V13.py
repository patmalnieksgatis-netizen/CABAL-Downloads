#!/usr/bin/env python3
"""V13: build previously staged Diamond sources with the verified GCC14 image.
Offline outputs only. No live game/SQL changes or container restart.
"""
import hashlib,json,pathlib,subprocess,sys

SRC=pathlib.Path("/root/CABAL_V282_LIVE_MERGE_CANDIDATE_v14/source_tree/src")
STAGE=pathlib.Path("/tmp/cabal_diamond_v291_0bda_offline_build_20261123_v4")
BASE=pathlib.Path("/root/cabal_diamond_backup/lib.so_before_diamond_20261122")
REBUILT=pathlib.Path("/tmp/cabal_diamond_v291_gcc14_isolated_v10/libDiamondV14_GCC14_REBUILT_OFFLINE.so")
OUT=pathlib.Path("/tmp/cabal_diamond_v291_gcc14_v13")
IMAGE="sha256:2805f2cd7dacf0547b8762437009a4814ab0c352f913b15c87b3e856f04528bb"
EXCLUDED={"hooks/Handlers/C2SHandler.cpp","hooks/Packets/EventPassInventoryPersistV282.cpp"}
def run(argv,timeout=40):
    p=subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError("STOP rc="+str(p.returncode)+" "+repr(argv[:6])+" "+p.stderr[-2000:])
    return p.stdout
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def manifest(p):
    return {str(x.relative_to(p)):sha(x) for x in sorted(p.rglob("*")) if x.is_file()}
def syms(p):
    defined={};undefined=set()
    for line in run(["readelf","--dyn-syms","-W",str(p)]).splitlines():
        w=line.split()
        if len(w)<8 or not w[0].rstrip(":").isdigit():continue
        if w[6]=="UND":undefined.add(w[7])
        elif w[4] in ("GLOBAL","WEAK","UNIQUE"):defined[w[7]]=(w[3],w[4],w[5],int(w[1],16),int(w[2]))
    return defined,undefined
def diff(reference,candidate):
    a,ai=syms(reference);b,bi=syms(candidate)
    return {"missing_exports":sorted(set(a)-set(b)),
      "new_exports":sorted(set(b)-set(a)),
      "new_imports":sorted(bi-ai),"removed_imports":sorted(ai-bi),
      "changed_export_type_binding_visibility":sorted(k for k in set(a)&set(b) if a[k][:3]!=b[k][:3]),
      "changed_function_rvas":sum(a[k][0]=="FUNC" and a[k][3]!=b[k][3] for k in set(a)&set(b))}
def main():
    if sha(BASE)!="6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab":raise RuntimeError("baseline hash mismatch")
    if sha(REBUILT)!="519394563dc196b57cb221b4c4029c4e62a242d9b787f4585a372d222cb1f524":raise RuntimeError("GCC14 reconstruction hash mismatch")
    if OUT.exists():raise RuntimeError("output exists")
    v=run(["docker","run","--rm","--network","none","--entrypoint","g++-14",IMAGE,"-dumpfullversion","-dumpversion"]).strip()
    if v!="14.2.0":raise RuntimeError("wrong compiler")
    inputs={"observer":STAGE/"observer-source","full_hook":STAGE/"source"}
    before={k:manifest(p) for k,p in inputs.items()}
    original=manifest(SRC)
    if not original or not all(before.values()):raise RuntimeError("source missing")
    OUT.mkdir()
    result={"compiler":v,"install_allowed":False,"rankup_verified":False,"candidates":{}}
    for key,p in inputs.items():
        cpp=sorted(x for x in p.rglob("*.cpp") if x.relative_to(p).as_posix() not in EXCLUDED)
        if len(cpp)!={"observer":33,"full_hook":34}[key]:raise RuntimeError("unexpected translation unit count "+key)
        name="libDiamondV14_GCC14_"+key.upper()+"_OFFLINE.so"
        target=OUT/name
        cmd=["g++-14","-std=c++17","-O2","-fPIC","-shared","-Wl,--no-undefined","-Wl,-soname,"+name,
             "-Wl,-rpath,/usr/lib/cabal","-o","/result/"+name,
             *["/source/"+str(x.relative_to(p)) for x in cpp],"-ldl","-lpthread","-lodbc"]
        print("DIAMOND_V13_BUILD="+key,flush=True)
        run(["docker","run","--rm","--network","none","--read-only",
             "--tmpfs","/tmp:rw,nosuid,size=512m",
             "--mount","type=bind,src="+str(p)+",dst=/source,readonly",
             "--mount","type=bind,src="+str(OUT)+",dst=/result",
             "--workdir","/source",IMAGE,*cmd],timeout=900)
        result["candidates"][key]={"path":str(target),"sha256":sha(target),
            "vs_original_live":diff(BASE,target),"vs_gcc14_reconstruction":diff(REBUILT,target)}
    if original!=manifest(SRC) or any(before[k]!=manifest(p) for k,p in inputs.items()):
        raise RuntimeError("source changed")
    result["status"]="GCC14_DIAMOND_CANDIDATES_BUILT_OFFLINE"
    result["source_unchanged"]=True
    (OUT/"REPORT.json").write_text(json.dumps(result,indent=2)+"\n")
    print("BEGIN_DIAMOND_V13_RESULT")
    print(json.dumps(result,indent=2,sort_keys=True))
    print("END_DIAMOND_V13_RESULT")
if __name__=="__main__":
    try:main()
    except Exception as e:
        print("DIAMOND_V13=STOP "+str(e),file=sys.stderr)
        sys.exit(2)
