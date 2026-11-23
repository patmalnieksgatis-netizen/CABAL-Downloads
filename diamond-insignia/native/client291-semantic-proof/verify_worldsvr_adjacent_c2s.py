#!/usr/bin/env python3
"""Source-pinned read-only verification of 4 client Merit-adjacent C2S WorldSvr handlers.

No networking, patching, game execution, or user/session database reads.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

SHA="caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3"
REGISTRY=0x235f8c0
# opcode : (registry test, function-pointer store, label-pointer store,
#           handler, server label)
ENTRIES={
  0x09f3:(0x8fbf6d,0x8fbfa8,0x8fbfb4,0xa40d90,
          "CSC_MERIT_MASTERY_LV_UP: OnCSCMeritMasteryLvUp"),
  0x09f9:(0x8fc1b2,0x8fc1ed,0x8fc1f9,0x78c130,
          "CSC_DIMENSION_INVENTORY_LIST: OnCSCDimensionInventoryList"),
  0x09fb:(0x8fc258,0x8fc293,0x8fc29f,0x78d270,
          "CSC_DIMENSION_INVENTORY_EXPEND: OnCSCDimensionInventoryExpend"),
  0x09fd:(0x8fc2fe,0x8fc339,0x8fc345,0x78e5d0,
          "CSC_DIMENSION_INVENTORY_MOVE_PROCESS: OnCSCDimensionInventoryMoveProcess")
}

def u32(raw,offset=0):
    return struct.unpack_from("<I",raw,offset)[0]

def verify_entry(read,opcode,entry):
    compare_site,handler_site,label_site,expected_handler,expected_label=entry
    compare=read(compare_site,8)
    if compare[:3]!=bytes.fromhex("48833d") or compare[7]!=0:
        raise ValueError("registry opcode reference changed")
    slot=compare_site+8+struct.unpack_from("<i",compare,3)[0]
    if slot!=REGISTRY+8*opcode:
        raise ValueError("registry slot mismatch")
    raw_handler=read(handler_site,7)
    if raw_handler[:3]!=bytes.fromhex("48c700"):
        raise ValueError("handler store changed")
    handler=u32(raw_handler,3)
    if handler!=expected_handler:
        raise ValueError("handler pointer mismatch")
    raw_label=read(label_site,8)
    if raw_label[:4]!=bytes.fromhex("48c74318"):
        raise ValueError("label pointer store changed")
    label_addr=u32(raw_label,4)
    label=read(label_addr,len(expected_label)+1)
    if label!=expected_label.encode("ascii")+b"\x00":
        raise ValueError("handler label mismatch")
    return {"opcode":hex(opcode),"slot_va":hex(slot),"handler_va":hex(handler),
            "handler_label":expected_label,"registration_va":hex(compare_site)}

def verify_merit_dispatch(read):
    """Proof that legacy 0x09F3 has TWO server-side Merit paths."""
    anchors={
        0xa40dc0:"8b700a",       # first C2S DWORD
        0xa40dca:"8b400e",       # second C2S DWORD
        0xa40dda:"488d4de8",     # pass two local fields
        0xa40deb:"7513",         # branch based on server selector
        0xa3ca58:"488b9730010000", # manager's search-tree root
        0xa3ca8c:"394820",       # compare manager key to first DWORD
        0xa3caef:"83782401",     # compare selected entry metadata to 1
    }
    for site,expected in anchors.items():
        want=bytes.fromhex(expected)
        if read(site,len(want))!=want:
            raise ValueError("Merit branch instruction changed at "+hex(site))
    for site,dst in ((0xa40dd3,0xa3ca50),(0xa40ded,0xa3b2d0),
                     (0xa40e00,0xa3c3a0)):
        b=read(site,5)
        if b[0]!=0xe8 or site+5+struct.unpack_from("<i",b,1)[0]!=dst:
            raise ValueError("Merit dispatch CALL changed at "+hex(site))
    return {
        "incoming_opcode":"0x09f3",
        "payload_dword_offsets":["0x0a","0x0e"],
        "server_selector_rva":"0xa3ca50",
        "branch_if_selector_zero":"0xa3b2d0",
        "branch_if_selector_nonzero":"0xa3c3a0",
        "selector_lookup":"tree keyed from first C2S DWORD, value flag compared with 1",
        "mastery_159_474_accepted_proven":False,
        "diamond_rankup_semantics_proven":False
    }

def elf_reader(exe):
    if exe[:4]!=b"\x7fELF" or exe[4]!=2 or exe[5]!=1:
        raise ValueError("not ELF64 little-endian")
    if struct.unpack_from("<H",exe,16)[0]!=2:
        raise ValueError("not ET_EXEC")
    phoff=struct.unpack_from("<Q",exe,32)[0]
    entsize=struct.unpack_from("<H",exe,54)[0]
    count=struct.unpack_from("<H",exe,56)[0]
    if count>128 or entsize<56 or phoff+count*entsize>len(exe):
        raise ValueError("invalid ELF program headers")
    segments=[]
    for i in range(count):
        off=phoff+i*entsize
        typ=struct.unpack_from("<I",exe,off)[0]
        if typ==1:
            fileoff=struct.unpack_from("<Q",exe,off+8)[0]
            va=struct.unpack_from("<Q",exe,off+16)[0]
            filesize=struct.unpack_from("<Q",exe,off+32)[0]
            if fileoff+filesize>len(exe):raise ValueError("invalid PT_LOAD")
            segments.append((va,fileoff,filesize))
    def read(va,size):
        if size<1 or size>256:raise ValueError("invalid read size")
        for start,off,length in segments:
            if start<=va and va+size<=start+length:
                return exe[off+va-start:off+va-start+size]
        raise ValueError("unmapped virtual address "+hex(va))
    return read

def inspect(exe):
    if len(exe)!=10596184 or hashlib.sha256(exe).hexdigest()!=SHA:
        raise ValueError("wrong exact WorldSvr binary")
    reader=elf_reader(exe)
    entries=[verify_entry(reader,opcode,entry) for opcode,entry in ENTRIES.items()]
    merit_dispatch=verify_merit_dispatch(reader)
    return {
        "mode":"EXACT_WORLDSVR_C2S_REGISTRY_STATIC",
        "worldsvr_sha256":SHA,
        "registration_evidence":entries,
        "merit_dispatch_evidence":merit_dispatch,
        "dimension_inventory_not_diamond":[hex(x) for x in (0x09f9,0x09fb,0x09fd)],
        "client_ui_event_mapping_correlated":True,
        "diamond_rankup_opcode_proven":False,
        "runtime_packet_capture_performed":False,
        "worldsvr_modified":False
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("worldsvr",type=Path)
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    if args.out and args.out.exists():p.error("refuse overwrite")
    data=inspect(args.worldsvr.read_bytes())
    report=json.dumps(data,indent=2)+"\n"
    if args.out:args.out.write_text(report,encoding="utf-8")
    else:print(report,end="")
if __name__=="__main__":main()
