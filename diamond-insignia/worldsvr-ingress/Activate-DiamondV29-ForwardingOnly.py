#!/usr/bin/env python3
"""V29: CH1-only V28 forwarding trial. Native registration intentionally blocked. Automatic restore on failure."""
import hashlib,json,pathlib,re,subprocess,sys,time,os
C="cabal_main"; P="WorldSvr_01_01"
LAUNCH="/usr/bin/WorldSvr_01_01"
LIVE="/usr/lib/cabal/lib.so"
STAGE=pathlib.Path("/tmp/cabal-diamond-v28-gjkifghe/build/Diamond291_Startup_V28.so")
DEST="/usr/lib/cabal/Diamond291_Startup_V28.so"
ROOT=pathlib.Path("/root/cabal-diamond-v23-deploy-a1fpo5tp")
BASE="6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab"
CAND="ec5810489581e7bc10ac17ab96c1c5ff4752e4d53a403e972aca3920ae652857"
WORLD="caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3"
EXPECTED=[
"/etc/cabal/migration_tools/ep36-costume-trial-v1/mileage-v1/EP36CostumeMileage.so",
LIVE,"/usr/lib/cabal/libchilkat-9.5.0.so","/usr/lib/cabal/libPolyHook_2.so",
"/usr/lib/cabal/libZycore.so.1.4","/usr/lib/cabal/libZydis.so.4.0",
"/usr/lib/cabal/guardian-v1/GuardianArcana-v1.so",
"/usr/lib/cabal/skillbook291/SkillBook291.so",
"/usr/lib/cabal/cashshop291/CashShop291.so"]
TRIAL=EXPECTED[:1]+[DEST]+EXPECTED[1:]
MARK="    os.execve(NATIVE,['/usr/bin/WorldSvr_01_01',*sys.argv[1:]],environment)"
PATCH="""    # V29 forwarding only: no native map registration, no SQL.
    diamond_tokens=environment.get('LD_PRELOAD','').split()
    if diamond_tokens.count('/usr/lib/cabal/lib.so')!=1 or '/usr/lib/cabal/Diamond291_Startup_V28.so' in diamond_tokens:
        raise ValueError('DIAMOND_V29_PRELOAD_MISMATCH')
    if digest(Path('/usr/lib/cabal/Diamond291_Startup_V28.so'))!='ec5810489581e7bc10ac17ab96c1c5ff4752e4d53a403e972aca3920ae652857':
        raise ValueError('DIAMOND_V29_ADAPTER_HASH_MISMATCH')
    diamond_tokens.insert(diamond_tokens.index('/usr/lib/cabal/lib.so'),'/usr/lib/cabal/Diamond291_Startup_V28.so')
    environment['LD_PRELOAD']=' '.join(diamond_tokens)
    environment['CABAL_DIAMOND_V28_NATIVE_OBSERVER']='1'
    environment['CABAL_DIAMOND_V28_STARTUP_RETURN']='0'
"""
def d(*a,check=True,data=None,timeout=120):
    p=subprocess.run(["docker","exec",*(["-i"] if data is not None else []),C,*a],input=data,capture_output=True,timeout=timeout)
    if check and p.returncode:raise RuntimeError("command failed: "+repr(a[:3])+" rc="+str(p.returncode)+" "+p.stderr.decode(errors="replace")[-700:])
    return p
def t(*a,**kw):return d(*a,**kw).stdout.decode(errors="replace").strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def csha(p):return t("sha256sum",p).split()[0]
def target():
    p=d("supervisorctl","status",P,check=False)
    line=p.stdout.decode(errors="replace").strip()
    m=re.fullmatch(r"WorldSvr_01_01\s+(RUNNING|STARTING|STOPPING|STOPPED|EXITED|FATAL|BACKOFF)(?:\s+.*)?",line)
    if not m:raise RuntimeError("unrecognized supervisor status: "+line[:200])
    pm=re.search(r"\bpid (\d+),",line)
    return m.group(1),int(pm.group(1)) if pm else 0
def pid():
    return target()[1]
def ctl(action):
    p=d("supervisorctl",action,P,check=False,timeout=180)
    print("V29_"+action.upper()+"_RC="+str(p.returncode)+" "+(p.stdout+p.stderr).decode(errors="replace").strip()[:400],flush=True)
    return p.returncode
def wait_state(wanted,seconds=90):
    deadline=time.monotonic()+seconds
    last=None
    while time.monotonic()<deadline:
        state,n=target()
        if state!=last:
            print("V29_STATE="+state,flush=True);last=state
        if state in wanted:return state,n
        if "RUNNING" in wanted and state in ("STOPPED","EXITED","FATAL"):return state,n
        time.sleep(2)
    return target()
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
    if observer and (b"CABAL_DIAMOND_V28_NATIVE_OBSERVER=1" not in env or b"CABAL_DIAMOND_V28_STARTUP_RETURN=0" not in env):
        raise RuntimeError("observer env not present")
    paths={w[5] for l in t("cat","/proc/"+str(n)+"/maps").splitlines() if len(w:=l.split(None,5))==6}
    if not all(x in paths for x in expected):raise RuntimeError("expected preload missing in maps")
    if not observer and DEST in paths:raise RuntimeError("observer module remained mapped")
    if csha(LIVE)!=BASE:raise RuntimeError("original shared library changed")
    return n
def stop():
    state,_=target()
    if state not in ("STOPPED","EXITED","FATAL"):
        ctl("stop")
    state,_=wait_state({"STOPPED","EXITED","FATAL"},45)
    if state not in ("STOPPED","EXITED","FATAL"):raise RuntimeError("stop incomplete: "+state)
def start():
    state,_=target()
    if state in ("STARTING","BACKOFF"):
        state,_=wait_state({"RUNNING"},90)
    if state=="RUNNING":return
    if state=="STOPPING":
        state,_=wait_state({"STOPPED","EXITED","FATAL"},45)
    if state not in ("STOPPED","EXITED","FATAL"):raise RuntimeError("cannot start from "+state)
    ctl("start")
    state,_=wait_state({"RUNNING"},90)
    if state!="RUNNING":raise RuntimeError("original startup failed: "+state)
def write_launcher(data):
    # Preserve launcher ownership and permissions; atomic rename.
    d("sh","-c",'set -eu; t=$(mktemp "$1.diamond.XXXXXXXX"); cp -p "$1" "$t"; cat > "$t"; mv -f "$t" "$1"',"sh",LAUNCH,data=data)
    if d("cat",LAUNCH).stdout!=data:raise RuntimeError("launcher write mismatch")

def fresh_logs(path,offset):
    current=d("sh","-c","ls -t /var/log/supervisor/WorldSvr_01_01-stderr---supervisor-*.log | head -1").stdout.decode().strip()
    if not current:raise RuntimeError("no target stderr log")
    size=int(t("stat","-c","%s",current))
    start=offset if current==path and size>=offset else 0
    return t("tail","-c","+"+str(start+1),current)
def main():
    os.umask(0o077)
    original=(ROOT/"WorldSvr_01_01.launcher.original").read_bytes()
    if original.count(MARK.encode())!=1 or WORLD.encode() not in original:raise RuntimeError("original launcher backup mismatch")
    updated=original.replace(MARK.encode(),(PATCH+MARK).encode())
    compile(updated,LAUNCH,"exec")
    if csha(LIVE)!=BASE or sha(ROOT/"lib.so.original")!=BASE:raise RuntimeError("core hash mismatch")
    current=d("cat",LAUNCH).stdout
    if current not in (original,updated):raise RuntimeError("unknown launcher; refusing overwrite")
    def restore():
        print("V29_RESTORE_ORIGINAL",flush=True)
        now=d("cat",LAUNCH).stdout
        if now not in (original,updated):raise RuntimeError("external launcher change")
        if now==updated:
            stop();write_launcher(original)
        start()
        print("V29_ROLLBACK=PASS pid="+str(verify(EXPECTED,False)),flush=True)
    if "--rollback" in sys.argv:
        restore();return
    if "--apply-forwarding" not in sys.argv:raise RuntimeError("explicit --apply-forwarding required")
    if current!=original:raise RuntimeError("already trial launcher; use --rollback")
    old=verify(EXPECTED,False)
    if sha(STAGE)!=CAND:raise RuntimeError("V28 adapter SHA mismatch")
    if d("test","-e",DEST,check=False).returncode==0:
        if csha(DEST)!=CAND:raise RuntimeError("adapter path collision")
    else:
        p=subprocess.run(["docker","cp",str(STAGE),C+":"+DEST],capture_output=True)
        if p.returncode:raise RuntimeError("adapter staging failed")
        d("chmod","0644",DEST)
    if csha(DEST)!=CAND:raise RuntimeError("staged adapter mismatch")
    loader=t("ldd","-r",DEST)
    if "not found" in loader or "undefined symbol" in loader:raise RuntimeError("loader check failed: "+loader[-1500:])
    backup=ROOT/"WorldSvr_01_01.launcher.v29"
    if backup.exists() and backup.read_bytes()!=updated:raise RuntimeError("V29 backup collision")
    backup.write_bytes(updated)
    before=states()
    path=t("sh","-c","ls -t /var/log/supervisor/WorldSvr_01_01-stderr---supervisor-*.log | head -1")
    offset=int(t("stat","-c","%s",path))
    print("V29_PREFLIGHT=PASS; REGISTRATION=FORCED_OFF",flush=True)
    touched=False
    try:
        if verify(EXPECTED,False)!=old or d("cat",LAUNCH).stdout!=original:raise RuntimeError("baseline changed")
        touched=True
        stop();write_launcher(updated);start()
        new=verify(TRIAL,True)
        deadline=time.monotonic()+100
        while time.monotonic()<deadline:
            if target()!=("RUNNING",new):raise RuntimeError("trial unstable")
            logs=fresh_logs(path,offset)
            if "DIAMOND_V28_NATIVE_REGISTER=OBSERVE_ONLY" in logs:raise RuntimeError("unexpected registration")
            if "DIAMOND_V28_OPEN=BLOCKED_STARTUP_CALLSITE" in logs and "Complete Loading Data" in logs:break
            time.sleep(2)
        else:raise RuntimeError("forwarding or loading marker absent")
        if verify(TRIAL,True)!=new:raise RuntimeError("trial changed PID")
        after=states()
        if {k:v for k,v in before.items() if k!=P}!={k:v for k,v in after.items() if k!=P}:
            print("V29_OTHER_SERVICE_STATE_CHANGED_EXTERNALLY=YES",flush=True)
        for line in logs.splitlines():
            if any(x in line for x in ("DIAMOND_V28_", "EP39_GUARDIAN_V1=READY","COSTUME291_ADAPTER_READY","CH1_MILEAGE_ATTACHED","Complete Loading Data")):
                print("V29_LOG="+line[:400],flush=True)
        # Keep the validated forwarding-only trial running to avoid another interruption.
        touched=False
        report={"forwarding_verified":True,"native_registration":False,"rankup_verified":False,
                "original_core_unchanged":True,"original_launcher_restored":False,"sql_modified_by_adapter":False}
        (ROOT/"forwarding-v29.json").write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps(report,indent=2))
        print("DIAMOND_V29=FORWARDING_ONLY_ACTIVE")
    except BaseException:
        if touched:restore()
        raise
if __name__=="__main__":
    try:main()
    except Exception as e:
        print("DIAMOND_V29=STOP "+str(e),flush=True);sys.exit(2)
