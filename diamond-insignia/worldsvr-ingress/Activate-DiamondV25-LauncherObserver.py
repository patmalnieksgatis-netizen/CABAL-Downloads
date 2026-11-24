#!/usr/bin/env python3
"""V24: approved CH1-only observer trial through the actual Python launcher.
No shared lib.so replacement, supervisor config change, SQL write or VM restart.
"""
import hashlib,json,pathlib,re,subprocess,sys,time,os
C="cabal_main"; P="WorldSvr_01_01"
LAUNCH="/usr/bin/WorldSvr_01_01"
LIVE="/usr/lib/cabal/lib.so"
STAGE="/tmp/cabal-diamond-v23-stage-U9ZoMeDT/libDiamondV23_NativeStartup_OFFLINE.so"
DEST="/usr/lib/cabal/libDiamondV23_Observer_8ecc2cd6.so"
ROOT=pathlib.Path("/root/cabal-diamond-v23-deploy-a1fpo5tp")
BASE="6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab"
CAND="8ecc2cd687b650719b69d952f17ca658fc627ffea8b560b48f255c05f319bcec"
WORLD="caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3"
EXPECTED=[
"/etc/cabal/migration_tools/ep36-costume-trial-v1/mileage-v1/EP36CostumeMileage.so",
LIVE,"/usr/lib/cabal/libchilkat-9.5.0.so","/usr/lib/cabal/libPolyHook_2.so",
"/usr/lib/cabal/libZycore.so.1.4","/usr/lib/cabal/libZydis.so.4.0",
"/usr/lib/cabal/guardian-v1/GuardianArcana-v1.so",
"/usr/lib/cabal/skillbook291/SkillBook291.so",
"/usr/lib/cabal/cashshop291/CashShop291.so"]
TRIAL=[DEST if p==LIVE else p for p in EXPECTED]
MARK="    os.execve(NATIVE,['/usr/bin/WorldSvr_01_01',*sys.argv[1:]],environment)"
PATCH="""    # Diamond V23: observer only, preserve final preload order and all existing add-ons.
    diamond_tokens=environment.get('LD_PRELOAD','').split()
    if diamond_tokens.count('/usr/lib/cabal/lib.so')!=1:
        raise ValueError('DIAMOND_V23_ORIGINAL_PRELOAD_MISMATCH')
    if digest(Path('/usr/lib/cabal/libDiamondV23_Observer_8ecc2cd6.so'))!='8ecc2cd687b650719b69d952f17ca658fc627ffea8b560b48f255c05f319bcec':
        raise ValueError('DIAMOND_V23_CANDIDATE_HASH_MISMATCH')
    environment['LD_PRELOAD']=' '.join('/usr/lib/cabal/libDiamondV23_Observer_8ecc2cd6.so' if x=='/usr/lib/cabal/lib.so' else x for x in diamond_tokens)
    environment['CABAL_DIAMOND_V23_NATIVE_OBSERVER']='1'
"""
def d(*a,check=True,data=None,timeout=120):
    p=subprocess.run(["docker","exec",*(["-i"] if data is not None else []),C,*a],input=data,capture_output=True,timeout=timeout)
    if check and p.returncode:raise RuntimeError("command failed: "+repr(a[:3])+" rc="+str(p.returncode)+" "+p.stderr.decode(errors="replace")[-700:])
    return p
def t(*a,**kw):return d(*a,**kw).stdout.decode(errors="replace").strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def csha(p):return t("sha256sum",p).split()[0]
def pid():
    # supervisorctl pid returns nonzero for an intentionally stopped process.
    # Resolve from status instead; reject unknown state or missing program.
    p=d("supervisorctl","status",P,check=False)
    line=p.stdout.decode(errors="replace").strip()
    m=re.fullmatch(r"WorldSvr_01_01\s+(RUNNING|STARTING|STOPPING|STOPPED|EXITED|FATAL|BACKOFF)(?:\s+.*)?",line)
    if not m:raise RuntimeError("unrecognized target status: "+line[:200])
    state=m.group(1)
    pm=re.search(r"\bpid (\d+),",line)
    if state=="RUNNING":
        if not pm:raise RuntimeError("RUNNING without PID")
        return int(pm.group(1))
    if state in ("STARTING","STOPPING"):
        q=d("supervisorctl","pid",P,check=False)
        value=q.stdout.decode(errors="replace").strip()
        if q.returncode==0 and value.isdigit() and int(value)>1:return int(value)
        raise RuntimeError("target transitional state: "+state)
    return 0
def states():
    out={}
    for l in t("supervisorctl","status",check=False).splitlines():
        w=l.split()
        if len(w)<2:continue
        m=re.search(r"\bpid (\d+),",l)
        out[w[0]]=(w[1],int(m.group(1)) if m else 0)
    return out
def running():return states().get(P,("",0))[0]=="RUNNING"
def verify(expected,observer):
    n=pid()
    if n<=1 or not running():raise RuntimeError("target not RUNNING")
    if csha("/proc/"+str(n)+"/exe")!=WORLD:raise RuntimeError("WorldSvr hash mismatch")
    env=d("cat","/proc/"+str(n)+"/environ").stdout.split(b"\0")
    values=[e[len(b"LD_PRELOAD="):].decode().split() for e in env if e.startswith(b"LD_PRELOAD=")]
    if values!=[expected]:raise RuntimeError("unexpected actual preload list")
    if observer and b"CABAL_DIAMOND_V23_NATIVE_OBSERVER=1" not in env:
        raise RuntimeError("observer env not present")
    paths={w[5] for l in t("cat","/proc/"+str(n)+"/maps").splitlines() if len(w:=l.split(None,5))==6}
    if not all(x in paths for x in expected):raise RuntimeError("expected preload missing in maps")
    if observer and LIVE in paths:raise RuntimeError("both old and new lib.so mapped")
    if not observer and DEST in paths:raise RuntimeError("observer module remained mapped")
    if csha(LIVE)!=BASE:raise RuntimeError("original shared library changed")
    return n
def stop():
    if pid()>1 or running():d("supervisorctl","stop",P,timeout=180)
    if pid()>1:raise RuntimeError("WorldSvr stop incomplete")
def start():
    d("supervisorctl","start",P,timeout=180)
    if not running():raise RuntimeError("WorldSvr startup failed")
def write_launcher(data):
    # Preserve launcher ownership and permissions; atomic rename.
    d("sh","-c",'set -eu; t=$(mktemp "$1.diamond.XXXXXXXX"); cp -p "$1" "$t"; cat > "$t"; mv -f "$t" "$1"',"sh",LAUNCH,data=data)
    if d("cat",LAUNCH).stdout!=data:raise RuntimeError("launcher write mismatch")
def rollback(original,trial):
    print("V25_ROLLBACK_BEGIN",flush=True)
    current=d("cat",LAUNCH).stdout
    if current not in (original,trial):raise RuntimeError("launcher changed externally; not overwriting")
    stop()
    if current!=original:write_launcher(original)
    start()
    print("V25_ROLLBACK=PASS pid="+str(verify(EXPECTED,False)),flush=True)
def main():
    os.umask(0o077)
    backup=ROOT/"WorldSvr_01_01.launcher.original"
    patched=ROOT/"WorldSvr_01_01.launcher.v24"
    if "--rollback" in sys.argv:
        rollback(backup.read_bytes(),patched.read_bytes());return
    if "--apply-observer" not in sys.argv:raise RuntimeError("explicit --apply-observer required")
    # Permit retry after V24 stopped before writing its launcher. Existing
    # original and trial backups must match byte-for-byte; never overwrite.
    retry=backup.exists() or patched.exists()
    if retry and not (backup.is_file() and patched.is_file()):raise RuntimeError("incomplete prior backups")
    if sha(ROOT/"lib.so.original")!=BASE or csha(LIVE)!=BASE or csha(STAGE)!=CAND:raise RuntimeError("preflight hashes mismatch")
    n=verify(EXPECTED,False)
    before=states()
    # Check original launcher and the exact single insertion point.
    if d("test","-L",LAUNCH,check=False).returncode==0:raise RuntimeError("launcher symlink")
    if t("stat","-c","%u",LAUNCH)!="0":raise RuntimeError("launcher not root owned")
    original=d("cat",LAUNCH).stdout
    source=original.decode()
    if not source.startswith("#!/usr/bin/python3") or source.count(MARK)!=1 or "DIAMOND_V23" in source or WORLD not in source:
        raise RuntimeError("launcher no longer matches observed source")
    for x in ("trial_preloads(previous)","EP36_COSTUME_TRIAL","GuardianArcana-v1.so","SkillBook291.so","CashShop291.so"):
        if x not in source:raise RuntimeError("existing launcher feature missing: "+x)
    updated=source.replace(MARK,PATCH+MARK).encode()
    compile(updated,LAUNCH,"exec")
    if d("test","-e",DEST,check=False).returncode==0:
        if csha(DEST)!=CAND:raise RuntimeError("candidate path collision")
    else:
        d("cp","--",STAGE,DEST);d("chmod","0644",DEST)
    if csha(DEST)!=CAND:raise RuntimeError("candidate copy mismatch")
    if retry:
        if original!=backup.read_bytes() or updated!=patched.read_bytes():raise RuntimeError("prior backup mismatch; restore original first")
    else:
        backup.write_bytes(original);patched.write_bytes(updated)
    print("V25_LAUNCHER_BACKUP="+str(backup),flush=True)
    touched=False
    try:
        if d("cat",LAUNCH).stdout!=original or pid()!=n:raise RuntimeError("launcher/process changed")
        touched=True
        # Stop only authorized WorldSvr, then edit its launcher and start.
        stop()
        write_launcher(updated)
        print("V25_START_TARGET_ONLY="+P,flush=True)
        start()
        new=verify(TRIAL,True)
        marker="DIAMOND_V23_NATIVE_REGISTER=OBSERVE_ONLY"
        logs=""
        for _ in range(12):
            if pid()!=new or not running():raise RuntimeError("WorldSvr unstable")
            logs=t("supervisorctl","tail","-20000",P,"stderr",check=False)
            if marker in logs:break
            if "DIAMOND_V23_NATIVE_REGISTER=BLOCKED_" in logs:raise RuntimeError("observer registration blocked")
            time.sleep(5)
        if marker not in logs:raise RuntimeError("native observer marker absent")
        time.sleep(5)
        if verify(TRIAL,True)!=new:raise RuntimeError("WorldSvr restarted unexpectedly")
        after=states()
        if {k:v for k,v in before.items() if k!=P}!={k:v for k,v in after.items() if k!=P}:
            raise RuntimeError("other supervisor service state changed")
        report={"old_pid":n,"new_pid":new,"observer_registered":True,"preloads_preserved_except_lib":True,"shared_lib_unchanged":True,"rankup_enabled":False,"sql_modified":False,"launcher_backup":str(backup)}
        (ROOT/"observer-v25.json").write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps(report,indent=2))
        print("DIAMOND_V25_OBSERVER=ACTIVE",flush=True)
    except BaseException:
        if touched:rollback(original,updated)
        raise
if __name__=="__main__":
    try:main()
    except Exception as e:
        print("DIAMOND_V25_OBSERVER=STOP "+str(e),flush=True)
        sys.exit(2)
