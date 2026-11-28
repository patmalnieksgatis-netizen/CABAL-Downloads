#!/usr/bin/env python3
"""Read ONLY the CABAL ticket's two 4-byte runtime metadata fields.

Requires a separately authorized DISPOSABLE VM CLONE, exact WorldSvr ELF SHA,
per-PID clone marker and matching Linux machine-id. The Python process makes
no patches, ptrace writes, SQL calls, socket calls, nor game command requests.
A marker alone is not proof of a clone: the operator MUST verify the VM.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import sys

WORLD_SHA="caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3"
WORLD_SIZE=10596184
TICKET=33554961
METADATA_VA=0x13CAB48
METADATA_KIND_VA=METADATA_VA+0x38
METADATA_STACK_VA=METADATA_VA+0x3C
PURPOSE="DIAMOND_V291_DISPOSABLE_CLONE_METADATA_READ_ONLY"
class Reject(ValueError):pass

def classification(kind,stack):
    if stack<=1:
        return "singleton_metadata_stack_le_1"
    if kind in (0x43,0x46):
        return "option_unsigned_upper_10_bits"
    if kind in (0xAF,0xB8):
        return "option_unsigned_lower_16_bits"
    if kind in (0x10,0x1B,0x66):
        return "option_unsigned_lower_7_bits"
    return "option_numeric_unmasked"

def machine_id_text(text):
    token=text.strip()
    if len(token)!=32 or any(x not in "0123456789abcdef" for x in token):
        raise Reject("UNEXPECTED_MACHINE_ID")
    return token

def validate_marker(raw,machine_id,pid):
    if not isinstance(raw,dict) or set(raw)!={"purpose","machine_id","pid","world_sha256","ticket_item_id"}:
        raise Reject("UNEXPECTED_CLONE_MARKER_FIELDS")
    if raw["purpose"]!=PURPOSE or raw["machine_id"]!=machine_id or \
        type(raw["pid"]) is not int or raw["pid"]!=pid or \
        raw["world_sha256"]!=WORLD_SHA or raw["ticket_item_id"]!=TICKET:
        raise Reject("CLONE_MARKER_NOT_BOUND_TO_THIS_PROCESS")
    return True

def mapped_readable(maps,va,n):
    for line in maps.splitlines():
        fields=line.split()
        if len(fields)<2:
            continue
        lo_hi=fields[0].split("-")
        if len(lo_hi)!=2:
            continue
        try: lo,hi=(int(v,16) for v in lo_hi)
        except ValueError:continue
        if lo<=va and va+n<=hi and fields[1].startswith("r"):
            return True
    return False

def process_start_time(statline):
    # /proc/<pid>/stat's process name may contain spaces and ')' chars.
    right=statline.rfind(")")
    if right<0:raise Reject("PID_STAT_MALFORMED")
    fields=statline[right+2:].split() # starts with field 3 state
    if len(fields)<20:raise Reject("PID_STAT_TOO_SHORT")
    try:return int(fields[19]) # field 22 starttime
    except ValueError as exc:raise Reject("PID_STARTTIME_BAD") from exc

def checked_world_sha(exe:Path):
    digest=hashlib.sha256()
    with exe.open("rb") as inp:
        inp.seek(0,os.SEEK_END)
        if inp.tell()!=WORLD_SIZE:raise Reject("WRONG_RUNNING_WORLD_SIZE")
        inp.seek(0)
        for chunk in iter(lambda:inp.read(1024*1024),b""):
            digest.update(chunk)
    if digest.hexdigest()!=WORLD_SHA:raise Reject("WRONG_RUNNING_WORLD_SHA")

def capture(pid:int,marker:Path)->dict:
    if pid<1 or pid>2**31-1:raise Reject("PID_OUT_OF_RANGE")
    if marker.is_symlink() or not marker.is_file():
        raise Reject("CLONE_MARKER_NOT_REGULAR_FILE")
    metadata=marker.stat()
    if metadata.st_uid!=os.geteuid() or stat.S_IMODE(metadata.st_mode)&0o077:
        raise Reject("CLONE_MARKER_OWNER_OR_PERMISSIONS_UNSAFE")
    actual_machine_id=machine_id_text(Path("/etc/machine-id").read_text())
    validate_marker(json.loads(marker.read_text()),actual_machine_id,pid)
    proc=Path("/proc")/str(pid)
    start1=process_start_time((proc/"stat").read_text())
    checked_world_sha(proc/"exe")
    if not mapped_readable((proc/"maps").read_text(),METADATA_KIND_VA,8):
        raise Reject("TICKET_CATALOG_METADATA_NOT_READABLE")
    # Only 8 bytes of memory are ever read, at the verified item metadata
    # address; no item inventory, user name, account IDs or game secrets.
    fd=os.open(str(proc/"mem"),os.O_RDONLY|os.O_CLOEXEC)
    try:
        raw=os.pread(fd,8,METADATA_KIND_VA)
    finally:
        os.close(fd)
    if len(raw)!=8:raise Reject("SHORT_RUNTIME_METADATA_READ")
    start2=process_start_time((proc/"stat").read_text())
    if start1!=start2:raise Reject("PID_CHANGED_DURING_INSPECTION")
    kind,stack=struct.unpack("<Ii",raw)
    return {
        "status":"READ_ONLY_CLONE_RUNTIME_SNAPSHOT",
        "running_world_sha256":WORLD_SHA,
        "ticket_item_id":TICKET,
        "catalog_item_index":529,"catalog_variant":1,
        "metadata_address":hex(METADATA_VA),
        "kind_field38":kind,"kind_field38_hex":hex(kind),
        "stack_field3c_signed":stack,
        "quantity_decode_branch":classification(kind,stack),
        "safe_to_plan_real_game_ticket_debit": (
            stack<=1 or kind in (0x43,0x46,0xAF,0xB8,0x10,0x1B,0x66)
        ),
        "unknown_stack_count_type": (
            stack>1 and kind not in (0x43,0x46,0xAF,0xB8,0x10,0x1B,0x66)
        ),
        "metadata_from_real_verified_process":True,
        "runtime_write_attempted":False,
        "inventory_modified":False,"sql_modified":False,
        "diamond_gradeup_validated":False,
        "gameplay_persistence_validated":False,
    }
def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid",type=int,required=True,
                        help="WorldSvr PID INSIDE an isolated disposable clone")
    parser.add_argument("--clone-marker",type=Path,required=True,
                        help="restricted 0600 per-PID authorization JSON created only in clone")
    args=parser.parse_args(argv)
    try:result=capture(args.pid,args.clone_marker)
    except (Reject,OSError,ValueError,json.JSONDecodeError) as exc:
        print("DIAMOND_CLONE_TICKET_METADATA=REJECTED:",str(exc),file=sys.stderr)
        return 2
    print(json.dumps(result,indent=2))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
