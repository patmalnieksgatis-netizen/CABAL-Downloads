#!/usr/bin/env python3
"""Source-pinned, READ-ONLY v291 CABAL x64 Merit resource loading audit.

Input: exact archive with CabalMain.exe and meritsystem.enc. Zero writes to
client or VM, does not claim Diamond UI or live gameplay integration.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path

CLIENT_SHA = '52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9'
MERIT_SHA = '3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a'
XOR4 = bytes.fromhex('92 65 67 57')

class EvidenceError(RuntimeError): pass

def h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

class PE:
    def __init__(self, data: bytes):
        if len(data) != 15089000 or h(data) != CLIENT_SHA:
            raise EvidenceError('EXACT_CLIENT_SHA_OR_SIZE_MISMATCH')
        if data[:2] != b'MZ':
            raise EvidenceError('INVALID_MZ')
        nt, = struct.unpack_from('<I',data,0x3c)
        if data[nt:nt+4] != b'PE\0\0' or struct.unpack_from('<H',data,nt+24)[0] != 0x20b:
            raise EvidenceError('INVALID_PE64')
        if struct.unpack_from('<Q',data,nt+24+24)[0] != 0x140000000:
            raise EvidenceError('UNEXPECTED_IMAGEBASE')
        count = struct.unpack_from('<H',data,nt+6)[0]
        section_base = nt+24+struct.unpack_from('<H',data,nt+20)[0]
        sections = []
        for i in range(count):
            at = section_base+40*i
            vsize,va,rsize,foff=struct.unpack_from('<IIII',data,at+8)
            sections.append((va,rsize,foff,data[at:at+8].split(b'\0')[0].decode('ascii','replace')))
        self.data,self.sections = data,sections

    def rva(self, rva: int, length: int = 1) -> bytes:
        if length<1 or rva<0: raise EvidenceError('INVALID_READ')
        for va,size,foff,_name in self.sections:
            if va <= rva and rva+length <= va+size:
                start=foff+rva-va
                if start+length>len(self.data): break
                return self.data[start:start+length]
        raise EvidenceError(f'UNMAPPED_RVA {rva:x} length {length}')

    def check(self,rva:int,raw:str):
        expected=bytes.fromhex(raw)
        if self.rva(rva,len(expected))!=expected:
            raise EvidenceError(f'OPCODE_MISMATCH RVA=0x{rva:x}')

    def call(self,rva:int,target:int):
        b=self.rva(rva,5)
        actual=rva+5+struct.unpack_from('<i',b,1)[0]
        if b[0]!=0xe8 or actual!=target:
            raise EvidenceError(f'CALL_MISMATCH RVA=0x{rva:x} wanted=0x{target:x} actual=0x{actual:x}')

    def cstr(self,rva:int,maxlen:int=64)->str:
        raw=self.rva(rva,maxlen)
        return raw.split(b'\0',1)[0].decode('ascii','strict')

def inspect(client:bytes,merit:bytes) -> dict:
    pe=PE(client)
    if len(merit)!=41368 or h(merit)!=MERIT_SHA:
        raise EvidenceError('EXACT_MERITSYSTEM_SHA_OR_SIZE_MISMATCH')
    if pe.cstr(0xb5ee68) != 'meritsystem.enc' or pe.cstr(0xb5ee78) != 'meritsystem_msg.enc':
        raise EvidenceError('SELECTOR_LITERAL_MISMATCH')
    checks = {
        0x21c21e:'4183f834',
        0x21c4a5:'488d15bc299400',
        0x21c4c1:'4183e835',
        0x21c564:'4c8d0d0d299400',
        0x21d938:'81fa89000000',
        0x21ce6e:'8bd7',
        0x21ce78:'ffc7',
        0x21ce7a:'81ff85000000',
        0x21ce80:'7cec',
        0x26927a:'488d0dafd1b600',
        0x21cde2:'4c8d4208',
        0x21cdeb:'90488b542440',
        0x2179c7:'488d4804',
        0x2b7ac5:'410fb6400383f057',
        0x2b7ad5:'410fb6400283f067',
        0x2b7ae5:'410fb6400183f065',
        0x2b7af5:'410fb6003592000000',
    }
    for rva,raw in checks.items():pe.check(rva,raw)
    edges = [(0x269281,0x21ce38),(0x21ce73,0x21cda4),
             (0x21cdc6,0x21cbd4),(0x21cde6,0x2178e0),
             (0x217a17,0x2b7fac),(0x2b7fc7,0x2b8b08),
             (0x2b802a,0x2b7a90)]
    for src,dst in edges:pe.call(src,dst)
    route = pe.rva(0x21d96c,0x8a)
    header = struct.unpack_from('<I',merit,0)[0]
    xored = bytes(a^b for a,b in zip(merit[4:8],XOR4))
    btype=(xored[0]>>1)&3
    if btype!=3:raise EvidenceError('UNEXPECTED_DEFLATE_FIRST_BYTE')
    lower = client.lower()
    return {
      'mode':'READ_ONLY_EXACT_V291_RESOURCE_ROUTE',
      'client_sha256':h(client),'merit_sha256':h(merit),
      'exact_sha_match':'PASS','instruction_anchors':len(checks),
      'verified_call_edges':len(edges),
      'selector_names':{'52':pe.cstr(0xb5ee68),'53':pe.cstr(0xb5ee78)},
      'upstream_initialization_call':'0x269281 -> 0x21ce38; observed static call, runtime execution not observed',
      'loader_loop_range':{'first':0,'last_inclusive':132,'entry_rva':'0x21ce73'},
      'path_selector_flag':{'52':int(route[52]),'53':int(route[53]),
          'interpretation':'selects different filename/path assembly branch; not a codec flag'},
      'decompress_call':'0x21cde6 -> 0x2178e0',
      'direct_caller_check':'no immediate return-code branch after call; does not prove later success',
      'xor4_first4_bytes':'92 65 67 57',
      'expected_unpacked_bytes_if_header':header,
      'actual_enc_first4_after_header':merit[4:8].hex(),
      'post_xor_first4':xored.hex(),
      'post_xor_raw_deflate_block_type':btype,
      'raw_deflate_result':'invalid if this exact XOR4 path consumes the provided .enc as-is',
      'ASCII_diamond_or_insignia_in_exe':bool(b'diamond' in lower or b'insignia' in lower),
      'diamond_packet_opcode':'NOT_PROVEN',
      'client_files_modified':False,'vm_modified':False,
      'next_evidence':'trace actual loaded Merit resource bytes or identify alternate resource processing before proposing client patch',
    }

def inspect_archive(archive:Path)->dict:
    with zipfile.ZipFile(archive) as z:
        if sorted(z.namelist())!=['CabalMain.exe','meritsystem.enc']:
            raise EvidenceError('EXACT_CLIENT_ARCHIVE_NAMES_REQUIRED')
        if z.testzip() is not None:raise EvidenceError('ZIP_CORRUPTED')
        return inspect(z.read('CabalMain.exe'),z.read('meritsystem.enc'))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--archive',required=True,type=Path)
    ap.add_argument('--report',type=Path)
    args=ap.parse_args()
    try:
        result=inspect_archive(args.archive)
    except (EvidenceError,OSError,ValueError,zipfile.BadZipFile) as e:
        print('DIAMOND_RESOURCE_ROUTE=FAIL',str(e))
        return 2
    output=json.dumps(result,indent=2,ensure_ascii=False)+'\n'
    if args.report:
        args.report.write_text(output,encoding='utf-8')
    print(output)
    return 0
if __name__=='__main__':raise SystemExit(main())
