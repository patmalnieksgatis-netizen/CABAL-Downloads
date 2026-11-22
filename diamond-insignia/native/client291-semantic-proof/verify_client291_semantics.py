#!/usr/bin/env python3
"""Read-only exact-hash CABAL v291 0x09F3 client routing and Merit budget flow proof.

No game launch, no process access, no packet capture, no server changes.
This does not prove that Diamond Insignia uses 0x09F3.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path

EXE_SHA = '52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9'
MERIT_SHA = '3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a'
IMAGEBASE = 0x140000000

class PE:
    def __init__(self, path: Path):
        self.file = path
        self.data = path.read_bytes()
        self.sha = hashlib.sha256(self.data).hexdigest()
        if self.sha != EXE_SHA:
            raise ValueError(f'WRONG_CLIENT_SHA256 {self.sha}')
        if self.data[:2] != b'MZ': raise ValueError('NOT_MZ')
        pe = struct.unpack_from('<I', self.data, 0x3c)[0]
        if self.data[pe:pe+4] != b'PE\x00\x00':raise ValueError('NOT_PE')
        number = struct.unpack_from('<H',self.data,pe+6)[0]
        opt = pe+24
        if struct.unpack_from('<H',self.data,opt)[0]!=0x20b:
            raise ValueError('NOT_PE32_PLUS')
        if struct.unpack_from('<Q',self.data,opt+24)[0]!=IMAGEBASE:
            raise ValueError('WRONG_IMAGEBASE')
        self.sections=[]
        for i in range(number):
            o=opt+struct.unpack_from('<H',self.data,pe+20)[0]+i*40
            name=self.data[o:o+8].split(b'\0')[0].decode('ascii','replace')
            virtual_size,virtual_address,raw_size,raw_start=struct.unpack_from('<IIII',self.data,o+8)
            self.sections.append({'name':name,'rva':virtual_address,'virtual_size':virtual_size,
                                  'size':raw_size,'off':raw_start})
        self.text=next(s for s in self.sections if s['name']=='.text')
        pdata=next(s for s in self.sections if s['name']=='.pdata')
        self.pdata=[]
        for o in range(pdata['off'],pdata['off']+pdata['size']-11,12):
            first,last,_=struct.unpack_from('<III',self.data,o)
            if 0 < first < last < 0x2000000:self.pdata.append((first,last))
    def at(self,rva,length):
        for s in self.sections:
            if s['rva']<=rva and rva+length<=s['rva']+s['size']:
                off=s['off']+rva-s['rva']
                if off+length>len(self.data):break
                return self.data[off:off+length]
        raise ValueError(f'RVA_NOT_FILE_BACKED {rva:x} {length}')
    def exact(self,rva,expected,why):
        expected=bytes.fromhex(expected.replace(' ',''))
        actual=self.at(rva,len(expected))
        if actual!=expected:
            raise ValueError(f'OPCODE_MISMATCH {why}@{rva:#x} expected={expected.hex()} actual={actual.hex()}')
        return dict(rva=hex(rva),bytes=actual.hex(),meaning=why)
    def rip_lea(self,rva,target,why):
        code=self.at(rva,7)
        if code[:3] != bytes.fromhex('488d15'):
            raise ValueError(f'NOT_EXPECTED_LEA {why}@{rva:#x} {code.hex()}')
        resolved=rva+7+struct.unpack_from('<i',code,3)[0]
        if resolved!=target:raise ValueError(f'LEA_TARGET_MISMATCH {why}: {resolved:#x} != {target:#x}')
        return dict(rva=hex(rva),target_rva=hex(target),bytes=code.hex(),meaning=why)
    def near_call(self,rva,target,why):
        code=self.at(rva,5)
        if code[0]!=0xe8:raise ValueError(f'NOT_DIRECT_CALL {why}@{rva:#x}')
        resolved=rva+5+struct.unpack_from('<i',code,1)[0]
        if resolved!=target:raise ValueError(f'WRONG_CALL_TARGET {why}: {resolved:#x} != {target:#x}')
        return dict(rva=hex(rva),target_rva=hex(target),bytes=code.hex(),meaning=why)
    def function(self,rva):
        hits=[(a,b) for a,b in self.pdata if a<=rva<b]
        if len(hits)!=1:raise ValueError(f'MISSING_OR_MULTIPLE_PDATA {rva:#x}: {hits}')
        a,b=hits[0]
        return {'query_rva':hex(rva),'begin':hex(a),'end':hex(b)}

def check(pe:PE, merit:Path):
    b=merit.read_bytes(); mer_sha=hashlib.sha256(b).hexdigest()
    if mer_sha!=MERIT_SHA:raise ValueError(f'WRONG_MERIT_SHA256 {mer_sha}')
    route=[
        pe.exact(0x6f1253,'c74510a2010000','Local event ID 0x1A2 binds nearby function pointer'),
        pe.rip_lea(0x6f123f,0x6ff14c,'Local event 0x1A2 -> C2S 0x09F3 function'),
        pe.exact(0x6efed7,'c74510f3090000','Network handler ID 0x09F3'),
        pe.rip_lea(0x6efeee,0x6f84fc,'S2C 0x09F3 -> receive callback'),
    ]
    request=[
        pe.exact(0x6ff157,'b8f3090000','C2S 0x09F3'),
        pe.exact(0x6ff161,'c7442420e2b71200','C2S 18-byte packet header'),
        pe.exact(0x244d24,'8b8118010000','Client singleton DWORD +0x118 getter'),
        pe.exact(0x244d2c,'8b811c010000','Client singleton DWORD +0x11C getter'),
        pe.exact(0x244d34,'8b8120010000','Client singleton DWORD +0x120 getter'),
        pe.exact(0x6ff17c,'8944242a','C2S field +0x0A'),
        pe.exact(0x6ff197,'8944242e','C2S field +0x0E'),
    ]
    response=[
        pe.exact(0x6f851c,'807d0601','Client requires success status byte +6 == 1'),
        pe.exact(0x6f8585,'8b5507','Success path reads DWORD at +7 into EDX'),
        pe.near_call(0x6f858f,0x37fa34,'Store +7 DWORD into global Merit budget at +0xAB6C'),
        pe.exact(0x6f85a5,'83f801','Condition for category 1'),
        pe.exact(0x6f85af,'83f802','Condition for category 2'),
        pe.exact(0x6f85b9,'8b5d07','Second success path reads DWORD at +7 into EBX'),
        pe.near_call(0x6f85d0,0x37f9d8,'Store +7 DWORD as keyed Merit map value'),
        pe.exact(0x37fa34,'89916cab0000','Global Merit budget setter'),
        pe.exact(0x37fa1b,'895814','Merit map node DWORD value set from R9D'),
    ]
    ui=[
        pe.exact(0x2523bf,'8b806cab0000','UI retrieves global Merit budget'),
        pe.exact(0x2523e0,'443be0','UI compares allocated sum with global budget'),
        pe.exact(0x63b70f,'8b806cab0000','Second UI path retrieves same budget'),
        pe.exact(0x63b72b,'3bf0','Second UI path compares allocated sum and budget'),
        pe.exact(0x63b72d,'7e1c','Branch when allocated sum does not exceed budget'),
    ]
    funcs=[pe.function(r) for r in [0x6ff14c,0x6f84fc,0x37f9d8,0x2523bf,0x63b70f]]
    j=pe.data.find(b'dia_meritscore_fomula\x00')
    if j<0:raise ValueError('DIA_STRING_MISSING')
    near=pe.data[max(0,j-400):j+250]
    for s in (b'trophyreward_meritscore',b'trophy_transform',b'dia_meritscore_fomula'):
        if s not in near:raise ValueError(f'TROPHY_CONTEXT_NOT_PROVEN {s!r}')
    return {
       'status':'PASS','mode':'READ_ONLY_EXACT_CLIENT_SEMANTIC_PROOF',
       'client_sha256':pe.sha,'merit_enc_sha256':mer_sha,
       'functions':funcs,'routing':route,'request':request,
       'response_success_conditional_value':response,'ui_budget_usage':ui,
       'dia_meritscore_fomula_context':'Located among trophyreward_meritscore and trophy_transform; NOT proof of Diamond Insignia',
       'legacy_7_byte_success':'CONDITIONAL_DWORD_AT_PLUS7_NOT_PRESENT; POTENTIAL_CLIENT_BUDGET_CORRUPTION',
       'server_11_byte_success':'NOT_PROVEN; authoritative +7 value and WorldSvr response path still required',
       'diamond_insignia_command':'UNKNOWN; local event 0x1A2 does NOT prove Diamond UI action',
       'game_files_modified':False,'vm_modified':False,
    }

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--client',required=True,type=Path)
    a.add_argument('--merit',required=True,type=Path)
    a.add_argument('--report',type=Path)
    v=a.parse_args()
    try:
        report=check(PE(v.client),v.merit)
        if v.report:
            v.report.parent.mkdir(parents=True,exist_ok=True)
            v.report.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print('DIAMOND_V291_CLIENT_SEMANTIC_EVIDENCE=PASS')
        print('LEGACY_09F3_LOCAL_EVENT=0x1A2')
        print('LEGACY_09F3_PLUS7_FIELD=MERIT_BUDGET_OR_KEYED_STATE_VALUE')
        print('TROPHY_DIA_FORMULA_IS_NOT_DIAMOND_INSIGNIA_PROOF=YES')
        print('LIVE_PATCH=NOT_READY;NO_GAME_FILES_MODIFIED=YES')
    except (ValueError, OSError) as exc:
        print('DIAMOND_V291_CLIENT_SEMANTIC_EVIDENCE=FAIL',str(exc))
        raise SystemExit(1)
