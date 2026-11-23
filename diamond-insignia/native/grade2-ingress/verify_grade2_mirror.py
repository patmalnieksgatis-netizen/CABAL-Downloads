#!/usr/bin/env python3
"""Corrected SHA-pinned v291 Merit S2C/C2S pairing: 0B13 <-> 0BDD.

Earlier hypothesis 0B10 <-> 0BDD was WRONG: the success handler 0x6DBDA0
belongs to the client 0B13 slot-open-cancel event, not 0B10 grade-up.
This read-only proof prevents misrouting 0BDD to Diamond rank-up.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path

CLIENT_SHA="52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9"
CLIENT_SIZE=15089000
ANCHORS={
    0x6CFEE1:"c74510100b0000", # actual Platinum GRADE-UP S2C 0B10
    0x6CFEF8:"488d1589b70000", # 0B10 handler -> 0x6DB688 (NOT 0x6DBDA0!)
    0x6CFF62:"c74510130b0000", # Platinum SLOT-OPEN-CANCEL S2C 0B13
    0x6CFF79:"488d1520be0000", # 0B13 handler -> 0x6DBDA0
    0x6D0064:"c74510dd0b0000", # new S2C 0BDD
    0x6D007B:"488d157ab00000", # 0BDD handler -> 0x6DB0FC
    0x6DBDA6:"80790601",       # 0B13 status success
    0x6DBDB1:"ba01000000",     # 0B13 Merit state slot 1
    0x6DBDDE:"b901000000",     # 0B13 UI index 1
    0x6DB102:"80790601",       # 0BDD status success
    0x6DB10D:"ba02000000",     # 0BDD Merit state slot 2
    0x6DB13A:"b902000000",     # 0BDD UI index 2
    0x6DBDBE:"ba00d8b805",     # same GUI lookup key
    0x6DB11A:"ba00d8b805",
    0x6E0DEB:"b8130b0000",     # C2S 0B13
    0x6E0DFA:"8b8874010000",   # C2S 0B13 raw selector at +0x174
    0x6E0E04:"83f9ff",         # both reject FFFFFFFF selector
    0x6E0E15:"41b80e000000",   # C2S 0B13 = 14 B
    0x6E0414:"b8dd0b0000",     # C2S 0BDD
    0x6E0423:"8b8878010000",   # C2S 0BDD raw selector at +0x178
    0x6E042D:"83f9ff",
    0x6E043E:"41b80e000000",
}
CALLS={
    0x6DBDB9:0x242888,0x6DB115:0x242888,
    0x6DBDCA:0x678804,0x6DB126:0x678804,
    0x6DBDE3:0x24D128,0x6DB13F:0x24D128,
    0x6DBDEB:0x24D01C,0x6DB147:0x24D01C,
    0x6E0E21:0x2B7A40,0x6E044A:0x2B7A40,
    0x6CFF84:0x2879E4,0x6D0086:0x2879E4,
}
S2C_BINDINGS={
    0x6CFEF8:0x6DB688, # original Platinum grade-up, distinct!
    0x6CFF79:0x6DBDA0, # original Platinum slot-open cancel
    0x6D007B:0x6DB0FC, # new slot-open cancel candidate
}
class ProofError(ValueError):pass
def read(exe:bytes,rva:int,size:int)->bytes:
    if rva<0xC00 or rva+size-0xC00>len(exe):
        raise ProofError("RVA_OUT_OF_BOUNDS")
    return exe[rva-0xC00:rva-0xC00+size]
def verify(exe:bytes)->dict:
    if len(exe)!=CLIENT_SIZE or hashlib.sha256(exe).hexdigest()!=CLIENT_SHA:
        raise ProofError("EXACT_CLIENT_SHA_OR_SIZE_MISMATCH")
    if exe[:2]!=b"MZ":raise ProofError("NOT_MZ")
    nt,=struct.unpack_from("<I",exe,0x3c)
    if exe[nt:nt+4]!=b"PE\x00\x00" or struct.unpack_from("<H",exe,nt+24)[0]!=0x20b:
        raise ProofError("NOT_PE64")
    for rva,raw in ANCHORS.items():
        expected=bytes.fromhex(raw)
        if read(exe,rva,len(expected))!=expected:
            raise ProofError(f"ANCHOR_CHANGED_{rva:X}")
    for rva,dest in CALLS.items():
        raw=read(exe,rva,5)
        if raw[0]!=0xE8 or rva+5+struct.unpack_from("<i",raw,1)[0]!=dest:
            raise ProofError(f"CALL_CHANGED_{rva:X}")
    for rva,dest in S2C_BINDINGS.items():
        raw=read(exe,rva,7)
        if raw[:3]!=bytes.fromhex("488d15") or rva+7+struct.unpack_from("<i",raw,3)[0]!=dest:
            raise ProofError(f"S2C_BINDING_CHANGED_{rva:X}")
    return {
        "status":"PASS","mode":"EXACT_CLIENT_READ_ONLY_CORRECTED",
        "client_sha256":CLIENT_SHA,
        "instruction_anchors_checked":len(ANCHORS),
        "call_targets_checked":len(CALLS),
        "s2c_handler_bindings_checked":len(S2C_BINDINGS),
        "actual_platinum_gradeup":{"opcode":"0x0B10","s2c_handler_rva":"0x6DB688"},
        "verified_platinum_slot_cancel":{"opcode":"0x0B13",
            "c2s_sender_rva":"0x6E0DC8","s2c_handler_rva":"0x6DBDA0",
            "merit_state_slot":1,"selector_source_offset":"0x174","c2s_bytes":14},
        "new_slot_cancel_counterpart":{"opcode":"0x0BDD",
            "c2s_sender_rva":"0x6E03EC","s2c_handler_rva":"0x6DB0FC",
            "merit_state_slot":2,"selector_source_offset":"0x178","c2s_bytes":14},
        "same_success_ui_helpers":["0x242888","0x678804","0x24D128","0x24D01C"],
        "conclusion":"0BDD strongly matches grade-2 slot-open cancel, NOT proven rank-up",
        "misidentified_platinum_handler_corrected":True,
        "rankup_route_permitted":False,"live_world_sql_modified":False,
    }
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--client-zip",required=True,type=Path)
    args=p.parse_args()
    with zipfile.ZipFile(args.client_zip) as z:
        if sorted(z.namelist())!=["CabalMain.exe","meritsystem.enc"] or z.testzip():
            raise ProofError("BAD_EXACT_CLIENT_ARCHIVE")
        print(json.dumps(verify(z.read("CabalMain.exe")),indent=2))
if __name__=="__main__":main()
