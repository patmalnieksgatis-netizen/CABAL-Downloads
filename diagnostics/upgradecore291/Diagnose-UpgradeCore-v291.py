#!/usr/bin/env python3
"""Read-only CABAL v291/EP39 WorldSvr Upgrade/Perfect Core disconnect audit.

Run ON THE TEST VM HOST (where docker CLI controls cabal_main):
  python3 Diagnose-UpgradeCore-v291.py --seconds 60 --out /tmp/upgradecore-audit.json

During sampling, reproduce ONE Upgrade Core or Perfect Core disconnect from
an authorized game client. Repeat separately with a Force Core control test.
No restart, DB query/write, hook, patch, debugger attachment or network sniff.
Reports can contain account identifiers and IPs: keep reports PRIVATE.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

CONTAINER = "cabal_main"
WORLD = "WorldSvr_01_01"
FILTER = re.compile(
    r"upgrad|perfect|core|packet|opcode|command|disconnect|kick|"
    r"exception|invalid|mismatch|assert|error|fatal|sigsegv|sigabrt|"
    r"worldsvr|usermap|unknown|unregistered|refus|close|client",
    re.IGNORECASE,
)
MAX_LINES_PER_LOG = 140
INNER = r'''
import glob, json, os, pathlib, re
positions = json.loads(POSITIONS)
patterns = ['/var/log/supervisor/*WorldSvr*',
            '/var/log/cabal/*WorldSvr*',
            '/var/log/supervisor/*worldsvr*',
            '/var/log/cabal/*worldsvr*']
files = sorted({f for p in patterns for f in glob.glob(p) if os.path.isfile(f)})
rows=[]
needle=re.compile(r'upgrad|perfect|core|packet|opcode|command|disconnect|kick|exception|invalid|mismatch|assert|error|fatal|sigsegv|sigabrt|worldsvr|usermap|unknown|unregistered|refus|close|client', re.I)
for path in files[:40]:
    try:
        st=os.stat(path)
        base=positions.get(path, {})
        start=base.get('size',0) if base.get('inode') == st.st_ino and st.st_size >= base.get('size',0) else 0
        # Read at most the newest 2MB of post-baseline data per file.
        start=max(start,st.st_size-2*1024*1024)
        entry={'path':path,'inode':st.st_ino,'size':st.st_size,
               'offset':start,'rotated_or_truncated': bool(base and (base.get('inode') != st.st_ino or base.get('size',0)>st.st_size))}
        if ENABLE_EXCERPTS:
            with open(path,'rb') as f:
                f.seek(start)
                raw=f.read(2*1024*1024)
            lines=raw.decode('utf-8','replace').splitlines()
            match=[line[:700] for line in lines if needle.search(line)]
            entry['matched_lines']=match[-140:]
            entry['new_lines']=len(lines)
            entry['matches']=len(match)
        rows.append(entry)
    except OSError as exc:
        rows.append({'path':path,'error':str(exc)})
cores=[]
for patt in ['/etc/cabal_etc/core/*WorldSvr*', '/etc/cabal_etc/core/core*', '/var/lib/cabal/core*']:
    for f in glob.glob(patt)[:30]:
        try:
            if os.path.isfile(f):
                st=os.stat(f)
                cores.append({'path':f,'size':st.st_size,'mtime':st.st_mtime})
        except OSError:
            pass
print(json.dumps({'files':rows,'corefiles':cores},ensure_ascii=False))
'''


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run(args, stdin=None, timeout=15):
    p = subprocess.run(args, input=stdin, text=True, capture_output=True, timeout=timeout)
    return {"rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr[:1200]}


def inside_logs(positions=None, excerpts=False):
    script = "POSITIONS=" + repr(json.dumps(positions or {})) + "\n"
    script += "ENABLE_EXCERPTS=" + repr(excerpts) + "\n" + INNER
    p = run(["docker", "exec", "-i", CONTAINER, "python3", "-"], script, timeout=25)
    if p["rc"]:
        return {"error": "CONTAINER_PYTHON_UNAVAILABLE", "detail": p["stderr"]}
    try:
        return json.loads(p["stdout"])
    except json.JSONDecodeError:
        return {"error": "INVALID_LOG_SNAPSHOT", "detail": p["stdout"][-500:]}


def service_snapshot():
    p = run(["docker", "exec", CONTAINER, "supervisorctl", "status"], timeout=12)
    # supervisorctl may return code 3 when some services are stopped.
    if p["rc"] not in (0, 3):
        return {"error": p["stderr"], "exit_code": p["rc"]}
    services = []
    for line in p["stdout"].splitlines():
        m = re.match(r"^(WorldSvr_\S+)\s+(RUNNING|STOPPED|STARTING|BACKOFF|EXITED|FATAL)\s*(.*)$", line)
        if m:
            services.append({"name": m.group(1), "state": m.group(2), "detail": m.group(3)[:180]})
    pids = {}
    for entry in services:
        if entry["state"] == "RUNNING":
            v = run(["docker", "exec", CONTAINER, "supervisorctl", "pid", entry["name"]], timeout=10)
            pids[entry["name"]] = int(v["stdout"].strip()) if v["stdout"].strip().isdigit() else None
    return {"services": services, "pids": pids}


def compare(samples):
    pids = [sample.get("snapshot", {}).get("pids", {}).get(WORLD) for sample in samples]
    states = []
    for sample in samples:
        for service in sample.get("snapshot", {}).get("services", []):
            if service["name"] == WORLD:
                states.append(service["state"])
                break
    valid = [pid for pid in pids if isinstance(pid, int) and pid > 0]
    if not valid:
        result = "WORLD_PROCESS_NOT_OBSERVED"
    elif len(set(valid)) > 1:
        result = "WORLD_PID_CHANGED_RESTART_POSSIBLE"
    elif any(state != "RUNNING" for state in states):
        result = "WORLD_NON_RUNNING_STATE_SEEN"
    else:
        result = "WORLD_PID_STABLE_IN_SAMPLES"
    return {"world_observation": result, "observed_pids": sorted(set(valid)),
            "states_seen": sorted(set(states)),
            "note": "Stable PID does NOT prove correct server response or packet compatibility."}


def main():
    import os
    os.umask(0o077)  # Secure new report files from creation, not only after writing.
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seconds", type=int, default=60, help="Sampling window, 5 to 300 seconds")
    ap.add_argument("--interval", type=float, default=1.0, help="PID/status sampling period in seconds")
    ap.add_argument("--case", choices=["upgrade", "perfect", "force-control"], default="upgrade")
    ap.add_argument("--out", type=Path, required=True, help="Private local JSON report path")
    args = ap.parse_args()
    if not 5 <= args.seconds <= 300 or not 0.5 <= args.interval <= 10:
        ap.error("seconds must be 5..300 and interval 0.5..10")
    if shutil.which("docker") is None:
        sys.exit("Docker CLI not available: run on the TEST VM host")
    started = now()
    before = inside_logs()
    positions = {d["path"]: {"inode": d["inode"], "size": d["size"]}
                 for d in before.get("files", []) if "inode" in d}
    samples = []
    until = time.monotonic() + args.seconds
    print(f"{started} CASE={args.case}; observe WorldSvr for {args.seconds}s; read-only",flush=True)
    while time.monotonic() < until:
        samples.append({"at": now(), "snapshot": service_snapshot()})
        time.sleep(min(args.interval, max(0, until-time.monotonic())))
    after = inside_logs(positions, excerpts=True)
    dockerlog = run(["docker", "logs", "--since", started,
                     "--tail", "800", CONTAINER], timeout=20)
    matches = [x[:700] for x in (dockerlog["stdout"]+"\n"+dockerlog["stderr"]).splitlines() if FILTER.search(x)]
    report = {
        "case": args.case, "started_utc": started, "finished_utc": now(),
        "environment": "test VM", "container": CONTAINER, "world": WORLD,
        "read_only": True, "status": compare(samples),
        "samples": samples, "before": before, "after": after,
        "docker_logs": {"rc": dockerlog["rc"], "matched_lines": matches[-MAX_LINES_PER_LOG:]},
        "limitations": ["Does not record packets unless the existing server logging already does.",
                        "Cannot distinguish malformed C2S from S2C without a trusted packet capture or client trace.",
                        "No claim of bug fix or real gameplay success.",
                        "Keep this report private: logs can include IPs, account details or item identifiers."],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        args.out.chmod(0o600)
    except OSError:
        pass
    print(json.dumps({"report": str(args.out), **report["status"]}, ensure_ascii=False))
    print("REPORT_PRIVATE=YES; NO_SERVER_MUTATIONS=YES; GAMEPLAY_FIX_VERIFIED=NO")


if __name__ == "__main__":
    main()
