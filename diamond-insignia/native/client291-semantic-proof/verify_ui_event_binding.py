#!/usr/bin/env python3
"""Exact CABAL v291 x64 local-UI event registration map; read-only.

Distinguishes callback association from next adjacent event ID.
Only claims event->callback binding in the pinned client, NOT a Diamond UI action.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

SHA="52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9"
RVA_START=0x6f0c00
RVA_END=0x6f1400
EVENT_CONSTRUCTOR=0x16bacc
CALLBACK_BINDER=0x6b69c8
MERIT_CALLBACK=0x6ff14c
EXPECTED={
    0x1a0:0x6ffa8c,0x1a1:0x6ff14c,0x1a2:0x6fcd44,
    0x1a3:0x6fcd00,0x1a4:0x6fcf44,
}

def i32(b,offset):
    return struct.unpack_from("<i",b,offset)[0]

def call_target(raw,start,position):
    if raw[position]!=0xe8:
        raise ValueError("missing near CALL")
    return start+position+5+i32(raw,position+1)

def parse_registrations(raw,begin_rva):
    """Raw contiguous .text window, or a test-generated synthetic window."""
    found={}
    for p in range(len(raw)-42):
        if raw[p:p+3]!=b"\xc7\x45\x10":
            continue
        event=struct.unpack_from("<I",raw,p+3)[0]
        if not 0x180<=event<=0x1af:
            continue
        if (raw[p+7:p+14]!=b"\x48\x8d\x55\xb0\x48\x8b\xcb"
            or raw[p+19:p+23]!=b"\x48\x8b\x4d\xb0"
            or raw[p+23:p+26]!=b"\x48\x8d\x15"
            or raw[p+30:p+34]!=b"\x48\x83\xc1\x18"):
            continue
        if (call_target(raw,begin_rva,p+14)!=EVENT_CONSTRUCTOR
            or call_target(raw,begin_rva,p+34)!=CALLBACK_BINDER):
            continue
        handler=begin_rva+p+30+i32(raw,p+26)
        if event in found: raise ValueError("duplicate event mapping")
        found[event]={"event_id":hex(event),"set_rva":hex(begin_rva+p),
                      "handler_lea_rva":hex(begin_rva+p+23),
                      "handler_rva":hex(handler)}
    return found

def read_pe_rva(exe,begin,length):
    if exe[:2]!=b"MZ": raise ValueError("wrong MZ")
    pe=struct.unpack_from("<I",exe,0x3c)[0]
    if exe[pe:pe+4]!=b"PE\0\0": raise ValueError("wrong PE")
    if struct.unpack_from("<H",exe,pe+24)[0]!=0x20b:
        raise ValueError("not PE32+")
    count=struct.unpack_from("<H",exe,pe+6)[0]
    sections=pe+24+struct.unpack_from("<H",exe,pe+20)[0]
    for n in range(count):
        off=sections+n*40
        virtual=struct.unpack_from("<I",exe,off+12)[0]
        raw_size,raw_ptr=struct.unpack_from("<II",exe,off+16)
        if virtual<=begin and begin+length<=virtual+raw_size:
            pos=raw_ptr+begin-virtual
            return exe[pos:pos+length]
    raise ValueError("RVA outside raw section")

def inspect(exe):
    if len(exe)!=15089000 or hashlib.sha256(exe).hexdigest()!=SHA:
        raise ValueError("unexpected client identity")
    raw=read_pe_rva(exe,RVA_START,RVA_END-RVA_START)
    maps=parse_registrations(raw,RVA_START)
    for event,handler in EXPECTED.items():
        if event not in maps or int(maps[event]["handler_rva"],16)!=handler:
            raise ValueError("event/callback mismatch at "+hex(event))
    merit=read_pe_rva(exe,MERIT_CALLBACK,0x66)
    if (merit[0x0b:0x10]!=bytes.fromhex("b8f3090000")
        or merit[0x15:0x1d]!=bytes.fromhex("c7442420e2b71200")
        or merit[0x4f:0x54]!=bytes.fromhex("e8a088bbff")):
        raise ValueError("Merit C2S sender byte anchors changed")
    return {"mode":"STATIC_EXACT_CLIENT_UI_EVENT_BINDINGS",
            "client_sha256":SHA,
            "ui_event_0x1a1_handler":hex(MERIT_CALLBACK),
            "merit_c2s_opcode":"0x09f3","merit_c2s_bytes":18,
            "previous_0x1a2_attribution":"CORRECTED_OFF_BY_ONE",
            "bindings":[maps[k] for k in sorted(EXPECTED)],
            "diamond_button_proven":False,"runtime_event_fired_proven":False,
            "game_files_modified":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("client",type=Path)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    if args.out and args.out.exists():ap.error("refuse overwrite")
    result=inspect(args.client.read_bytes())
    rendered=json.dumps(result,indent=2)+"\n"
    if args.out:args.out.write_text(rendered,encoding="utf-8")
    else:print(rendered,end="")
if __name__=="__main__":main()
