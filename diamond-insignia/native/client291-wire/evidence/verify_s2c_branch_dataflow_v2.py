#!/usr/bin/env python3
"""Read-only, exact-byte CABAL v291 x64 0x09F3 S2C dataflow proof.

This tool NEVER edits the client, emits an S2C response, runs game code,
or infers the meaning of unknown DWORDs. It only verifies an already
SHA-pinned PE and names the *machine-level write destinations*.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

CLIENT_SHA256="52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9"
# Exact bytes are from the owner's 15,089,000-byte v291 CabalMain.exe.
# Keep the probes deliberately small and separately check control-flow targets.
BYTES={
    0x6F851C:"80 7D 06 01",                 # success byte +6 == 1
    0x6F852A:"0F 85 D8 00 00 00",           # status !=1 -> error
    0x6F857C:"E8 DB B1 B4 FF",              # query branch selector
    0x6F8581:"85 C0",
    0x6F8583:"75 11",                       # selector !=0 -> 1/2 test
    0x6F8585:"8B 55 07",                    # DWORD from packet +7
    0x6F858F:"E8 A0 74 C8 FF",              # writes scalar member
    0x6F8596:"8B D7",
    0x6F859B:"E8 BC B1 B4 FF",
    0x6F85A5:"83 F8 01",
    0x6F85A8:"74 0F",                       # selector ==1 -> +7 load
    0x6F85AA:"E8 AD B1 B4 FF",
    0x6F85AF:"83 F8 02",
    0x6F85B2:"75 21",                       # selector !=2 -> no +7 load
    0x6F85B9:"8B 5D 07",                    # DWORD from packet +7
    0x6F85D0:"E8 03 74 C8 FF",              # map-entry update
    0x37FA34:"89 91 6C AB 00 00 C3",       # mov [rcx+AB6C],edx; ret
    0x37FA1B:"89 58 14",                    # mov [rax+14],ebx
}
CALL_TARGETS={
    0x6F857C:0x24375C,
    0x6F858F:0x37FA34,
    0x6F859B:0x24375C,
    0x6F85AA:0x24375C,
    0x6F85D0:0x37F9D8,
}
BRANCH_TARGETS={
    0x6F852A:0x6F8608,
    0x6F8583:0x6F8596,
    0x6F85A8:0x6F85B9,
    0x6F85B2:0x6F85D5,
}
EXPECTED_HANDLER_RVA=0x6F84FC

def pe_reader_and_pdata(raw):
    if len(raw)<0x200 or raw[:2]!=b"MZ":
        raise ValueError("not a valid MZ file")
    pe=struct.unpack_from("<I",raw,0x3C)[0]
    if pe>len(raw)-256 or raw[pe:pe+4]!=b"PE\0\0":
        raise ValueError("invalid PE header")
    number=struct.unpack_from("<H",raw,pe+6)[0]
    optional=pe+24
    if struct.unpack_from("<H",raw,optional)[0]!=0x20B:
        raise ValueError("not a PE32+ client")
    section_headers=optional+struct.unpack_from("<H",raw,pe+20)[0]
    sections={}
    for i in range(number):
        sec=section_headers+i*40
        if sec+40>len(raw):raise ValueError("section header out of bounds")
        name=raw[sec:sec+8].split(b"\0",1)[0].decode("ascii")
        size,base,raw_size,offset=struct.unpack_from("<IIII",raw,sec+8)
        if offset+raw_size>len(raw):
            raise ValueError("section data out of bounds")
        sections[name]=(base,raw_size,offset)
    def read(rva,size):
        if not isinstance(rva,int) or size<=0:raise ValueError("invalid RVA")
        for base,raw_size,offset in sections.values():
            if base<=rva and rva+size<=base+raw_size:
                return raw[offset+rva-base:offset+rva-base+size]
        raise ValueError("RVA out of PE raw section")
    if ".pdata" not in sections:raise ValueError("missing x64 unwind entries")
    pbase,psize,poffset=sections[".pdata"]
    if psize%12:raise ValueError("invalid PDATA table size")
    boundary=None
    for i in range(poffset,poffset+psize,12):
        begin,end,_=struct.unpack_from("<III",raw,i)
        if begin<=EXPECTED_HANDLER_RVA<end:
            boundary=(begin,end)
            break
    if not boundary or boundary[0]!=EXPECTED_HANDLER_RVA or boundary[1]<0x6F86A9:
        raise ValueError("unexpected S2C handler PDATA bounds")
    return read,boundary

def rel32_call(read,rva):
    instruction=read(rva,5)
    if instruction[0]!=0xE8:raise ValueError(f"not a call: {rva:#x}")
    return rva+5+struct.unpack_from("<i",instruction,1)[0]

def branch_destination(read,rva):
    b=read(rva,2)
    if b[0] in (0x74,0x75):return rva+2+struct.unpack("<b",b[1:2])[0]
    six=read(rva,6)
    if six[:2] in (b"\x0f\x84",b"\x0f\x85"):
        return rva+6+struct.unpack_from("<i",six,2)[0]
    raise ValueError(f"unexpected branch encoding at {rva:#x}")

def examine(read,boundary):
    for rva,hex_bytes in BYTES.items():
        expected=bytes.fromhex(hex_bytes)
        if read(rva,len(expected))!=expected:
            raise ValueError(f"client S2C code changed at RVA {rva:#x}")
    for rva,target in CALL_TARGETS.items():
        if rel32_call(read,rva)!=target:
            raise ValueError(f"client call target changed at {rva:#x}")
    for rva,target in BRANCH_TARGETS.items():
        if branch_destination(read,rva)!=target:
            raise ValueError(f"client conditional branch changed at {rva:#x}")
    return {
        "mode":"EXACT_CLIENT_READ_ONLY_STATIC_PROOF",
        "client_sha256":CLIENT_SHA256,
        "handler_rva":f"0x{EXPECTED_HANDLER_RVA:X}",
        "handler_pdata_begin":f"0x{boundary[0]:X}",
        "handler_pdata_end":f"0x{boundary[1]:X}",
        "verified_byte_probes":len(BYTES),
        "verified_calls":len(CALL_TARGETS),
        "verified_branches":len(BRANCH_TARGETS),
        "response_status_offset":6,
        "response_success_byte":1,
        "response_dword_offset":7,
        "conditional_selectors_with_dword":[0,1,2],
        "selector_0_side_effect":{
            "callees":["0x24375C","0x37FA34"],
            "write":"DWORD [RCX+0xAB6C] = response_DWORD_at_plus_7",
            "game_meaning":"UNKNOWN",
        },
        "selectors_1_2_side_effect":{
            "callees":["0x24375C","0x37F9D8"],
            "write":"DWORD [MAP_ENTRY+0x14] = response_DWORD_at_plus_7",
            "game_meaning":"UNKNOWN",
        },
        "all_other_selectors":"no +7 DWORD read on this shown success path; remaining behavior not proven",
        "legacy_7_byte_success":"insufficient for selectors 0,1,2",
        "safe_diamond_reply_serializer":"NOT_IMPLEMENTED",
        "real_game_or_client_modified":False,
    }

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("client",type=Path,help="Exact owner v291 CabalMain.exe, read-only")
    parser.add_argument("--report",type=Path,help="Write static evidence JSON (not a game patch)")
    args=parser.parse_args(argv)
    raw=args.client.read_bytes()
    got=hashlib.sha256(raw).hexdigest()
    if got!=CLIENT_SHA256:
        raise ValueError(f"STOP wrong CabalMain SHA256: {got}")
    read,boundary=pe_reader_and_pdata(raw)
    report=examine(read,boundary)
    if args.report:
        if args.report.resolve()==args.client.resolve():
            raise ValueError("refuse overwriting client")
        args.report.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("CLIENT291_MERIT_S2C_BRANCH_DATAFLOW=PASS")
    print("SELECTORS_0_1_2_READ_RESPONSE_DWORD_AT_PLUS7=PASS")
    print("SCALAR_AB6C_AND_MAP_NODE14_DESTINATIONS=PASS")
    print("DIAMOND_RESPONSE_MEANING=UNKNOWN;NO_PATCH")
    return report

if __name__=="__main__":
    main()
