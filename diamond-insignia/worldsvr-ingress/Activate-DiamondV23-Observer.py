#!/usr/bin/env python3
"""Owner-approved WorldSvr_01_01-only V23 observer trial.
Keep shared lib.so unchanged. Change only target supervisor program's
preload entry and observer environment. Restore original config on failure.
No SQL writes, no VM/container/network restart.
"""
import hashlib,json,pathlib,re,subprocess,sys,time,os
C="cabal_main"; P="WorldSvr_01_01"
LIVE="/usr/lib/cabal/lib.so"
STAGE="/tmp/cabal-diamond-v23-stage-U9ZoMeDT/libDiamondV23_NativeStartup_OFFLINE.so"
DEST="/usr/lib/cabal/libDiamondV23_Observer_8ecc2cd6.so"
CFG="/etc/cabal_scripts/cabal_services/cabal_server1.conf"
ROOT=pathlib.Path("/root/cabal-diamond-v23-deploy-a1fpo5tp")
BASE="6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab"
CAND="8ecc2cd687b650719b69d952f17ca658fc627ffea8b560b48f255c05f319bcec"
WORLD="caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3"
def run(args,check=True,data=None,timeout=120):
    p=subprocess.run(args,input=data,capture_output=True,timeout=timeout)
    if check and p.returncode:raise RuntimeError("command failed: "+repr(args[:5])+" rc="+str(p.returncode))
    return p
def d(*a,check=True,data=None,timeout=120):
    return run(["docker","exec",*(["-i"] if data is not None else []),C,*a],check,data,timeout)
def t(*a,check=True,timeout=120):return d(*a,check=check,timeout=timeout).stdout.decode(errors="replace").strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def csha(p):return t("sha256sum",p).split()[0]
def pid():
    s=t("supervisorctl","pid",P)
    return int(s) if s.isdigit() else 0
def states():
    s=t("supervisorctl","status",check=False)
    return {l.split()[0]:l.split()[1:4] for l in s.splitlines() if len(l.split())>=2}
def running():
    s=states().get(P,[])
    return bool(s and s[0]=="RUNNING")
def setcfg(data):
    # Atomic same-directory replacement, preserving existing metadata.
    d("sh","-c",'set -eu; t=$(mktemp "$1.diamond.XXXXXXXX"); cp -p "$1" "$t"; cat > "$t"; mv -f "$t" "$1"',"sh",CFG,data=data)
    if d("cat",CFG).stdout!=data:raise RuntimeError("config write verification failed")
def reread():
    p=d("supervisorctl","reread")
    return p.stdout.decode(errors="replace").strip()
def ensure_only_target(s):
    for line in s.splitlines():
        if line.strip() in ("","No config updates to processes"):continue
        if line.strip()!=P+": changed":raise RuntimeError("unexpected pending supervisor config changes: "+line)
def start_target():
    if not running():
        d("supervisorctl","start",P,timeout=180)
    if not running() or pid()<=1:raise RuntimeError("target did not reach RUNNING")
def stop_target():
    if pid()>1 or running():d("supervisorctl","stop",P,timeout=180)
    if pid()>1:raise RuntimeError("target still active")
def verify_world(expected_path,expected_sha,env_required):
    n=pid()
    if n<=1 or not running():raise RuntimeError("target not RUNNING")
    if csha("/proc/"+str(n)+"/exe")!=WORLD:raise RuntimeError("restarted WorldSvr hash mismatch")
    maps=t("cat","/proc/"+str(n)+"/maps")
    if not any(l.split(None,5)[-1]==expected_path for l in maps.splitlines() if len(l.split(None,5))==6):
        raise RuntimeError("expected module not mapped")
    if csha(expected_path)!=expected_sha:raise RuntimeError("module hash mismatch")
    if env_required:
        e=d("cat","/proc/"+str(n)+"/environ").stdout.split(b"\0")
        if b"CABAL_DIAMOND_V23_NATIVE_OBSERVER=1" not in e:raise RuntimeError("observer environment not present")
    return n
def rollback(original):
    print("V23_ROLLBACK_BEGIN",flush=True)
    stop_target()
    setcfg(original)
    ensure_only_target(reread())
    d("supervisorctl","update",P,timeout=180)
    start_target()
    n=verify_world(LIVE,BASE,False)
    print("V23_ROLLBACK=PASS pid="+str(n),flush=True)
def main():
    os.umask(0o077)
    original_backup=ROOT/"supervisor.original.conf"
    if "--rollback" in sys.argv:
        if not original_backup.is_file():raise RuntimeError("no saved supervisor config")
        if csha(LIVE)!=BASE:raise RuntimeError("shared original library changed")
        current=d("cat",CFG).stdout
        trial=ROOT/"supervisor.v23.conf"
        if not trial.is_file() or current not in (trial.read_bytes(),original_backup.read_bytes()):
            raise RuntimeError("configuration changed externally; refusing overwrite")
        rollback(original_backup.read_bytes())
        return
    if "--apply-observer" not in sys.argv:raise RuntimeError("explicit --apply-observer required")
    if original_backup.exists():raise RuntimeError("trial already prepared; use --rollback or inspect report")
    if sha(ROOT/"lib.so.original")!=BASE or csha(LIVE)!=BASE or csha(STAGE)!=CAND:
        raise RuntimeError("preflight hash mismatch")
    oldpid=verify_world(LIVE,BASE,False)
    original=d("cat",CFG).stdout
    cfg=original.decode("utf-8")
    # Require the exact named program section and an unambiguous LD_PRELOAD.
    pat=r"(?ms)^\[program:"+re.escape(P)+r"\][^\n]*\n.*?(?=^\[|\Z)"
    matches=list(re.finditer(pat,cfg))
    if len(matches)!=1:raise RuntimeError("target config section missing or ambiguous")
    m=matches[0]; section=m.group(0)
    commands=list(re.finditer(r'(?m)^command\s*=[^\r\n]+',section))
    if len(commands)!=1:raise RuntimeError("ambiguous command")
    command=commands[0].group(0)
    preload=list(re.finditer(r'LD_PRELOAD="([^"]+)"',command))
    if len(preload)!=1 or "CABAL_DIAMOND_V23_NATIVE_OBSERVER" in section:
        raise RuntimeError("unexpected preload/observer config")
    libs=preload[0].group(1).split()
    if libs.count(LIVE)!=1 or DEST in libs:raise RuntimeError("unexpected original preload list")
    env=d("cat","/proc/"+str(oldpid)+"/environ").stdout.split(b"\0")
    actual=[x[len(b"LD_PRELOAD="):].decode().split() for x in env if x.startswith(b"LD_PRELOAD=")]
    if actual!=[libs]:raise RuntimeError("running preload differs from supervisor config")
    if not re.search(r"(?m)^autostart\s*=\s*(?:true|false)\s*$",section,re.I):
        raise RuntimeError("unexpected supervisor autostart config")
    # Replace one token inside only this program command, preserve every
    # other preload and option. Do not replace the shared library.
    new_command=command.replace('LD_PRELOAD="','CABAL_DIAMOND_V23_NATIVE_OBSERVER=1 LD_PRELOAD="',1).replace(LIVE,DEST,1)
    new_section=section[:commands[0].start()]+new_command+section[commands[0].end():]
    updated=(cfg[:m.start()]+new_section+cfg[m.end():]).encode()
    ensure_only_target(reread())
    # Stage persistent distinct filename, refusing to overwrite other files.
    if d("test","-e",DEST,check=False).returncode==0:
        if csha(DEST)!=CAND:raise RuntimeError("destination collision")
    else:
        d("cp","--",STAGE,DEST)
        d("chmod","0644",DEST)
    if csha(DEST)!=CAND:raise RuntimeError("persistent candidate checksum mismatch")
    original_backup.write_bytes(original)
    (ROOT/"supervisor.v23.conf").write_bytes(updated)
    before=states()
    touched=False
    try:
        if d("cat",CFG).stdout!=original or pid()!=oldpid:raise RuntimeError("live config/process changed")
        touched=True
        setcfg(updated)
        ensure_only_target(reread())
        print("V23_RESTART_TARGET_ONLY="+P,flush=True)
        stop_target()
        d("supervisorctl","update",P,timeout=180)
        start_target()
        n=verify_world(DEST,CAND,True)
        # Check original startup and positive native observer marker.
        logs=""
        for _ in range(12):
            if pid()!=n or not running():raise RuntimeError("target unstable")
            logs=t("supervisorctl","tail","-20000",P,"stderr",check=False)
            if "DIAMOND_V23_NATIVE_REGISTER=OBSERVE_ONLY" in logs:break
            if "DIAMOND_V23_NATIVE_REGISTER=BLOCKED_" in logs:
                raise RuntimeError("native observer registration blocked")
            time.sleep(5)
        if "DIAMOND_V23_NATIVE_REGISTER=OBSERVE_ONLY" not in logs:
            raise RuntimeError("positive native registration marker absent")
        time.sleep(5)
        if verify_world(DEST,CAND,True)!=n or csha(LIVE)!=BASE:raise RuntimeError("post-start stability check failed")
        after=states()
        changed=[k for k,v in before.items() if k!=P and (k not in after or v[:2]!=after[k][:2] or (v[0]=="RUNNING" and v[2:3]!=after[k][2:3]))]
        if changed:raise RuntimeError("other supervisor process state changed: "+str(changed))
        report={"old_pid":oldpid,"new_pid":n,"observer_registered":True,"shared_library_unchanged":True,"sql_modified":False,"rankup_enabled":False,"config_backup":str(original_backup)}
        (ROOT/"observer-trial.json").write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps(report,indent=2))
        print("DIAMOND_V23_OBSERVER=ACTIVE")
    except BaseException:
        if touched:rollback(original)
        raise
if __name__=="__main__":
    try:main()
    except Exception as e:
        print("DIAMOND_V23_OBSERVER=STOP "+str(e),flush=True)
        sys.exit(2)
