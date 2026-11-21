#!/usr/bin/env python3
"""WorldSvr opcode 951 validation branch locator, read-only.

Runs on the VirtualBox *Linux VM host* where docker CLI controls cabal_main.
It reads /proc/PID/exe from within cabal_main, then analyzes a temporary private
binary copy using local objdump (if available). No injection, tracing, patches,
DB actions, restart, player session reads, or service changes.

Output: ELF identity, target string file offset/virtual address, nearby xrefs.
Do not publish the full native server binary.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile

NEEDLE = b"Invalid recvPacket->wPayLoadLen or recvPacket->escapeSlotCount"
PROCESS = "WorldSvr_01_01"
CONTAINER = "cabal_main"
MARK = re.compile(r"^\s*([0-9a-fA-F]+):")
# GNU objdump prints target after comment; do not guess based only on nearby names.
REF = re.compile(r"#\s*(?:0x)?([0-9a-fA-F]+)\b")

def cmd(args, timeout=20):
    return subprocess.run(args, check=True, capture_output=True, timeout=timeout)

def get_binary():
    pid_out = cmd(["docker", "exec", CONTAINER, "supervisorctl", "pid", PROCESS]).stdout.decode("ascii", "replace").strip()
    if not pid_out.isdigit() or int(pid_out) == 0:
        raise RuntimeError("WORLD_PID_NOT_RUNNING")
    pid = int(pid_out)
    # subprocess captures only the WorldSvr *executable*, not its process memory.
    exe = cmd(["docker", "exec", CONTAINER, "sh", "-c",
               "cat /proc/" + str(pid) + "/exe"], timeout=45).stdout
    if not exe.startswith(b"\x7fELF"):
        raise RuntimeError("NOT_AN_ELF_EXECUTABLE")
    return pid, exe

def elf_va(binary, file_offset):
    """Map a file offset to VA through ELF64 section headers, or return None."""
    if binary[4] != 2 or binary[5] != 1:
        return None
    try:
        shoff = struct.unpack_from("<Q", binary, 0x28)[0]
        shentsize, shnum = struct.unpack_from("<HH", binary, 0x3A)
        if shentsize < 64 or shnum > 4096 or shoff + shentsize * shnum > len(binary):
            return None
        for i in range(shnum):
            pos = shoff + i * shentsize
            typ = struct.unpack_from("<I", binary, pos + 4)[0]
            addr, off, size = struct.unpack_from("<QQQ", binary, pos + 16)
            if typ != 8 and off <= file_offset < off + size:  # exclude NOBITS
                return addr + file_offset - off
    except (struct.error, ValueError):
        return None
    return None

def xrefs(binary, va):
    if va is None or shutil.which("objdump") is None:
        return [], "OBJDUMP_OR_ADDRESS_NOT_AVAILABLE"
    with tempfile.TemporaryDirectory(prefix="upgrade951-") as td:
        p = Path(td) / "WorldSvr_01_01"
        p.write_bytes(binary)
        p.chmod(0o600)
        proc = subprocess.Popen(["objdump", "-d", "-M", "intel", str(p)],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, errors="replace")
        before = deque(maxlen=35)
        results, after, pending = [], 0, None
        try:
            for line in proc.stdout:
                line = line.rstrip()
                if after:
                    pending.append(line)
                    after -= 1
                    if not after:
                        results.append(pending)
                        pending = None
                    continue
                m = REF.search(line)
                if m and int(m.group(1),16)==va:
                    pending = list(before) + [line]
                    after = 22
                else:
                    before.append(line)
                if len(results)>=10:
                    break
            if pending:
                results.append(pending)
        finally:
            proc.kill()  # only temporary objdump child; never kills server
            proc.communicate()
    return results, None if results else "NO_DIRECT_RIP_XREF_FOUND"

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,default=Path("/tmp/upgrade951-handler.json"))
    args=p.parse_args()
    os.umask(0o077)
    pid,binary = get_binary()
    offset = binary.find(NEEDLE)
    va = elf_va(binary, offset) if offset>=0 else None
    refs,reason = xrefs(binary, va)
    report = {
        "read_only":True,"world_process":PROCESS,"pid":pid,
        "bytes":len(binary),"sha256":hashlib.sha256(binary).hexdigest(),
        "error_string_present":offset>=0,
        "error_string_file_offset":hex(offset) if offset>=0 else None,
        "error_string_va":hex(va) if va is not None else None,
        "xrefs":refs,"xref_limitation":reason,
        "note":"This locates the validator check; it does not modify WorldSvr or prove wire format.",
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2))
    args.out.chmod(0o600)
    compact={k:v for k,v in report.items() if k not in ("xrefs",)}
    compact["xref_matches"]=len(refs)
    print(json.dumps(compact))
    print("PRIVATE_REPORT="+str(args.out))
    print("SERVER_UNCHANGED=YES")

if __name__=="__main__":
    main()
