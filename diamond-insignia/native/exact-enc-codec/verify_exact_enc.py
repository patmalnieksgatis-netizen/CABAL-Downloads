#!/usr/bin/env python3
"""Read-only exact CABAL v291 x64 ENC/XOR evidence gate. No game file edits."""
from pathlib import Path
import hashlib, json, struct, sys, zlib

CLIENT_SHA = "52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9"
MERIT_SHA = "3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a"
XOR = bytes.fromhex("92 65 67 57")

def verify(client: Path, merit: Path):
    exe=client.read_bytes()
    enc=merit.read_bytes()
    if hashlib.sha256(exe).hexdigest()!=CLIENT_SHA: raise ValueError("WRONG_CLIENT_SHA")
    if hashlib.sha256(enc).hexdigest()!=MERIT_SHA: raise ValueError("WRONG_MERIT_SHA")
    pe=struct.unpack_from("<I",exe,0x3c)[0]
    if exe[:2]!=b"MZ" or exe[pe:pe+4]!=b"PE\0\0": raise ValueError("BAD_PE")
    opt=pe+24
    if struct.unpack_from("<H",exe,opt)[0]!=0x20b: raise ValueError("NOT_PE64")
    sections=[]
    for i in range(struct.unpack_from("<H",exe,pe+6)[0]):
        off=opt+struct.unpack_from("<H",exe,pe+20)[0]+40*i
        va,rs,rp=struct.unpack_from("<III",exe,off+12)
        sections.append((va,rs,rp))
    def read(rva,n):
        for va,rs,rp in sections:
            if va<=rva and rva+n<=va+rs:
                b=exe[rp+rva-va:rp+rva-va+n]
                if len(b)==n:return b
        raise ValueError("MISSING_RVA_%x"%rva)
    expected={
        0x2b7a90:"4c634914488bd1443b4910",
        0x2b7ac5:"410fb6400383f057",
        0x2b7ad5:"410fb6400283f067",
        0x2b7ae5:"410fb6400183f065",
        0x2b7af5:"410fb6003592000000",
        0x2179c7:"488d4804"
    }
    for rva,bytestr in expected.items():
        if read(rva,len(bytes.fromhex(bytestr)))!=bytes.fromhex(bytestr):
            raise ValueError("CLIENT_CODEC_OPCODE_MISMATCH_%x"%rva)
    for src,dst in [(0x21cde6,0x2178e0),(0x217a17,0x2b7fac),
                    (0x2b7fc7,0x2b8b08),(0x2b8b36,0x2b8004),
                    (0x2b802a,0x2b7a90)]:
        b=read(src,5)
        if b[0]!=0xe8 or src+5+struct.unpack_from("<i",b,1)[0]!=dst:
            raise ValueError("CLIENT_LOADER_CALL_MISMATCH_%x"%src)
    if len(enc)<8: raise ValueError("SHORT_ENC")
    size=struct.unpack_from("<I",enc)[0]
    head=bytes(enc[i+4]^XOR[i] for i in range(4))
    btype=(head[0]>>1)&3
    result={
        "exact_client_sha256":CLIENT_SHA,"exact_merit_sha256":MERIT_SHA,
        "rva_codec":"0x2B7A90","size_header_unpacked_bytes":size,
        "client_xor_bytes":XOR.hex(),"compressed_first4":enc[4:8].hex(),
        "after_xor_first4":head.hex(),"deflate_block_type":btype,
        "raw_deflate_compatible":btype!=3,
        "warning":"Parser linkage to specific Merit asset NOT confirmed by static call chain",
        "client_modified":False,"server_modified":False
    }
    if btype==3:result["status"]="INCOMPATIBLE_WITH_PROVEN_RAW_DEFLATE_LOADER"
    else:
        x=bytearray(enc[4:]);x[:4]=head
        try:
            decoded=zlib.decompress(bytes(x),-15)
            result["status"]="DECODED" if len(decoded)==size else "UNPACKED_LENGTH_MISMATCH"
            result["decoded_bytes"]=len(decoded)
            result["decoded_sha256"]=hashlib.sha256(decoded).hexdigest()
        except zlib.error as e:
            result["status"]="DEFLATE_REJECTED"
            result["error"]=str(e)
    return result

if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("Usage: verify_exact_enc.py CabalMain.exe meritsystem.enc")
    report=verify(Path(sys.argv[1]),Path(sys.argv[2]))
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report["status"]=="DECODED" else 2)
