#!/usr/bin/env python3
"""Read-only exact-v291 Merit UI event 0x216 -> C2S 0x0B10 proof.

This is NOT evidence of Diamond rank-up nor a WorldSvr patch.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
import zipfile
from pathlib import Path

SHA="52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9"
CLIENT_SIZE=15089000
ANCHORS={
  0x6D0FD8:"c7451016020000",    # local UI event 0x216
  0x6D0FE6:"e8e1aaa9ff",        # event lookup
  0x6D0FEF:"488d1502f70000",    # callback RVA 0x6e06f8
  0x6D0FFA:"e8c959feff",        # callback registration
  0x6E0733:"b8e2b700006689442450", # packet magic
  0x6E073D:"b8100b00006689442458", # 0x0b10 opcode
  0x6E08B1:"b80e0000006685db7407", # packet minimum 14B
  0x6E08BB:"6683c3068d041b",   # variable packet length
  0x6E08C2:"6689442452",       # write packet length
  0x6E08D7:"e86471bdff",       # call actual sender
}

class ProofError(ValueError): pass

def direct_target(rva,instr,opcode,size):
    if len(instr)!=size or instr[0]!=opcode:
        raise ProofError("NOT_RELATIVE_INSTRUCTION")
    return rva+size+struct.unpack_from("<i",instr,size-4)[0]

def audit(exe):
    if len(exe)!=CLIENT_SIZE or hashlib.sha256(exe).hexdigest()!=SHA:
        raise ProofError("EXACT_CLIENT_HASH_OR_LENGTH_MISMATCH")
    if exe[:2]!=b"MZ":
        raise ProofError("MZ_MISSING")
    nt,=struct.unpack_from("<I",exe,0x3c)
    if exe[nt:nt+4]!=b"PE\x00\x00":
        raise ProofError("PE_MISSING")
    for rva,anchor in ANCHORS.items():
        expected=bytes.fromhex(anchor)
        if exe[rva-0xc00:rva-0xc00+len(expected)]!=expected:
            raise ProofError(f"ANCHOR_CHANGED_{rva:08X}")
    for rva,opcode,size,dest in (
            (0x6D0FE6,0xe8,5,0x16BACC),
            (0x6D0FEF,0x48,7,0x6E06F8),
            (0x6D0FFA,0xe8,5,0x6B69C8),
            (0x6E08D7,0xe8,5,0x2B7A40)):
        at=rva-0xc00
        if direct_target(rva,exe[at:at+size],opcode,size)!=dest:
            raise ProofError(f"RELATIVE_TARGET_CHANGED_{rva:08X}")
    return {"status":"PASS","client_sha256":SHA,
            "ui_event_id":"0x216","callback_rva":"0x6E06F8",
            "c2s_opcode":"0x0B10","packet_min_bytes":14,
            "packet_size":"DYNAMIC; 16-bit entry accumulation; semantics unknown",
            "anchors_checked":len(ANCHORS),"diamond_rank_up_event_proven":False,
            "client_or_server_modified":False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--client-zip",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        with zipfile.ZipFile(args.client_zip) as z:
            if sorted(z.namelist())!=["CabalMain.exe","meritsystem.enc"]:
                raise ProofError("ZIP_MEMBERS_UNEXPECTED")
            result=audit(z.read("CabalMain.exe"))
    except (OSError,ValueError,zipfile.BadZipFile) as exc:
        print("V291_MERIT_0B10_UI=FAIL",exc,file=sys.stderr)
        return 2
    print(json.dumps(result,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
