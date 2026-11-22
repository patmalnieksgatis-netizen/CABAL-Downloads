#!/usr/bin/env python3
"""Read-only hash-pinned verification of exact legacy WorldSvr Merit byte evidence."""
import hashlib
import pathlib
import re
import subprocess
import sys

EXPECTED_WORLD_SHA256 = "caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3"

def disassemble(path, begin, end):
    return subprocess.run(
        ["objdump", "-d", "-M", "intel",
         f"--start-address={begin}", f"--stop-address={end}", str(path)],
        text=True, capture_output=True, check=True).stdout

def require(assembly, address, pattern):
    if not re.search(r"(?m)^\s*" + address + r":\s+[^\n]+?\s+" + pattern + r"\s*$", assembly):
        raise SystemExit(f"NOT_PROVEN: {address}: {pattern}")

def main(path):
    if not path.is_file():
        raise SystemExit("Missing exact WorldSvr binary")
    with path.open("rb") as f:
        sha = hashlib.file_digest(f, "sha256").hexdigest()
    if sha != EXPECTED_WORLD_SHA256:
        raise SystemExit(f"REFUSE_WRONG_WORLD_SHA: got {sha}")
    handler = disassemble(path, 0xA40D90, 0xA40DE0)
    require(handler, "a40dc0", r"mov\s+esi,DWORD PTR \[rax\+0xa\]")
    require(handler, "a40dca", r"mov\s+eax,DWORD PTR \[rax\+0xe\]")
    prior_update = disassemble(path, 0xA3B4F0, 0xA3B520)
    require(prior_update, "a3b502", r"mov\s+esi,0x1030")
    formatter = disassemble(path, 0x527c70, 0x527ccb)
    require(formatter, "527cab", r"mov\s+BYTE PTR \[rbp-0x6a\],0x7c")
    require(formatter, "527cba", r"call\s+410990\s+<_ZNSolsEi@plt>")
    reply = disassemble(path, 0xA3B530, 0xA3B600)
    for address, pattern in [
        ("a3b544",r"mov\s+eax,0x9f3"),
        ("a3b549",r"mov\s+edx,0x7"),
        ("a3b551",r"mov\s+DWORD PTR \[rbp-0x170\],0x7b7e2"),
        ("a3b562",r"mov\s+BYTE PTR \[rbp-0x16a\],0x1"),
        ("a3b5ca",r"mov\s+edx,0x9f3"),
        ("a3b5dd",r"mov\s+edx,0x7"),
        ("a3b5e2",r"mov\s+DWORD PTR \[rbp-0x170\],0x7b7e2"),
        ("a3b5ec",r"mov\s+BYTE PTR \[rbp-0x16a\],0x0"),
    ]:
        require(reply, address, pattern)
    print("WORLD_BINARY_SHA256=PASS")
    print("LEGACY_09F3_C2S_RAW_DWORD_OFFSETS=0x0A,0x0E")
    print("LEGACY_09F3_S2C_STATUS_PACKET=E2B70700F309[00_or_01]")
    print("LEGACY_MERIT_TEXT_FORMAT_ID=0x1030;NOT_A_PROVEN_S2C_PACKET")
    print("DIAMOND_V291_CLIENT_COMPATIBILITY=UNVERIFIED")
    print("WORLD_BINARY_MUTATED=NO")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: verify_worldsvr_merit.py /path/to/WorldSvr")
    main(pathlib.Path(sys.argv[1]))
