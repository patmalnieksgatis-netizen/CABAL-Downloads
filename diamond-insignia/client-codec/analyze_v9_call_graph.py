#!/usr/bin/env python3
"""V10 read-only disassembly of exact V9 extracted x64 function bytes."""
import argparse, hashlib, json, re, shutil, subprocess, tempfile, zipfile
from pathlib import Path

CLIENT = "52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9"
MERIT = "3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a"
TARGETS = {"buffer_processing_step":0x2b8004,"buffer_copy_like_callee":0xa37890,
           "linked_buffer_free_callee":0xa6be2c}

def read_report(path):
    if path.stat().st_size > 250000: raise ValueError("oversized input")
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names=z.namelist()
            if len(names)!=len(set(names)) or set(names)!={"MERIT_X64_V9_REPORT.json","README.txt"}:
                raise ValueError("unexpected ZIP entries")
            if z.getinfo("MERIT_X64_V9_REPORT.json").file_size>200000:
                raise ValueError("oversized report")
            raw=z.read("MERIT_X64_V9_REPORT.json")
    else: raw=path.read_bytes()
    return json.loads(raw)

def addr(v):
    if not isinstance(v,str) or not re.fullmatch(r"0x[0-9a-fA-F]+",v):
        raise ValueError("invalid RVA")
    return int(v,16)

def body_bytes(v,limit):
    if not isinstance(v,str) or len(v)%2 or len(v)>limit*2 or not re.fullmatch("[0-9a-fA-F]*",v):
        raise ValueError("invalid/big byte body")
    return bytes.fromhex(v)

def validate(report):
    if report.get("schema")!=9 or report.get("mode")!="READ_ONLY_X64_MERIT_PROCESSING_STEP_CALLEES":
        raise ValueError("wrong report schema/mode")
    if report.get("exe_sha256")!=CLIENT or report.get("merit_enc_sha256")!=MERIT:
        raise ValueError("source hash mismatch")
    for field in ("game_launched","process_memory_read","sql_or_vm_access","client_modified",
                  "actual_merit_decoder_proven","diamond_opcode_proven"):
        if report.get(field) is not False: raise ValueError("wrong safety marker: "+field)
    targets=report.get("targets")
    if not isinstance(targets,list) or len(targets)!=3: raise ValueError("wrong target count")
    result=[]
    for t in targets:
        name=t.get("name")
        if name not in TARGETS or name in [v["name"] for v in result]: raise ValueError("duplicate/unknown name")
        if addr(t.get("requested_rva"))!=TARGETS[name]: raise ValueError("wrong target RVA")
        classification=t.get("classification")
        if classification=="PDATA_BOUNDED_FUNCTION":
            begin,end=addr(t.get("function_begin_rva")),addr(t.get("function_end_rva"))
            if t.get("pdata_range_proven") is not True or not begin<=TARGETS[name]<end:
                raise ValueError("unproven boundaries")
            blob=body_bytes(t.get("leading_bytes_hex"),8192)
            complete=t.get("code_complete") is True
            if complete and (len(blob)!=end-begin or t.get("total_bytes")!=len(blob)):
                raise ValueError("incomplete marked as complete")
            if not complete and t.get("total_bytes",0)<len(blob): raise ValueError("bad partial length")
        elif classification=="RAW_CALL_TARGET_NO_PDATA_ENTRY":
            begin=addr(t.get("raw_window_start_rva"))
            end=None
            blob=body_bytes(t.get("raw_window_hex"),2048)
            complete=False
            if begin!=TARGETS[name] or len(blob)!=2048 or t.get("pdata_range_proven") is not False:
                raise ValueError("unsafe raw-window claim")
        else: raise ValueError("unknown target classification")
        result.append({"name":name,"begin":begin,"end":end,"blob":blob,"complete":complete,
                       "classification":classification})
    return result

def disassemble(item, objdump):
    with tempfile.TemporaryDirectory(prefix="diamond_v9_") as d:
        p=Path(d)/"bytes.bin";p.write_bytes(item["blob"])
        args=[objdump,"-D","-b","binary","-m","i386:x86-64","-M","intel",
              "--adjust-vma=0x%x"%item["begin"],str(p)]
        output=subprocess.run(args,check=True,capture_output=True,text=True,timeout=10).stdout
    calls=[]
    for line in output.splitlines():
        m=re.match(r"^\s*([0-9a-f]+):\s*(?:[0-9a-f]{2}\s+)+\s*call\s+(?:0x)?([0-9a-f]+)(?:\s|$)",line)
        if m: calls.append({"site_rva":"0x%x"%int(m.group(1),16),"target_rva":"0x%x"%int(m.group(2),16)})
    return output,calls

def inspect(report,objdump):
    items=validate(report)
    result={"mode":"READ_ONLY_STATIC_V9_CALL_GRAPH","client_sha256":CLIENT,
            "runtime_path_proven":False,"diamond_decoder_proven":False,
            "diamond_opcode_proven":False,"live_game_modified":False,"functions":[]}
    listing={}
    for item in items:
        text,calls=disassemble(item,objdump)
        listing[item["name"]]=text
        result["functions"].append({
            "name":item["name"],"start_rva":hex(item["begin"]),
            "end_rva":hex(item["end"]) if item["end"] else None,
            "classification":item["classification"],"complete":item["complete"],
            "byte_count":len(item["blob"]),"sha256":hashlib.sha256(item["blob"]).hexdigest(),
            "direct_calls":calls,
            "caution":"unproven full boundaries" if not item["complete"] else None})
    return result,listing

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report",type=Path)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists(): raise SystemExit("REFUSE_OVERWRITE_OUTPUT")
    objdump=shutil.which("objdump")
    if not objdump: raise SystemExit("GNU objdump missing")
    result,listing=inspect(read_report(args.report),objdump)
    args.out.mkdir(parents=True,exist_ok=False)
    (args.out/"V9_STATIC_CALL_GRAPH.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    for name,asm in listing.items():
        (args.out/(name+".asm.txt")).write_text(asm,encoding="utf-8")
    print("V9_STATIC_CALL_GRAPH=PASS;DIAMOND_DECODER=NOT_PROVEN")
if __name__=="__main__":main()
