#!/usr/bin/env python3
"""V26 recovery only. Inspect V25 trial, retain it only if proven healthy;
otherwise restore original launcher and CH1. No new observer deployment."""
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
    print("V26_"+action.upper()+"_RC="+str(p.returncode)+" "+(p.stdout+p.stderr).decode(errors="replace").strip()[:400],flush=True)
    return p.returncode
def wait_state(wanted,seconds=90):
    deadline=time.monotonic()+seconds
    last=None
    while time.monotonic()<deadline:
        state,n=target()
        if state!=last:
            print("V26_STATE="+state,flush=True);last=state
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
    if observer and b"CABAL_DIAMOND_V23_NATIVE_OBSERVER=1" not in env:
        raise RuntimeError("observer env not present")
    paths={w[5] for l in t("cat","/proc/"+str(n)+"/maps").splitlines() if len(w:=l.split(None,5))==6}
    if not all(x in paths for x in expected):raise RuntimeError("expected preload missing in maps")
    if observer and LIVE in paths:raise RuntimeError("both old and new lib.so mapped")
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
def log_evidence():
    # Output only narrowly selected diagnostic lines, not full game logs.
    logs=t("supervisorctl","tail","-20000",P,"stderr",check=False)
    selected=[line for line in logs.splitlines()
              if re.search(r"DIAMOND_V23_|LAUNCH_GUARD_FAILED|undefined symbol|cannot open shared object|segmentation fault|assertion.*failed|terminate called|GLIBC.*not found|error while loading shared libraries|symbol lookup error",line,re.I)]
    for line in selected[-15:]:print("V26_LOG="+line[:500],flush=True)
    return logs
def main():
    if "--recover" not in sys.argv:raise RuntimeError("explicit --recover required")
    if sha(ROOT/"lib.so.original")!=BASE or csha(LIVE)!=BASE:raise RuntimeError("original library hash mismatch")
    original=(ROOT/"WorldSvr_01_01.launcher.original").read_bytes()
    trial=(ROOT/"WorldSvr_01_01.launcher.v24").read_bytes()
    if original.count(MARK.encode())!=1 or trial!=original.replace(MARK.encode(),(PATCH+MARK).encode()):
        raise RuntimeError("launcher backups do not match approved patch")
    current=d("cat",LAUNCH).stdout
    if current not in (original,trial):raise RuntimeError("launcher changed externally; refusing overwrite")
    state,n=target()
    print("V26_INITIAL_STATE="+state+" LAUNCHER="+("ORIGINAL" if current==original else "TRIAL"),flush=True)
    logs=log_evidence()
    if current==trial:
        # Do not launch a fresh trial. An existing stable registered trial
        # can remain active, but incomplete registration must roll back.
        if state in ("STARTING","BACKOFF"):
            state,n=wait_state({"RUNNING"},90)
        if state=="RUNNING":
            try:
                n=verify(TRIAL,True)
                logs=log_evidence()
                if "DIAMOND_V23_NATIVE_REGISTER=OBSERVE_ONLY" not in logs:
                    raise RuntimeError("positive native registration marker missing")
                time.sleep(3)
                if verify(TRIAL,True)!=n:raise RuntimeError("unstable PID")
                print("DIAMOND_V26_RECOVERY=OBSERVER_ACTIVE pid="+str(n),flush=True)
                return
            except Exception as e:
                print("V26_TRIAL_NOT_CONFIRMED="+str(e),flush=True)
        print("V26_RESTORE_ORIGINAL",flush=True)
        log_evidence()
        stop()
        if d("cat",LAUNCH).stdout!=trial:raise RuntimeError("launcher changed during recovery")
        write_launcher(original)
    # If already running on original launcher, do NOT stop or restart it.
    start()
    n=verify(EXPECTED,False)
    print("DIAMOND_V26_RECOVERY=ORIGINAL_RUNNING pid="+str(n),flush=True)
if __name__=="__main__":
    try:main()
    except Exception as e:
        print("DIAMOND_V26_RECOVERY=STOP "+str(e),flush=True)
        sys.exit(2)
