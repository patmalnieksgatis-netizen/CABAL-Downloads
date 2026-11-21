#!/usr/bin/env python3
"""One-shot live WorldSvr 951 packet-shape probe.

Run on *Linux VirtualBox VM host*, where root can run docker, gdb and inspect
/proc (not on Windows and not in Github Actions). The script only observes
the next 951 Upgrade Core/Perfect Core action, then gdb detaches immediately.
Test VM only: gdb attach momentarily pauses a service. No changes to item,
inventory, server binary, client binary or database.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile

CONTAINER="cabal_main"
SERVICE="WorldSvr_01_01"
EXPECTED_SHA="caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3"
BREAK_ADDRESS="0x7ac0f0"

def run(argv):
    x=subprocess.run(argv,capture_output=True,text=True,check=True,timeout=20)
    return x.stdout.strip()

def select_host_pid(inner_pid):
    candidates=[]
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():continue
        try:
            status=(d/"status").read_text()
            match=re.search(r"(?m)^NSpid:\s+([\d\s]+)$",status)
            if not match or int(match.group(1).split()[-1])!=inner_pid:continue
            exe=(d/"exe").read_bytes()
            if hashlib.sha256(exe).hexdigest()==EXPECTED_SHA:
                candidates.append((int(d.name),exe))
        except (OSError,ValueError,PermissionError):
            pass
    if len(candidates)!=1:
        raise RuntimeError("WORLD_HOST_PID_NOT_UNIQUE_OR_BINARY_HASH_CHANGED: matched="+str(len(candidates)))
    return candidates[0]

def extract_header(gdb_stdout):
    """Parse 48 or 19 raw bytes between GDB markers, excluding address labels."""
    first = gdb_stdout.find("OPCODE_951_HEADER_BEGIN")
    last = gdb_stdout.find("OPCODE_951_HEADER_END",first)
    if first < 0 or last < 0:
        return None
    section = gdb_stdout[first+len("OPCODE_951_HEADER_BEGIN"):last]
    values = re.findall(r"(?<![0-9a-fA-F])0x([0-9a-fA-F]{2})(?![0-9a-fA-F])",section)
    if len(values) not in (19,48):
        return None
    return bytes(int(v,16) for v in values)

def infer_layout(header):
    if not header or len(header) < 19:
        return {"status":"NO_HEADER"}
    declared=struct.unpack_from("<H",header,2)[0]
    escape=struct.unpack_from("<H",header,17)[0]
    expected=139+2*escape
    implied=(declared-139)//2 if declared>=139 and (declared-139)%2==0 else None
    candidates=[]
    if implied is not None and implied<=521:
        for off in range(14,len(header)-1):
            if struct.unpack_from("<H",header,off)[0]==implied:
                candidates.append(off)
    return {"declared":declared,"legacy_escape_count":escape,"legacy_expected":expected,
        "length_delta":declared-expected,"length_implied_escape_count":implied,
        "possible_shifted_offsets":[hex(i) for i in candidates],
        "status":"LEGACY_LENGTH_MATCH" if declared==expected and escape<=521 else "V291_HEADER_MISMATCH"}

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--out",type=Path,default=Path("/tmp/upgrade951-live-shape.txt"))
    args=a.parse_args()
    import os
    os.umask(0o077)
    if os.geteuid()!=0:raise SystemExit("ROOT_REQUIRED_ON_TEST_VM")
    for tool in ("gdb","docker"):
        if not shutil.which(tool):raise SystemExit(tool.upper()+"_NOT_INSTALLED_ON_VM")
    value=run(["docker","exec",CONTAINER,"supervisorctl","pid",SERVICE])
    if not value.isdigit() or int(value)<1:raise SystemExit("WORLD_SERVICE_NOT_RUNNING")
    host_pid,exe=select_host_pid(int(value))
    if exe[:4]!=b"\x7fELF" or struct.unpack_from("<H",exe,0x10)[0]!=2:
        raise SystemExit("WORLD_NOT_FIXED_ADDRESS_ELF_EXEC; DO_NOT_ATTACH")
    gdb_script=r'''set pagination off
set confirm off
set print pretty off
set logging file /dev/null
break *0x7ac0f0
commands
  silent
  printf "OPCODE_951_SHAPE actual_packet_len=%u escape_slot_count=%u expected_packet_len=%u core_slot_count=%u main_slot=%u\n", *(unsigned short*)($r15+2), *(unsigned short*)($r15+0x11), (139+2*(*(unsigned short*)($r15+0x11))), *(unsigned char*)($r15+0x10), *(unsigned short*)($r15+0x0e)
  printf "OPCODE_951_HEADER_BEGIN\n"
  if *(unsigned short*)($r15+2) >= 48
    x/48xb $r15
  else
    x/19xb $r15
  end
  printf "OPCODE_951_HEADER_END\n"
  detach
  quit
end
continue
'''
    print("VERIFIED_HASH="+EXPECTED_SHA,flush=True)
    print("HOST_PID="+str(host_pid),flush=True)
    print("Now reproduce ONE Upgrade Core or Perfect Core action in LAB. The probe detaches immediately after one packet.",flush=True)
    with tempfile.TemporaryDirectory(prefix="upgrade951-gdb-") as td:
        script=Path(td)/"probe.gdb";script.write_text(gdb_script);script.chmod(0o600)
        proc=subprocess.run(["gdb","-nx","-q","-batch","-p",str(host_pid),"-x",str(script)],
                            capture_output=True,text=True)
    lines=[line.strip() for line in (proc.stdout+"\n"+proc.stderr).splitlines() if "OPCODE_951_SHAPE" in line or
           re.search("ptrace|Operation not permitted|Cannot attach|not permitted|not installed",line,re.I)]
    args.out.parent.mkdir(parents=True,exist_ok=True)
    header = extract_header(proc.stdout)
    layout = infer_layout(header)
    private_report = {"lines":lines,"layout":layout,
                      "first_48_or_19_bytes_hex":header.hex() if header else None}
    args.out.write_text(json.dumps(private_report,indent=2)+"\n",encoding="utf-8");args.out.chmod(0o600)
    print(json.dumps({"gdb_rc":proc.returncode,"captured":any(x.startswith("OPCODE_951_SHAPE") for x in lines),
                       "report":str(args.out),"lines":lines,"layout":layout,
                       "header_bytes_saved_privately":len(header) if header else 0}))
    if not any(x.startswith("OPCODE_951_SHAPE") for x in lines):
        raise SystemExit("NO_951_PACKET_CAPTURED; server unchanged")
    print("NO_PATCH_APPLIED=YES")

if __name__=="__main__":
    main()
