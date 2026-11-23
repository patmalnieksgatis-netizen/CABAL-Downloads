#!/usr/bin/env python3
"""SHA-verified CABAL v291 Platinum 0x0B10 / grade-2 0x0BDD S2C mirror.

Read-only static proof from exact user's client. No packet creation, process
execution, WorldSvr/SQL changes, nor live transaction claims.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path

CLIENT_SHA="52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9"
CLIENT_BYTES=15089000

ANCHORS={
  0x6CFEE1:"c74510100b0000", # client S2C Platinum cmd binding
  0x6CFEF8:"488d1589b70000", # S2C handler -> RVA 0x6DB688
  0x6D0064:"c74510dd0b0000", # client S2C 0BDD cmd binding
  0x6D007B:"488d157ab00000", # S2C handler -> RVA 0x6DB0FC
  0x6DBDA6:"80790601",       # Platinum status at +6 == 1
  0x6DBDB1:"ba01000000",     # Platinum reset state slot 1
  0x6DBDDE:"b901000000",     # Platinum UI refresh index 1
  0x6DB102:"80790601",       # New 0BDD status at +6 == 1
  0x6DB10D:"ba02000000",     # New 0BDD reset state slot 2
  0x6DB13A:"b902000000",     # New 0BDD UI refresh index 2
  0x6DBDBE:"ba00d8b805",     # shared UI resource key
  0x6DB11A:"ba00d8b805",     # shared UI resource key
  0x6E0414:"b8dd0b0000",     # outgoing C2S opcode 0BDD
  0x6E0423:"8b8878010000",   # outgoing payload u32 from Merit object+0x178
  0x6E042D:"83f9ff",         # outgoing invalid selector sentinel
  0x6E043E:"41b80e000000",   # outgoing 14 byte C2S request
}
CALLS={
  0x6DBDB9:0x242888,        # original Platinum: reset Merit slot
  0x6DB115:0x242888,        # 0BDD: reset Merit slot 2
  0x6DBDCA:0x678804,        # shared client GUI lookup
  0x6DB126:0x678804,
  0x6DBDE3:0x24D128,        # shared refresh helper
  0x6DB13F:0x24D128,
  0x6DBDEB:0x24D01C,        # shared refresh helper
  0x6DB147:0x24D01C,
  0x6E044A:0x2B7A40,        # 0BDD client network send
}
HANDLERS={0x6CFEF8:0x6DB688,0x6D007B:0x6DB0FC}

class ProofError(ValueError):pass

def pe_rva(exe:bytes,rva:int,size:int)->bytes:
    # This exact-client SHA has imagebase 0x140000000 and .text RVA-to-file
    # offset = RVA-0xC00 for these sites. Never use this on other executables.
    if rva<0xC00 or rva+size-0xC00>len(exe):
        raise ProofError("RVA_OUT_OF_FILE")
    return exe[rva-0xC00:rva-0xC00+size]

def verify(exe:bytes)->dict:
    if len(exe)!=CLIENT_BYTES or hashlib.sha256(exe).hexdigest()!=CLIENT_SHA:
        raise ProofError("EXACT_CLIENT_SHA_OR_SIZE_MISMATCH")
    if exe[:2]!=b"MZ":
        raise ProofError("NOT_PE")
    nt,=struct.unpack_from("<I",exe,0x3c)
    if exe[nt:nt+4]!=b"PE\x00\x00" or struct.unpack_from("<H",exe,nt+24)[0]!=0x20b:
        raise ProofError("NOT_PE64")
    for rva,raw in ANCHORS.items():
        expected=bytes.fromhex(raw)
        if pe_rva(exe,rva,len(expected))!=expected:
            raise ProofError(f"INSTRUCTION_CHANGED_0x{rva:X}")
    for rva,dest in CALLS.items():
        instr=pe_rva(exe,rva,5)
        if instr[0]!=0xE8 or rva+5+struct.unpack_from("<i",instr,1)[0]!=dest:
            raise ProofError(f"CALL_CHANGED_0x{rva:X}")
    for rva,dest in HANDLERS.items():
        instr=pe_rva(exe,rva,7)
        if instr[:3]!=bytes.fromhex("488d15") or rva+7+struct.unpack_from("<i",instr,3)[0]!=dest:
            raise ProofError(f"HANDLER_BINDING_CHANGED_0x{rva:X}")
    return {
        "status":"PASS","mode":"EXACT_CLIENT_READ_ONLY_STATIC",
        "client_sha256":CLIENT_SHA,
        "instruction_anchors_checked":len(ANCHORS),
        "direct_calls_checked":len(CALLS),
        "s2c_bindings_checked":len(HANDLERS),
        "platinum":{"c2s_opcode":"0x0B10","s2c_handler_rva":"0x6DBDA0",
                    "success_status_at_offset":6,"merit_state_slot":1},
        "new_candidate":{"c2s_opcode":"0x0BDD","s2c_handler_rva":"0x6DB0FC",
                         "success_status_at_offset":6,"merit_state_slot":2,
                         "outgoing_u32_source":"Merit object +0x178",
                         "outgoing_bytes":14},
        "shared_success_helpers":["0x242888","0x678804","0x24D128","0x24D01C"],
        "semantic_conclusion":"Strong grade-2 promotion candidate, not confirmed resource debit or gameplay operation",
        "real_game_working":False,"live_world_or_sql_changed":False,
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--client-zip",required=True,type=Path)
    args=p.parse_args()
    with zipfile.ZipFile(args.client_zip) as z:
        if sorted(z.namelist())!=["CabalMain.exe","meritsystem.enc"] or z.testzip():
            raise ProofError("INVALID_CLIENT_ARCHIVE")
        report=verify(z.read("CabalMain.exe"))
    print(json.dumps(report,indent=2))
if __name__=="__main__":
    main()
