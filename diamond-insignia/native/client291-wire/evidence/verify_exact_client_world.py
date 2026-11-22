#!/usr/bin/env python3
"""Read-only verification pinned to exact CABAL v291 x64 client and WorldSvr."""
import argparse, hashlib, struct
from pathlib import Path
C='52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9'
M='3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a'
W='caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3'

def load(path,sha):
    b=Path(path).read_bytes()
    got=hashlib.sha256(b).hexdigest()
    if got!=sha: raise ValueError(f"STOP wrong SHA for {path}: {got}")
    return b

def pe_mapper(b):
    assert b[:2]==b'MZ'
    pe=struct.unpack_from('<I',b,0x3c)[0]
    assert b[pe:pe+4]==b'PE\0\0'
    n=struct.unpack_from('<H',b,pe+6)[0]
    opt=pe+24
    assert struct.unpack_from('<H',b,opt)[0]==0x20b
    sec=pe+24+struct.unpack_from('<H',b,pe+20)[0]
    sections=[]
    for i in range(n):
        q=sec+40*i
        size,rva,raw_size,off=struct.unpack_from('<IIII',b,q+8)
        sections.append((rva,rva+raw_size,off))
    def read(rva,n):
        for start,end,off in sections:
            if start<=rva and rva+n<=end:
                return b[off+rva-start:off+rva-start+n]
        raise ValueError(f"PE RVA outside file: 0x{rva:x}")
    return read

def elf_mapper(b):
    assert b[:4]==b'\x7fELF' and b[4]==2 and b[5]==1
    off=struct.unpack_from('<Q',b,32)[0]
    size,count=struct.unpack_from('<HH',b,54)
    segments=[]
    for i in range(count):
        q=off+size*i
        typ,flags,p_off,vaddr,paddr,filesz,memsz,align=struct.unpack_from('<IIQQQQQQ',b,q)
        if typ==1: segments.append((vaddr,vaddr+filesz,p_off))
    def read(addr,n):
        for start,end,off in segments:
            if start<=addr and addr+n<=end:
                return b[off+addr-start:off+addr-start+n]
        raise ValueError(f"ELF address outside file 0x{addr:x}")
    return read

def check(read,marks,kind):
    for at,machine in marks.items():
        expected=bytes.fromhex(machine)
        if read(at,len(expected))!=expected:
            raise ValueError(f"{kind} instruction mismatch at 0x{at:x}")
    return len(marks)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--client',required=True)
    p.add_argument('--merit',required=True)
    p.add_argument('--world',required=True)
    a=p.parse_args()
    pe=pe_mapper(load(a.client,C))
    load(a.merit,M)
    elf=elf_mapper(load(a.world,W))
    client={
      0x6ff152:'83 64 24 24 00',0x6ff157:'b8 f3 09 00 00',
      0x6ff15c:'66 89 44 24 28',
      0x6ff161:'c7 44 24 20 e2 b7 12 00',
      0x6ff17c:'89 44 24 2a',0x6ff197:'89 44 24 2e',
      0x244d24:'8b 81 18 01 00 00 c3',
      0x244d2c:'8b 81 1c 01 00 00 c3',
      0x6efed7:'c7 45 10 f3 09 00 00',
      0x6efeee:'48 8d 15 07 86 00 00',
      0x6f851c:'80 7d 06 01',0x6f852a:'0f 85 d8 00 00 00',
      0x6f8585:'8b 55 07',0x6f85b9:'8b 5d 07',
      0x25621c:'48 8d 15 7d c8 90 00',
    }
    world={
      0xa40dc0:'8b 70 0a',0xa40dca:'8b 40 0e',
      0xa3b544:'b8 f3 09 00 00',0xa3b549:'ba 07 00 00 00',
      0xa3b551:'c7 85 90 fe ff ff e2 b7 07 00',
      0xa3b562:'c6 85 96 fe ff ff 01',
      0xa3b5ca:'ba f3 09 00 00',0xa3b5dd:'ba 07 00 00 00',
      0xa3b5ec:'c6 85 96 fe ff ff 00'
    }
    nc=check(pe,client,'client')
    nw=check(elf,world,'world')
    rel=struct.unpack('<i',pe(0x6efef1,4))[0]
    assert 0x6efeee+7+rel==0x6f84fc
    rel=struct.unpack('<i',pe(0x25621f,4))[0]
    ptr=0x25621c+7+rel
    assert pe(ptr,len(b'dia_meritscore_fomula\0'))==b'dia_meritscore_fomula\0'
    print(f"CLIENT_SOURCE_EXACT=PASS;INSTRUCTIONS={nc}")
    print(f"WORLD_SOURCE_EXACT=PASS;INSTRUCTIONS={nw}")
    print("CLIENT_09F3_C2S_18_BYTES=PROVEN")
    print("CLIENT_09F3_S2C_SUCCESS_CONDITIONALLY_READS_DWORD_AT_PLUS7=PROVEN")
    print("WORLD_09F3_SUCCESS_7_BYTES=PROVEN")
    print("DIAMOND_OPCODE_AND_S2C_FIELDS=NOT_PROVEN;NO_PATCH")
if __name__=='__main__':main()
