#!/usr/bin/env python3
"""Verified static 0BDA vs original Platinum 0B10 grade-up client pairing.

This is STRONG client-side grade-up counterpart evidence, NOT direct proof
of exact Diamond resource debit, server opcode implementation or gameplay.
Hash-pinned read-only executable inspection.
"""
from __future__ import annotations
import argparse,hashlib,json,struct,zipfile
from pathlib import Path

CLIENT_SHA="52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9"
CLIENT_SIZE=15089000
ANCHORS={
    0x6D0FD8:"c7451016020000", # original local UI 0x216
    0x6D10AF:"c745101c020000", # newer local UI 0x21C
    0x6CFEE1:"c74510100b0000", # original S2C grade-up 0B10 registration
    0x6CFFE3:"c74510da0b0000", # new S2C 0BDA registration
    0x6E073D:"b8100b0000",     # original outgoing C2S 0B10
    0x6DFD54:"c7442458da0b0000", # new outgoing C2S 0BDA
    0x6E077C:"448b8988ab0000", # same selected GUI Merit array source
    0x6DFD8E:"448b8988ab0000",
    0x6E08B1:"b80e000000",     # base packet length 14
    0x6DFD4C:"be0e000000",
    0x6DB6B9:"807b0600",       # original status!=0 for S2C 0B10
    0x6DA94C:"807b0600",       # new status!=0 for S2C 0BDA
    0x6DB6F5:"448d6e01",       # original success Merit state group=1
    0x6DAA34:"be02000000",     # new success Merit state group=2
}
LEAS={
    0x6D0FEF:0x6E06F8,0x6D10C6:0x6DFD08,
    0x6CFEF8:0x6DB688,0x6CFFFA:0x6DA920,
}
CALLS={
    0x6E0794:0x244D3C,0x6DFDA6:0x244D3C,
    0x6E08D7:0x2B7A40,0x6DFEED:0x2B7A40,
    0x6DB7A1:0x380BDC,0x6DAA2F:0x380BDC,
    0x6DB7B0:0x37FA2C,0x6DAA42:0x37FA2C,
    0x6DB808:0x365E44,0x6DAA95:0x365E44,
    0x6DB823:0x24D128,0x6DAAAF:0x24D128,
    0x6DB82B:0x24D01C,0x6DAAB7:0x24D01C,
}
class ProofError(ValueError):pass
def read(exe,rva,size):
    if rva<0xC00 or rva+size-0xC00>len(exe):raise ProofError("RVA_OOB")
    return exe[rva-0xC00:rva-0xC00+size]
def verify(exe):
    if len(exe)!=CLIENT_SIZE or hashlib.sha256(exe).hexdigest()!=CLIENT_SHA:
        raise ProofError("WRONG_EXACT_CLIENT")
    if exe[:2]!=b"MZ":raise ProofError("NOT_MZ")
    nt,=struct.unpack_from("<I",exe,0x3c)
    if exe[nt:nt+4]!=b"PE\x00\x00" or struct.unpack_from("<H",exe,nt+24)[0]!=0x20b:
        raise ProofError("NOT_PE64")
    for rva,raw in ANCHORS.items():
        if read(exe,rva,len(bytes.fromhex(raw)))!=bytes.fromhex(raw):
            raise ProofError(f"ANCHOR_CHANGED_{rva:X}")
    for rva,target in LEAS.items():
        code=read(exe,rva,7)
        if code[:3]!=bytes.fromhex("488d15") or rva+7+struct.unpack_from("<i",code,3)[0]!=target:
            raise ProofError(f"LEA_CHANGED_{rva:X}")
    for rva,target in CALLS.items():
        code=read(exe,rva,5)
        if code[0]!=0xE8 or rva+5+struct.unpack_from("<i",code,1)[0]!=target:
            raise ProofError(f"CALL_CHANGED_{rva:X}")
    return {
        "mode":"READ_ONLY_EXACT_CLIENT",
        "status":"PASS",
        "client_sha256":CLIENT_SHA,
        "checked_anchor_count":len(ANCHORS),
        "checked_lea_bindings":len(LEAS),
        "checked_shared_calls":len(CALLS),
        "verified_original":{"local_ui_event":"0x216","c2s":"0x0B10",
                             "s2c_handler_rva":"0x6DB688","merit_state_group":1},
        "strong_new_gradeup_candidate":{"local_ui_event":"0x21C","c2s":"0x0BDA",
                             "s2c_handler_rva":"0x6DA920","merit_state_group":2},
        "client_sends_both_as_variable_length_counted_list":True,
        "shared_merit_list_builder":"0x244D3C",
        "shared_client_success_helpers":["0x380BDC","0x37FA2C","0x365E44",
                                         "0x24D128","0x24D01C"],
        "incorrect_old_0bdd_assumption_retracted":True,
        "0bda_real_diamond_gradeup_proven":False,
        "real_game_backend_proven":False,
        "live_files_modified":False,
    }
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-zip",required=True,type=Path)
    args=parser.parse_args()
    with zipfile.ZipFile(args.client_zip) as z:
        if sorted(z.namelist())!=["CabalMain.exe","meritsystem.enc"] or z.testzip():
            raise ProofError("UNEXPECTED_CLIENT_ARCHIVE")
        report=verify(z.read("CabalMain.exe"))
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()
