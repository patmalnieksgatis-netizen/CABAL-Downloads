#!/usr/bin/env python3
"""CABAL v291 read-only exact client/WorldSvr Merit static registration audit.

Only checks known UI event -> C2S sender and WorldSvr RIP-relative user
procedure registry references. Zero matches != proof of no runtime/indirect
handler; newer opcode != Diamond rank-up proof.
"""
import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path

CLIENT_SHA = "52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9"
WORLD_SHA = "caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3"
WORLD_MAP_BASE = 0x235F8C0
# ui_event: (event_instruction_rva, callback_lea_rva, callback_rva,
#            C2S_opcode_instruction_rva, opcode)
CLIENT = {
    0x216: (0x6D0FD8,0x6D0FEF,0x6E06F8,0x6E073D,0x0B10),
    0x21C: (0x6D10AF,0x6D10C6,0x6DFD08,0x6DFD54,0x0BDA),
    0x21D: (0x6D10DA,0x6D10F1,0x6DFFE8,0x6E0032,0x0BDB),
    0x21E: (0x6D1105,0x6D111C,0x6E03EC,0x6E0414,0x0BDD),
    0x21F: (0x6D1130,0x6D1147,0x6DFF60,0x6DFF88,0x0BDF),
    0x220: (0x6D115B,0x6D1172,0x6E0464,0x6E04B1,0x0BE0),
}
# Server-to-client command -> (registration instruction, callback LEA, handler RVA)
# The client registers all six via 0x16BB3C and 0x2879E4.
S2C = {
    0x0BDA: (0x6CFFE3,0x6CFFFA,0x6DA920),
    0x0BDB: (0x6D000E,0x6D0025,0x6DAED8),
    0x0BDC: (0x6D0039,0x6D0050,0x6DB154),
    0x0BDD: (0x6D0064,0x6D007B,0x6DB0FC),
    0x0BDF: (0x6D008F,0x6D00A6,0x6DAD14),
    0x0BE0: (0x6D00BA,0x6D00D1,0x6DB3B4),
}

# (RIP-relative opcode prefix, full instruction length)
PATTERNS = (
    (bytes.fromhex("48833d"),8), # cmp qword [rip+disp32], imm8
    (bytes.fromhex("488b1d"),7), # mov rbx, [rip+disp32]
    (bytes.fromhex("48891d"),7), # mov [rip+disp32], rbx
    (bytes.fromhex("488d0d"),7),
    (bytes.fromhex("488d15"),7),
    (bytes.fromhex("488d05"),7),
    (bytes.fromhex("4c8b05"),7),
    (bytes.fromhex("4c8b0d"),7),
    (bytes.fromhex("4c8d05"),7),
    (bytes.fromhex("4c8d0d"),7),
    (bytes.fromhex("4c891d"),7),
)
class ProofError(ValueError): pass

def checked_sha(data,expected,label):
    if hashlib.sha256(data).hexdigest()!=expected:
        raise ProofError(label+"_SHA_MISMATCH")

def elf_text(data):
    if data[:4]!=b"\x7fELF" or data[4:6]!=b"\x02\x01":
        raise ProofError("NOT_ELF64_LE")
    shoff,=struct.unpack_from("<Q",data,0x28)
    entsize,num,names_idx=struct.unpack_from("<HHH",data,0x3a)
    if entsize<64 or num<1 or names_idx>=num or shoff+entsize*num>len(data):
        raise ProofError("ELF_SECTION_TABLE_INVALID")
    def entry(idx):
        return struct.unpack_from("<IIQQQQIIQQ",data,shoff+idx*entsize)
    n=entry(names_idx); name_off,name_len=n[4],n[5]
    if name_off+name_len>len(data):raise ProofError("ELF_NAMES_TRUNCATED")
    names=data[name_off:name_off+name_len]
    for i in range(num):
        row=entry(i); npos=row[0]
        if npos>=len(names):continue
        end=names.find(b"\0",npos)
        if end>=0 and names[npos:end]==b".text":
            va,off,size=row[3],row[4],row[5]
            if off+size>len(data):raise ProofError("ELF_TEXT_TRUNCATED")
            return va,data[off:off+size]
    raise ProofError("ELF_TEXT_NOT_FOUND")

def registry_hits(code,base,slot):
    hits=[]
    for prefix,length in PATTERNS:
        at=code.find(prefix)
        while at!=-1:
            if at+length<=len(code):
                disp,=struct.unpack_from("<i",code,at+3)
                if base+at+length+disp==slot:
                    hits.append({"rva":f"0x{base+at:X}",
                                 "bytes":code[at:at+length].hex()})
            at=code.find(prefix,at+1)
    return sorted(hits,key=lambda x:int(x["rva"],16))

def pe_reader(exe):
    if exe[:2]!=b"MZ":raise ProofError("NOT_MZ")
    nt,=struct.unpack_from("<I",exe,0x3c)
    if exe[nt:nt+4]!=b"PE\0\0" or struct.unpack_from("<H",exe,nt+24)[0]!=0x20b:
        raise ProofError("NOT_PE64")
    count,=struct.unpack_from("<H",exe,nt+6)
    opt,=struct.unpack_from("<H",exe,nt+20)
    for i in range(count):
        pos=nt+24+opt+i*40
        if exe[pos:pos+8].split(b"\0")[0]!=b".text":continue
        _vsize,va,size,off=struct.unpack_from("<IIII",exe,pos+8)
        def read(rva,n):
            ix=off+rva-va
            if not(va<=rva and rva+n<=va+size and ix+n<=len(exe)):
                raise ProofError("PE_RVA_OUT_OF_BOUNDS")
            return exe[ix:ix+n]
        return read
    raise ProofError("PE_TEXT_NOT_FOUND")

def verify_client(exe):
    checked_sha(exe,CLIENT_SHA,"CLIENT")
    read=pe_reader(exe)
    for ui,(event,lea,callback,at,opcode) in CLIENT.items():
        if read(event,3)!=bytes.fromhex("c74510") or int.from_bytes(read(event+3,4),"little")!=ui:
            raise ProofError("EVENT_ANCHOR_"+hex(ui))
        raw=read(lea,7)
        if raw[:3]!=bytes.fromhex("488d15") or lea+7+struct.unpack_from("<i",raw,3)[0]!=callback:
            raise ProofError("CALLBACK_ANCHOR_"+hex(ui))
        if opcode==0x0BDA:
            data=read(at,8)
            if data[:4]!=bytes.fromhex("c7442458") or int.from_bytes(data[4:],"little")!=opcode:
                raise ProofError("OPCODE_ANCHOR_"+hex(ui))
        elif read(at,5)!=b"\xb8"+struct.pack("<I",opcode):
            raise ProofError("OPCODE_ANCHOR_"+hex(ui))

    for opcode,(event_rva,lea_rva,callback_rva) in S2C.items():
        if read(event_rva,3)!=bytes.fromhex("c74510") or int.from_bytes(read(event_rva+3,4),"little")!=opcode:
            raise ProofError("S2C_REGISTRATION_ANCHOR_"+hex(opcode))
        lea=read(lea_rva,7)
        if lea[:3]!=bytes.fromhex("488d15") or lea_rva+7+struct.unpack_from("<i",lea,3)[0]!=callback_rva:
            raise ProofError("S2C_HANDLER_ANCHOR_"+hex(opcode))
        bind=read(lea_rva+11,5)
        if bind[0]!=0xe8 or lea_rva+16+struct.unpack_from("<i",bind,1)[0]!=0x2879E4:
            raise ProofError("S2C_BINDER_ANCHOR_"+hex(opcode))

def audit(client,world):
    verify_client(client)
    checked_sha(world,WORLD_SHA,"WORLD")
    text_base,code=elf_text(world)
    rows=[]
    for ui,(_a,_b,callback,_c,opcode) in CLIENT.items():
        slot=WORLD_MAP_BASE+opcode*8
        hits=registry_hits(code,text_base,slot)
        rows.append({"ui_event":f"0x{ui:X}","callback_rva":f"0x{callback:X}",
                     "c2s_opcode":f"0x{opcode:04X}","world_slot":f"0x{slot:X}",
                     "static_slot_references":hits})
    if not rows[0]["static_slot_references"]:
        raise ProofError("B10_POSITIVE_CONTROL_NOT_FOUND")
    if any(row["static_slot_references"] for row in rows[1:]):
        raise ProofError("NEW_STATIC_HANDLER_FOUND_REVIEW_REQUIRED")
    return {"status":"PASS","mode":"SHA_PINNED_READ_ONLY_STATIC",
            "client_sha256":CLIENT_SHA,"world_sha256":WORLD_SHA,
            "world_registry_base":f"0x{WORLD_MAP_BASE:X}",
            "claims":"Five client Merit-adjacent C2S opcodes have no direct static RIP-relative registry reference in this WorldSvr; indirect/dynamic registration and Diamond semantics remain unproven.",
            "events":rows,
            "client_s2c_handlers":[
                {"s2c_opcode":f"0x{opcode:04X}","handler_rva":f"0x{parts[2]:X}",
                 "paired_c2s_ui_event": next(
                     (f"0x{ui:X}" for ui,entry in CLIENT.items() if entry[4]==opcode),None)}
                for opcode,parts in S2C.items()
            ],
            "game_modified":False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--client-zip",type=Path,required=True)
    p.add_argument("--world",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        with zipfile.ZipFile(args.client_zip) as archive:
            if sorted(archive.namelist())!=["CabalMain.exe","meritsystem.enc"]:
                raise ProofError("UNEXPECTED_ARCHIVE_MEMBERS")
            exe=archive.read("CabalMain.exe")
        result=audit(exe,args.world.read_bytes())
    except (ProofError,OSError,zipfile.BadZipFile,struct.error) as exc:
        print("DIAMOND_UI_WORLDSVR_STATIC_GAP=FAIL",exc)
        return 2
    print(json.dumps(result,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
