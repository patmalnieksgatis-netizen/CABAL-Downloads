#!/usr/bin/env python3
"""Owner WorldSvr 0xAE0E90 item-count helper proof. Read-only exact ELF.

Proves the three stack bit-extraction modes and that item 33554961's runtime
metadata is NOT present in the file image. No GameData/SQL changes or hooks.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

EXACT_SHA="caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3"
EXACT_SIZE=10596184
ITEM_ID=33554961
ANCHORS={
  0xAE0E90:"488b07",       # raw kind from [rdi+0]
  0xAE0E99:"25ff0f0000",   # kind & 0xFFF
  0xAE0E9E:"c1ea19",       # kind>>25
  0xAE0EA5:"83e203",       # variant & 3
  0xAE0EB4:"48c1e20f",     # variant25<<15
  0xAE0EB8:"488d94c2008e2e01", # runtime metadata table
  0xAE0EC5:"837a3c01",     # signed metadata field 0x3C <=1 ->1
  0xAE0ECB:"8b5238",       # classify tag +0x38
  0xAE0ECE:"488b4710",     # raw option from slot+0x18
  0xAE0ED2:"83fa46",       # tag 0x46
  0xAE0ED9:"81faaf000000", # tag 0xAF
  0xAE0EE1:"81fab8000000", # tag 0xB8
  0xAE0EE9:"0fb7c0",       # 16 bit option units
  0xAE0EF0:"83fa1b",       # tag 0x1B
  0xAE0EF5:"83fa43",       # tag 0x43
  0xAE0EFA:"83fa10",       # tag 0x10
  0xAE0EFF:"83e07f",       # 7 bit option units
  0xAE0F08:"83fa66",       # tag 0x66
  0xAE0F10:"c1e816",       # 10 bit option units
  0xA413AB:"498d7f08",     # original Platinum passes slot+8 as item pointer
  0xA413AF:"e8dcfa0900",   # exact helper call 0xAE0E90
  0xA413BB:"0185e4feffff", # add decoded quantity
  0x587EA6:"48c1e004",     # 48 byte index stride
}
class EvidenceError(ValueError):pass

def segments(elf):
    if elf[:6]!=b"\x7fELF\x02\x01":raise EvidenceError("NOT_ELF64_LE")
    off,=struct.unpack_from("<Q",elf,0x20)
    size,count=struct.unpack_from("<HH",elf,0x36)
    if not size or size<56 or not count or off+size*count>len(elf):
        raise EvidenceError("INVALID_ELF_SEGMENTS")
    rows=[]
    for i in range(count):
        seg=struct.unpack_from("<IIQQQQQQ",elf,off+i*size)
        if seg[0]==1:rows.append(seg)
    return rows

def mapped(elf,rows,va,n):
    for typ,flags,off,base,paddr,filesz,memsz,align in rows:
        if base<=va and va+n<=base+filesz and off+filesz<=len(elf):
            return elf[off+va-base:off+va-base+n]
    raise EvidenceError(f"UNMAPPED_FILE_RVA_0x{va:X}")

def metadata_address(kind):
    idx=kind&0xFFF
    variant=(kind>>25)&3
    return 0x12E8E00+(variant*25<<15)+(idx*25*8)

def evidence(elf):
    if len(elf)!=EXACT_SIZE or hashlib.sha256(elf).hexdigest()!=EXACT_SHA:
        raise EvidenceError("WRONG_WORLD_FILE_SHA_OR_SIZE")
    rows=segments(elf)
    for va,h in ANCHORS.items():
        if mapped(elf,rows,va,len(bytes.fromhex(h)))!=bytes.fromhex(h):
            raise EvidenceError(f"CHANGED_INSTRUCTION_0x{va:X}")
    countcall=mapped(elf,rows,0xA413AF,5)
    if 0xA413AF+5+struct.unpack_from("<i",countcall,1)[0]!=0xAE0E90:
        raise EvidenceError("COUNT_HELPER_CALL_CHANGED")
    addr=metadata_address(ITEM_ID)
    relevant=[p for p in rows if p[3]<=addr and addr+0x40<=p[3]+p[6]]
    if len(relevant)!=1:raise EvidenceError("ITEM_METADATA_NOT_MAPPED_IN_MEMORY")
    seg=relevant[0]
    backed=addr+0x40<=seg[3]+seg[5]
    if backed:raise EvidenceError("ITEM_METADATA_NOW_FILE_BACKED_RECHECK")
    return {"status":"PASS","world_sha256":EXACT_SHA,
      "count_function_va":"0xAE0E90","inventory_slot_entry_bytes":48,
      "owner_slot_base_offset":8,"option_offset_from_slot":24,
      "metadata_kind_index":ITEM_ID&0xFFF,
      "metadata_variant":(ITEM_ID>>25)&3,
      "metadata_runtime_va":f"0x{addr:X}",
      "metadata_present_in_static_elf":False,
      "runtime_metadata_required":True,
      "kind_field38_classes":{
        "low_7_option_bits":["0x10","0x1B","0x66"],
        "low_16_option_bits":["0xAF","0xB8"],
        "bits_22_to_31":["0x43","0x46"],
        "other":"unmasked numeric ItemOption"},
      "metadata_field3c_le_1":"count 1",
      "static_anchors_checked":len(ANCHORS),
      "original_call_verified":True,
      "item_33554961_specific_classification_proven":False,
      "live_sql_or_world_modified":False}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world",required=True,type=Path)
    args=p.parse_args()
    print(json.dumps(evidence(args.world.read_bytes()),indent=2))
if __name__=="__main__":
    main()
