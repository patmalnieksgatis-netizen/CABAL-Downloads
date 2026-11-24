#!/usr/bin/env python3
"""Prepare V23 observer candidate in existing cabal_main runtime.
Does not replace any active files, load the extension into WorldSvr, execute
SQL, change supervisor configuration, or restart any process.
"""
import hashlib,json,pathlib,subprocess,tempfile,re,os
C="cabal_main"
P="WorldSvr_01_01"
CAND=pathlib.Path("/tmp/cabal-diamond-v23-5019unvv/build/libDiamondV23_NativeStartup_OFFLINE.so")
CAND_SHA="8ecc2cd687b650719b69d952f17ca658fc627ffea8b560b48f255c05f319bcec"
WORLD_SHA="caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3"
BASE_SHA="6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab"
def run(args,check=True,timeout=45):
    p=subprocess.run(args,capture_output=True,timeout=timeout)
    if check and p.returncode:raise RuntimeError(str(args[:4])+" rc="+str(p.returncode)+" "+p.stderr.decode(errors="replace")[-2000:])
    return p
def d(*args,check=True,timeout=45):return run(["docker","exec",C,*args],check,timeout)
def t(*args):return d(*args).stdout.decode().strip()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def exports(path):
    result=set()
    for line in run(["readelf","--dyn-syms","-W",str(path)]).stdout.decode().splitlines():
        w=line.split()
        if len(w)>=8 and w[0].rstrip(":").isdigit() and w[6]!="UND" and w[4] in ("GLOBAL","WEAK","UNIQUE") and w[5] in ("DEFAULT","PROTECTED"):
            result.add(w[7])
    return result
def main():
    if sha(CAND)!=CAND_SHA:raise RuntimeError("candidate hash mismatch")
    pid=t("supervisorctl","pid",P)
    if not pid.isdigit() or int(pid)<=1:raise RuntimeError("WorldSvr not running")
    if t("sha256sum","/proc/"+pid+"/exe").split()[0]!=WORLD_SHA:raise RuntimeError("WorldSvr hash mismatch")
    maps=t("cat","/proc/"+pid+"/maps").splitlines()
    entries=[]
    for line in maps:
        fields=line.split(None,5)
        if len(fields)==6 and re.search(r"/lib\.so(?: \(deleted\))?$",fields[5]):
            entries.append(fields)
    if not entries:raise RuntimeError("active lib.so not found in WorldSvr maps")
    paths={x[5] for x in entries}
    if len(paths)!=1:raise RuntimeError("ambiguous loaded lib.so path")
    live=paths.pop()
    if live.endswith(" (deleted)"):raise RuntimeError("loaded lib.so was replaced/deleted")
    if not live.startswith("/") or "\n" in live:raise RuntimeError("invalid live path")
    inode=t("stat","-Lc","%i",live)
    if any(x[4]!=inode for x in entries):raise RuntimeError("loaded/on-disk inode mismatch")
    before=t("sha256sum",live).split()[0]
    if before!=BASE_SHA:raise RuntimeError("live library differs from audited V14 baseline: "+before)
    # Binary-exact host backup outside the game container.
    os.umask(0o077)
    root=pathlib.Path(tempfile.mkdtemp(prefix="cabal-diamond-v23-deploy-",dir="/root"))
    backup=root/"lib.so.original"
    backup.write_bytes(d("cat",live).stdout)
    if sha(backup)!=before:raise RuntimeError("backup checksum mismatch")
    missing=sorted(exports(backup)-exports(CAND))
    if missing:raise RuntimeError("candidate missing existing exported symbols: "+str(missing[:30]))
    print("V23_ORIGINAL_BACKUP=PASS "+str(backup),flush=True)
    # Candidate resides in a new container staging directory, not the live
    # loader path. ldd performs loader dependency/relocation checks only;
    # never dlopen this extension because its original V14 constructors
    # are designed for the game executable.
    stage=t("mktemp","-d","/tmp/cabal-diamond-v23-stage-XXXXXXXX")
    if not re.fullmatch(r"/tmp/cabal-diamond-v23-stage-[A-Za-z0-9]+",stage):
        raise RuntimeError("unexpected stage path")
    dest=stage+"/libDiamondV23_NativeStartup_OFFLINE.so"
    run(["docker","cp",str(CAND),C+":"+dest])
    if t("sha256sum",dest).split()[0]!=CAND_SHA:raise RuntimeError("staged hash mismatch")
    # Only extract LD_LIBRARY_PATH from the actual WorldSvr environment;
    # no credentials or complete environment are printed or stored.
    env=d("cat","/proc/"+pid+"/environ").stdout
    libpath=[e.decode() for e in env.split(b"\0") if e.startswith(b"LD_LIBRARY_PATH=")]
    cmd=["env",*libpath,"ldd","-r",dest]
    p=d(*cmd,check=False,timeout=60)
    output=(p.stdout+p.stderr).decode(errors="replace")
    (root/"loader-check.txt").write_text(output)
    if p.returncode or re.search(r"not found|undefined symbol|version .* not found|not a dynamic executable|cannot open shared object",output,re.I):
        raise RuntimeError("runtime loader check failed:\n"+output[-4000:])
    if t("supervisorctl","pid",P)!=pid or t("sha256sum",live).split()[0]!=before:
        raise RuntimeError("active server changed during preparation")
    report={"pid":int(pid),"live_library":live,"live_sha256":before,
            "backup":str(backup),"backup_sha256":sha(backup),
            "container_candidate":dest,"candidate_sha256":CAND_SHA,
            "original_exports_preserved":True,"runtime_loader_check_pass":True,
            "active_library_replaced":False,"world_restarted":False,
            "sql_modified":False,"observer_activated":False,
            "rankup_ready":False,"install_allowed":False}
    (root/"REPORT.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    print("DIAMOND_V23_DEPLOY_PREPARE=PASS_OBSERVER_STAGED_ONLY")
if __name__=="__main__":
    try:main()
    except Exception as e:
        print("DIAMOND_V23_DEPLOY_PREPARE=STOP "+str(e))
        raise SystemExit(2)
