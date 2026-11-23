#!/usr/bin/env python3
"""CABAL exact WorldSvr 0B10 list -> 48-byte indexed inventory record proof.

Static, SHA-pinned original server ELF. The 0BDA counterpart remains
unregistered in this build and its grade-up list semantics unproven.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path

SHA="caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3"
ELF_BYTES=10596184
ANCHORS={
    0xA40FD2:"410fb7460a",       # count = u16 [request+10]
    0xA40FD7:"410fb75602",       # declared size = u16 [request+2]
    0xA40FDC:"488d44000c",       # expected = 12 + count*2
    0xA40FE1:"4839c2",           # length compare
    0xA41067:"410fb754560c",     # u16 item from +12 + 2*i
    0xA4137D:"6681fe0902",       # index <= 0x209
    0xA4135E:"498d8d08650000",   # server-owned [r13+0x6508]
    0xA41390:"8b4804",           # indexed record field +4
    0xA41397:"8b4008",           # indexed record field +8
    0xA4139A:"25ff0f0006",       # stored item field mask 0x6000fff
    0xA413AB:"498d7f08",         # load indexed entry pointer +8
    0x587E43:"4881fe09020000",   # helper enforces <= 0x209
    0x587E9D:"488d045b",         # 3*index
    0x587EA6:"48c1e004",         # *16 => 48-byte record stride
    0x587EAA:"4c01e0",           # add server-owned array base
}
CALLS={0xA413F6:0x587E30,0xA413AF:0xAE0E90}

class ProofError(ValueError):pass

def elf_va_bytes(data:bytes,va:int,size:int)->bytes:
    if data[:6]!=b"\x7fELF\x02\x01":
        raise ProofError("NOT_ELF64_LE")
    phoff,=struct.unpack_from("<Q",data,0x20)
    ent,count=struct.unpack_from("<HH",data,0x36)
    if ent<56 or count<1 or phoff+ent*count>len(data):
        raise ProofError("BAD_ELF_PROGRAM_HEADERS")
    for i in range(count):
        at=phoff+i*ent
        typ,flags,offset,base,_paddr,filesz,_memsz,_align=struct.unpack_from(
            "<IIQQQQQQ",data,at)
        if typ!=1 or not(flags&0x1):continue
        if base<=va and va+size<=base+filesz and offset+filesz<=len(data):
            return data[offset+va-base:offset+va-base+size]
    raise ProofError("ELF_VA_UNMAPPED")

def proof(data:bytes)->dict:
    if len(data)!=ELF_BYTES or hashlib.sha256(data).hexdigest()!=SHA:
        raise ProofError("WORLD_SHA_OR_SIZE_MISMATCH")
    for va,raw in ANCHORS.items():
        expected=bytes.fromhex(raw)
        if elf_va_bytes(data,va,len(expected))!=expected:
            raise ProofError(f"INSTRUCTION_CHANGED_{va:X}")
    for va,dest in CALLS.items():
        instr=elf_va_bytes(data,va,5)
        if instr[0]!=0xE8 or va+5+struct.unpack_from("<i",instr,1)[0]!=dest:
            raise ProofError(f"CALL_TARGET_CHANGED_{va:X}")
    return {
        "status":"PASS","mode":"EXACT_WORLDSVR_READ_ONLY",
        "world_sha256":SHA,"original_platinum_opcode":"0x0B10",
        "packet_list_count_offset":10,"list_start_offset":12,
        "list_element_bytes":2,"packet_bytes_formula":"12+2*count",
        "original_server_max_index":521,
        "server_indexed_entry_stride_bytes":48,
        "server_index_array_base":"USERDATACONTEXT +0x6508 (from code)",
        "indexed_item_record_field_used":"+0x8 (masked with 0x06000FFF)",
        "instruction_anchors_checked":len(ANCHORS),
        "calls_checked":len(CALLS),
        "new_0BDA_inventory_selection_abi_verified":False,
        "item_33554961_actual_stack_quantity_codec_verified":False,
        "client_or_server_modified":False,
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world",required=True,type=Path)
    args=parser.parse_args()
    print(json.dumps(proof(args.world.read_bytes()),indent=2))
if __name__=="__main__":main()
