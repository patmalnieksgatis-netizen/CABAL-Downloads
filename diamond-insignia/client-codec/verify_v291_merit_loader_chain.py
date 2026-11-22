#!/usr/bin/env python3
"""Verify exact v291 Merit ID->path->loader control flow from V5/V6/V11 reports.

Read-only; requires owner-produced SHA-pinned JSON/ZIP exports. No game process.
"""
import argparse
import json
import re
import struct
import zipfile
from pathlib import Path

EXE_SHA="52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9"
ENC_SHA="3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a"
FILES={5:"MERIT_X64_V5_REPORT.json",6:"MERIT_X64_V6_REPORT.json",11:"MERIT_X64_V11_REPORT.json"}

def load(path,version):
    if path.stat().st_size>512000: raise ValueError("oversized report")
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            if len(z.infolist())>8: raise ValueError("too many ZIP entries")
            info=z.getinfo(FILES[version])
            if info.file_size>1000000: raise ValueError("oversized JSON entry")
            raw=z.read(info)
    else: raw=path.read_bytes()
    j=json.loads(raw)
    if j.get("schema")!=version: raise ValueError("wrong schema")
    if j.get("exe_sha256")!=EXE_SHA or j.get("merit_enc_sha256")!=ENC_SHA:
        raise ValueError("wrong client identity")
    for k in ("game_launched","process_memory_read","sql_or_vm_access","client_modified"):
        if j.get(k) is not False: raise ValueError("unsafe report marker "+k)
    return j

def function(report,field,name):
    m=[x for x in report[field] if x["name"]==name]
    if len(m)!=1: raise ValueError("missing or ambiguous function "+name)
    f=m[0]
    if f.get("classification")!="PDATA_BOUNDED_FUNCTION" or f.get("pdata_range_proven") is not True:
        raise ValueError("unverified function PDATA")
    a,b=int(f["function_begin_rva"],16),int(f["function_end_rva"],16)
    raw=f.get("leading_bytes_hex","")
    if not re.fullmatch(r"[0-9a-fA-F]+",raw) or len(raw)%2:
        raise ValueError("invalid function hex")
    body=bytes.fromhex(raw)
    if b<=a or len(body)!=b-a or f.get("total_bytes")!=len(body):
        raise ValueError("function truncated")
    return a,body

def instr(fn,at,expected):
    a,body=fn
    i=at-a
    exp=bytes.fromhex(expected)
    if i<0 or i+len(exp)>len(body) or body[i:i+len(exp)]!=exp:
        raise ValueError("instruction mismatch at 0x%x"%at)

def call(fn,at,target):
    a,body=fn
    i=at-a
    if i<0 or i+5>len(body) or body[i]!=0xe8:
        raise ValueError("missing CALL at 0x%x"%at)
    displacement=struct.unpack_from("<i",body,i+1)[0]
    if at+5+displacement!=target:
        raise ValueError("wrong CALL target at 0x%x"%at)

def verify(v5,v6,v11):
    w=function(v5,"functions","selector_wrapper")
    entry=function(v6,"targets","indexed_path_wrapper_caller")
    loader=function(v11,"targets","enc_file_loader")
    # The path selector does not modify the file contents. ID->path branch only.
    call(w,0x21cc2a,0x21d938)
    instr(w,0x21cc34,"84c0")
    instr(w,0x21cc90,"ff15625d9100") # SHLWAPI!PathFileExistsA
    call(w,0x21cca6,0x217244) # Language fallback
    call(w,0x21ccfa,0x216fac) # Data/default path
    call(entry,0x21cdc6,0x21cbd4)
    call(entry,0x21cde6,0x2178e0)
    instr(entry,0x21cdce,"4883781810") # string SSO pointer check
    instr(entry,0x21cdd8,"488bd3") # 16-byte resource-index stride follows
    instr(entry,0x21cddb,"48c1e204")
    instr(entry,0x21cde2,"4c8d4208") # output length member address
    instr(loader,0x21793f,"ff1593ac9100") # SetFilePointer at file end
    instr(loader,0x21794b,"83e804") # tail offset = size - 4
    instr(loader,0x217975,"ff15f5ab9100") # ReadFile length DWORD
    instr(loader,0x217987,"ff154bac9100") # set offset 4
    instr(loader,0x2179c7,"488d4804") # mapped input + 4
    instr(loader,0x2179d0,"48634d00") # allocation based on trailing DWORD
    call(loader,0x217a17,0x2b7fac)
    return {
        "status":"STATIC_CALL_CHAIN_PASS",
        "exact_client_sha256":EXE_SHA,
        "verified_resource_selector_branches":2,
        "shared_file_loader_rva":"0x2178e0",
        "resource_index_stride_bytes":16,
        "loader_input_pointer":"mapped_file_plus_4",
        "loader_output_size_source":"last_4_bytes_of_file",
        "actual_runtime_file_path_proven":False,
        "actual_loaded_file_matches_collected_assets":False,
        "diamond_ui_packet_proven":False,
        "game_or_server_modified":False,
        "caveat":"Static code proves an available route, not observed runtime execution."
    }

def main():
    ap=argparse.ArgumentParser()
    for k in ("v5","v6","v11"): ap.add_argument("--"+k,type=Path,required=True)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    result=verify(load(args.v5,5),load(args.v6,6),load(args.v11,11))
    output=json.dumps(result,indent=2)+"\n"
    if args.out:
        if args.out.exists(): raise SystemExit("REFUSE_OVERWRITE")
        args.out.write_text(output,encoding="utf-8")
    else: print(output,end="")
if __name__=="__main__":main()
