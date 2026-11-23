#!/usr/bin/env python3
"""SHA-pinned, read-only v291 direct ENC-loader caller proof; no runtime claims."""
from __future__ import annotations
import argparse
import bisect
import hashlib
import json
import struct
import sys
import zipfile
from pathlib import Path

CLIENT_SHA = "52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9"
CLIENT_BYTES = 15089000
LOADER_RVA = 0x2178E0
KNOWN = {
    0x21CDE6: (0x21CDA4, 0x21CE36, "indexed_resource"),
    0x21D19E: (0x21CE38, 0x21D35B, "resource_initialization_secondary"),
    0x8DC351: (0x8DC214, 0x8DD34D, "independent_large_function"),
}

class ProofError(Exception):
    pass

def sections_and_pdata(exe):
    if len(exe) != CLIENT_BYTES or hashlib.sha256(exe).hexdigest() != CLIENT_SHA:
        raise ProofError("WRONG_CLIENT_SHA_OR_SIZE")
    if exe[:2] != b"MZ":
        raise ProofError("NO_MZ")
    pe, = struct.unpack_from("<I", exe, 0x3c)
    if exe[pe:pe+4] != b"PE\x00\x00":
        raise ProofError("NO_PE")
    count, = struct.unpack_from("<H", exe, pe+6)
    opt_size, = struct.unpack_from("<H", exe, pe+20)
    if struct.unpack_from("<H", exe, pe+24)[0] != 0x20b:
        raise ProofError("NOT_PE64")
    result = {}
    for i in range(count):
        at = pe+24+opt_size+40*i
        name = exe[at:at+8].split(b"\x00")[0].decode("ascii","replace")
        _vsize, rva, size, offset = struct.unpack_from("<IIII", exe, at+8)
        if size and offset+size > len(exe):
            raise ProofError("SECTION_OUT_OF_BOUNDS")
        result[name] = (rva,size,offset)
    if ".text" not in result or ".pdata" not in result:
        raise ProofError("MISSING_SECTIONS")
    _rva,size,offset = result[".pdata"]
    if size % 12:
        raise ProofError("MISALIGNED_PDATA")
    funcs = [struct.unpack_from("<III",exe,offset+i)[:2] for i in range(0,size,12)]
    return result, sorted(funcs)

def scan_direct_calls(data, base_rva, target_rva):
    """Scan potential relative E8 call locations; SHA/pdata anchors pin findings."""
    found = []
    for i in range(len(data)-4):
        if data[i] != 0xE8:
            continue
        disp, = struct.unpack_from("<i",data,i+1)
        if base_rva+i+5+disp == target_rva:
            found.append(base_rva+i)
    return found

def owning_function(rva, funcs):
    i = bisect.bisect_right(funcs,(rva,0xffffffff))-1
    if i < 0:
        return None
    lo,hi=funcs[i]
    return (lo,hi) if lo<=rva<hi else None

def audit(exe):
    sections,funcs=sections_and_pdata(exe)
    rva,size,offset=sections[".text"]
    callers=scan_direct_calls(exe[offset:offset+size],rva,LOADER_RVA)
    if callers != sorted(KNOWN):
        raise ProofError("LOADER_CALLER_SET_CHANGED: "+",".join(hex(x) for x in callers))
    records=[]
    for src in callers:
        begin,end,context=KNOWN[src]
        if owning_function(src,funcs)!=(begin,end):
            raise ProofError("CALLER_PDATA_CHANGED: "+hex(src))
        records.append({"call_rva":f"0x{src:X}",
                        "function_begin_rva":f"0x{begin:X}",
                        "function_end_rva":f"0x{end:X}",
                        "context":context,"target_rva":f"0x{LOADER_RVA:X}"})
    return {"audit":"READ_ONLY_SHA_PINNED_DIRECT_CALLS","status":"PASS",
            "client_sha256":CLIENT_SHA,"target_rva":f"0x{LOADER_RVA:X}",
            "direct_caller_count":len(records),"callers":records,
            "conclusion":"Three static direct loader callers; runtime file path, Diamond UI event and ENC decode unproven.",
            "game_process_launched":False,"client_modified":False,
            "world_or_sql_modified":False}

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--client-zip",required=True,type=Path)
    ap.add_argument("--output",type=Path)
    args=ap.parse_args(argv)
    try:
        with zipfile.ZipFile(args.client_zip) as z:
            if sorted(z.namelist())!=["CabalMain.exe","meritsystem.enc"]:
                raise ProofError("UNEXPECTED_ZIP_MEMBERS")
            if z.testzip() is not None:
                raise ProofError("BAD_ZIP_CRC")
            result=audit(z.read("CabalMain.exe"))
    except (ProofError,OSError,zipfile.BadZipFile,ValueError,struct.error) as exc:
        print("DIAMOND_CLIENT_LOADER_CALLERS=FAIL",exc,file=sys.stderr)
        return 2
    rendered=json.dumps(result,indent=2)+"\n"
    if args.output:
        args.output.write_text(rendered,encoding="utf-8")
    print(rendered,end="")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
