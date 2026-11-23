#!/usr/bin/env python3
"""Verify the v291 x64 Merit 0x09F3 S2C conditional DWORD reads from actual EXE.
Read-only: no process injection, modified client, WorldSvr, SQL or live game.
RVA refers to the exact original CabalMain.exe, not file offsets.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

EXPECTED_SHA="52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9"
HANDLER=0x6F84FC
END=0x6F86AA
LOOKUP=0x24375C

class PE64:
    def __init__(self,data):
        self.data=data
        if len(data)<0x400 or data[:2]!=b"MZ":
            raise ValueError("not a PE file")
        pe=struct.unpack_from("<I",data,0x3C)[0]
        if pe+24>len(data) or data[pe:pe+4]!=b"PE\\x00\\x00":
            raise ValueError("bad PE header")
        if struct.unpack_from("<H",data,pe+24)[0]!=0x20B:
            raise ValueError("not PE32+ x64")
        count=struct.unpack_from("<H",data,pe+6)[0]
        optsize=struct.unpack_from("<H",data,pe+20)[0]
        self.sections=[]
        for i in range(count):
            o=pe+24+optsize+i*40
            if o+40>len(data):raise ValueError("truncated section header")
            name=data[o:o+8].rstrip(b"\\x00").decode("ascii","replace")
            virtual_size,rva,rawsize,rawptr=struct.unpack_from("<IIII",data,o+8)
            if rawptr+rawsize>len(data):raise ValueError("truncated section")
            self.sections.append((name,rva,virtual_size,rawptr,rawsize))

    def read(self,rva,size):
        for name,begin,virtual,raw,rawsize in self.sections:
            if begin<=rva and rva+size<=begin+min(virtual,rawsize):
                pos=raw+(rva-begin)
                return self.data[pos:pos+size]
        raise ValueError("RVA out of loaded section: %X" % rva)

    def bounds(self,rva):
        pdata=next((x for x in self.sections if x[0]==".pdata"),None)
        if not pdata:raise ValueError("missing .pdata")
        _,begin,virtual,raw,_=pdata
        for off in range(0,virtual-11,12):
            first,last,_=struct.unpack_from("<III",self.data,raw+off)
            if first<=rva<last:return first,last
        raise ValueError("handler has no .pdata function")

# Fixed *machine opcode bytes*, captured from exact SHA-verified CabalMain.
# No conjectured packet meanings or parsed plaintext are embedded here.
SIGNATURES={
    0x6F851C:"807d0601",        # cmp byte ptr [rbp+6], 1
    0x6F8581:"85c0",            # test eax,eax
    0x6F8585:"8b5507",          # first conditional [rbp+7] DWORD
    0x6F85A5:"83f801",          # lookup return == 1?
    0x6F85AF:"83f802",          # lookup return == 2?
    0x6F85B9:"8b5d07",          # second conditional [rbp+7] DWORD
    0x6F86A9:"c3",              # function ret before next INT3
    0x24375C:"4883ec284c8b81a0000000", # lookup accesses singleton+0xA0
    0x243795:"8b4120",          # lookup returns map entry+0x20
    0x6F85C8:"448bcb458bc68bd0", # ebx (packet+7) -> r9d,
                                     # singleton+0x120 -> r8d; lookup -> edx
    0x37FA34:"89916cab0000",    # first branch writes to context+0xAB6C
    0x37FA1B:"895814",          # second branch writes r9d to map node+0x14
}
REL_CALLS={0x6F857C:LOOKUP,0x6F859B:LOOKUP,0x6F85AA:LOOKUP}
STATE_WRITE_CALLS={0x6F858F:0x37FA34,0x6F85D0:0x37F9D8}
JUMPS={
    0x6F852A:(b"\\x0f\\x85",0x6F8608), # status != 1
    0x6F8583:(b"\\x75",0x6F8596),     # first result != 0
    0x6F85A8:(b"\\x74",0x6F85B9),     # second result == 1
    0x6F85B2:(b"\\x75",0x6F85D5),     # third result != 2
}

def verify(reader):
    if reader.bounds(HANDLER)!=(HANDLER,END):
        raise ValueError("unexpected S2C handler .pdata bounds")
    for rva,hexbytes in SIGNATURES.items():
        expected=bytes.fromhex(hexbytes)
        if reader.read(rva,len(expected))!=expected:
            raise ValueError("S2C instruction changed at RVA %X" % rva)
    for rva,callee in {**REL_CALLS,**STATE_WRITE_CALLS}.items():
        raw=reader.read(rva,5)
        if raw[0]!=0xE8 or rva+5+struct.unpack_from("<i",raw,1)[0]!=callee:
            raise ValueError("S2C lookup call changed at RVA %X" % rva)
    for rva,(opcode,target) in JUMPS.items():
        raw=reader.read(rva,6 if len(opcode)==2 else 2)
        if not raw.startswith(opcode):
            raise ValueError("S2C branch opcode changed at RVA %X" % rva)
        offset=struct.unpack_from("<i" if len(opcode)==2 else "<b",raw,len(opcode))[0]
        if rva+len(raw)+offset!=target:
            raise ValueError("S2C branch target changed at RVA %X" % rva)
    return {
        "client_handler_rva":"0x6F84FC",
        "client_handler_pdata_end":"0x6F86AA",
        "opcode":"0x09F3",
        "required_status_byte_at_offset_6":1,
        "lookup_callee_rva":"0x24375C",
        "lookup_calls_rva":[hex(x) for x in REL_CALLS],
        "first_map_return_equals_0_reads_dword_at_rva":"0x6F8585",
        "otherwise_second_equals_1_or_third_equals_2_reads_dword_at_rva":"0x6F85B9",
        "other_observed_lookup_results":"no packet+7 read in this handler",
        "dword_route_zero_client_store":"context + 0xAB6C through RVA 0x37FA34",
        "dword_route_one_or_two_client_store":"map node + 0x14 through RVA 0x37F9D8",
        "client_state_field_passed_as_r8d":"singleton + 0x120",
        "client_state_store_semantics":"unknown; not a Diamond S2C schema",
        "7_byte_success_universally_truncated":False,
        "unknowns":["whether real UI triggers this request",
                    "runtime lookup values and possible state changes",
                    "payload+7 semantic meaning","Diamond S2C response encoding"],
        "live_server_modified":False
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--client",type=Path,required=True)
    p.add_argument("--json",type=Path)
    a=p.parse_args()
    data=a.client.read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    if digest!=EXPECTED_SHA:
        raise SystemExit("STOP: client SHA mismatch "+digest)
    result=verify(PE64(data))
    result["client_sha256"]=digest
    if a.json:a.json.write_text(json.dumps(result,indent=2)+"\\n",encoding="utf-8")
    print("CLIENT291_09F3_SUCCESS_CONDITIONAL_DWORD_BRANCHES=PASS")
    print("LEGACY_7B_SUCCESS_UNIVERSALLY_TRUNCATED=NO")
    print("CLIENT_DWORD_SUCCESS_FIELD_SEMANTICS=UNKNOWN")
    print("LIVE_CLIENT_OR_WORLDSVR_MODIFIED=NO")

if __name__=="__main__":main()
