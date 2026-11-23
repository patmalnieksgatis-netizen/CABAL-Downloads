#!/usr/bin/env python3
"""CABAL v291 Merit-adjacent 0BDA/0BDB/0BDD/0BDF/0BE0 C2S shape audit.

SOURCE: SHA-pinned owner's exact CabalMain.exe; real sender instruction anchors.
PURPOSE: offline read-only packet classification and integrity checking.
NEVER treat a matching shape as a verified Diamond purchase or send packets.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path

EXACT_SHA="52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9"
MAGIC=b"\xE2\xB7"
# All offsets are PE RVAs, NOT file offsets, and use the exact owner x64 binary.
ANCHORS={
  0x0BDA:{
    0x6DFD43:"48c7442450e2b70e00",0x6DFD54:"c7442458da0b0000",
    0x6DFEC7:"66895c245a",0x6DFED1:"6683c306",
    0x6DFED5:"8d341b",0x6DFED8:"6689742452",
    0x6DFEED:"e84e7bbdff"},
  0x0BDB:{
    0x6E0022:"48c74580e2b71400",0x6E0032:"b8db0b0000",
    0x6E004F:"89458a",0x6E0212:"6689458e",0x6E02FE:"6644897d90",
    0x6E0306:"84db",0x6E030D:"6683c009",
    0x6E0311:"8d3400",0x6E0314:"66897582",
    0x6E0327:"e81477bdff"},
  0x0BDD:{
    0x6E040A:"b8e2b70000",0x6E0414:"b8dd0b0000",
    0x6E0423:"8b8878010000",0x6E0429:"894c242a",
    0x6E042D:"83f9ff",0x6E043E:"41b80e000000",
    0x6E044A:"e8f175bdff"},
  0x0BDF:{
    0x6DFF88:"b8df0b0000",0x6DFF9E:"0fb68898ab0000",
    0x6DFFA5:"884c242a",0x6DFFA9:"3b88a4ab0000",
    0x6DFFB1:"84c9",0x6DFFC1:"41b80b000000",
    0x6DFFCD:"e86e7abdff"},
  0x0BE0:{
    0x6E049F:"48c7442450e2b71200",0x6E04B1:"b8e00b0000",
    0x6E04BB:"44897c245a",0x6E04C0:"6644897c245e",
    0x6E0652:"66895c245e",0x6E065F:"8944245a",
    0x6E0663:"6685db",0x6E0668:"6683c308",
    0x6E066C:"448d341b",0x6E0670:"664489742452",
    0x6E0686:"e8b573bdff"},
}
SEND_TARGET=0x2B7A40
SEND_RVAS={0x0BDA:0x6DFEED,0x0BDB:0x6E0327,
           0x0BDD:0x6E044A,0x0BDF:0x6DFFCD,0x0BE0:0x6E0686}

class EvidenceError(ValueError):
    pass

def read_rva(exe:bytes,rva:int,n:int)->bytes:
    if exe[:2]!=b"MZ":
        raise EvidenceError("NOT_PE")
    nt,=struct.unpack_from("<I",exe,0x3c)
    if exe[nt:nt+4]!=b"PE\x00\x00" or struct.unpack_from("<H",exe,nt+24)[0]!=0x20b:
        raise EvidenceError("NOT_PE64")
    count,=struct.unpack_from("<H",exe,nt+6)
    opt,=struct.unpack_from("<H",exe,nt+20)
    table=nt+24+opt
    for i in range(count):
        section=table+i*40
        _virtual_size,base,size,file_offset=struct.unpack_from("<IIII",exe,section+8)
        if base<=rva and rva+n<=base+size:
            pos=file_offset+rva-base
            if pos+n<=len(exe):
                return exe[pos:pos+n]
    raise EvidenceError("UNMAPPED_RVA")

def verify_exact_client(exe:bytes)->dict:
    if len(exe)!=15089000 or hashlib.sha256(exe).hexdigest()!=EXACT_SHA:
        raise EvidenceError("EXACT_CLIENT_SHA_OR_SIZE_MISMATCH")
    checked=0
    for opcode,anchors in ANCHORS.items():
        for rva,hexbytes in anchors.items():
            expected=bytes.fromhex(hexbytes)
            if read_rva(exe,rva,len(expected))!=expected:
                raise EvidenceError(f"CLIENT_ANCHOR_CHANGED_{opcode:04X}_{rva:08X}")
            checked+=1
        at=SEND_RVAS[opcode]
        call=read_rva(exe,at,5)
        if call[0]!=0xe8 or at+5+struct.unpack_from("<i",call,1)[0]!=SEND_TARGET:
            raise EvidenceError(f"SEND_TARGET_CHANGED_{opcode:04X}")
    return {"status":"PASS","exact_client_sha256":EXACT_SHA,
            "sender_opcodes":[f"0x{v:04X}" for v in ANCHORS],
            "instruction_anchors_checked":checked,
            "sender_calls_checked":len(SEND_RVAS),
            "diamond_specific_meaning_proven":False}

def u16(packet,at):
    return int.from_bytes(packet[at:at+2],"little")
def u32(packet,at):
    return int.from_bytes(packet[at:at+4],"little")

def classify_c2s(packet:bytes)->dict:
    result={"packet_bytes":len(packet),"verified_sender_shape":False,
            "diamond_action_proven":False}
    if len(packet)<10 or packet[:2]!=MAGIC:
        return {**result,"reason":"missing_or_invalid_header"}
    declared=u16(packet,2)
    opcode=u16(packet,8)
    result.update({"declared_bytes":declared,"opcode":f"0x{opcode:04X}",
                   "transport_dword_raw":u32(packet,4)})
    if declared!=len(packet):
        return {**result,"reason":"header_size_mismatch"}
    if opcode not in ANCHORS:
        return {**result,"reason":"not_this_merit_family"}
    if opcode==0x0BDD:
        if len(packet)!=14:
            return {**result,"reason":"expected_14_bytes"}
        value=u32(packet,10)
        if value==0xFFFFFFFF:
            return {**result,"reason":"sender_does_not_send_sentinel"}
        fields={"field_10_u32_raw":value}
    elif opcode==0x0BDF:
        if len(packet)!=11:
            return {**result,"reason":"expected_11_bytes"}
        if packet[10]==0:
            return {**result,"reason":"sender_requires_nonzero_byte"}
        fields={"field_10_u8_raw":packet[10],
                "upper_bound_check":"requires_client_state_not_present_in_trace"}
    elif opcode==0x0BDA:
        if len(packet)<14:
            return {**result,"reason":"short_base"}
        count=u16(packet,10)
        expected=max(14,12+2*count)
        if len(packet)!=expected:
            return {**result,"reason":"entry_count_size_mismatch"}
        fields={"count_u16":count,
                "entries_u16_raw":[u16(packet,12+2*i) for i in range(count)]}
    elif opcode==0x0BDB:
        if len(packet)<20:
            return {**result,"reason":"short_base"}
        first,second=u16(packet,14),u16(packet,16)
        if first+second>255:  # Client increments 8-bit BL for both lists.
            return {**result,"reason":"ambiguous_8bit_total_count"}
        expected=max(20,18+2*(first+second))
        if len(packet)!=expected:
            return {**result,"reason":"entry_count_size_mismatch"}
        fields={"field_10_u32_raw":u32(packet,10),
                "first_count_u16":first,"second_count_u16":second,
                "first_entries_u16_raw":[u16(packet,18+2*i) for i in range(first)],
                "second_entries_u16_raw":[u16(packet,18+2*(first+i)) for i in range(second)]}
    else:
        if len(packet)<18:
            return {**result,"reason":"short_base"}
        count=u16(packet,14)
        expected=max(18,16+2*count)
        if len(packet)!=expected:
            return {**result,"reason":"entry_count_size_mismatch"}
        fields={"field_10_u32_raw":u32(packet,10),"count_u16":count,
                "entries_u16_raw":[u16(packet,16+2*i) for i in range(count)]}
    return {**result,"verified_sender_shape":True,
            "reason":"client_sender_shape_only",
            "raw_fields":fields}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--client-zip",type=Path)
    p.add_argument("--packet-hex",help="one offline C2S frame as hex; no traffic is sent")
    args=p.parse_args(argv)
    if not args.client_zip and args.packet_hex is None:
        p.error("specify --client-zip or --packet-hex")
    if args.client_zip:
        with zipfile.ZipFile(args.client_zip) as z:
            if sorted(z.namelist())!=["CabalMain.exe","meritsystem.enc"] or z.testzip():
                raise EvidenceError("UNEXPECTED_OR_CORRUPT_ARCHIVE")
            print(json.dumps(verify_exact_client(z.read("CabalMain.exe")),indent=2))
    if args.packet_hex is not None:
        packet=bytes.fromhex(args.packet_hex.replace(":"," "))
        print(json.dumps(classify_c2s(packet),indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
