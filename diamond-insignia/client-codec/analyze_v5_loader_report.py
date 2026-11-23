#!/usr/bin/env python3
"""Offline verifier for V5 reports; no live client or server access."""
import argparse,json,zipfile
from pathlib import Path
EXE_SHA="52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9"
ENC_SHA="3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a"

def validate(d):
 if d.get("schema")!=5 or d.get("mode")!="READ_ONLY_X64_MERIT_LOADER_CALL_GRAPH":
  raise ValueError("V5_UNEXPECTED_REPORT_SCHEMA")
 if d.get("exe_sha256")!=EXE_SHA or d.get("merit_enc_sha256")!=ENC_SHA:
  raise ValueError("V5_SOURCE_SHA_MISMATCH")
 if any(d.get(k) is not False for k in ("game_launched","process_memory_read","sql_or_vm_access","client_modified")):
  raise ValueError("V5_UNSAFE_FLAGS")
 funcs={x["name"]:x for x in d["functions"]}
 if set(funcs)!={"selector_wrapper","selector_posthelper"}:
  raise ValueError("V5_MISSING_TARGET_FUNCTION")
 w=funcs["selector_wrapper"];helper=funcs["selector_posthelper"]
 if (int(w["function_begin_rva"],16),int(w["function_end_rva"],16))!=(0x21cbd4,0x21cda4):
  raise ValueError("V5_WRAPPER_ADDRESS_CHANGED")
 if not int(helper["function_begin_rva"],16)<=0x21d938<int(helper["function_end_rva"],16):
  raise ValueError("V5_HELPER_NOT_IN_FUNCTION")
 b=bytes.fromhex(w["leading_bytes_hex"])
 if len(b)!=w["total_bytes"] or not w["code_complete"]:
  raise ValueError("V5_WRAPPER_TRUNCATED")
 for site,target,expected in ((0x21cc08,0x21bb98,"e88befffff"),(0x21cc2a,0x21d938,"e8090d0000")):
  call=b[site-0x21cbd4:site-0x21cbd4+5]
  if call.hex()!=expected or call[0]!=0xe8:
   raise ValueError("V5_CALL_INSTRUCTION_CHANGED")
  displacement=int.from_bytes(call[1:],byteorder="little",signed=True)
  if site+5+displacement!=target:raise ValueError("V5_RELATIVE_TARGET_CHANGED")
 candidates=d["raw_e8_e9_candidate_count"]
 if not isinstance(candidates,int) or candidates<0 or candidates<len(d["exported_contexts"]):
  raise ValueError("V5_CANDIDATE_COUNT_INVALID")
 return {"status":"X64_V5_REPORT_VERIFIED","wrapper_rva":"0x21cbd4",
         "helper_target_rva":"0x21d938",
         "helper_function_begin":helper["function_begin_rva"],
         "helper_function_end":helper["function_end_rva"],
         "helper_code_complete":helper["code_complete"],
         "iat_0xb329f8":d.get("import_slot_name_candidates",{}).get("iat_slot_0xb329f8"),
         "iat_0xb32c28":d.get("import_slot_name_candidates",{}).get("iat_slot_0xb32c28"),
         "raw_e8_e9_candidates":candidates,"codec_confirmed":False,
         "diamond_opcode_confirmed":False}

if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("v5_report_zip",type=Path);args=a.parse_args()
 with zipfile.ZipFile(args.v5_report_zip) as z:
  d=json.loads(z.read("MERIT_X64_V5_REPORT.json"))
 print(json.dumps(validate(d),indent=2))
