#!/usr/bin/env python3
"""Read-only analysis of user's actual v291 static client-scan JSON ZIP.
Pattern matches alone do not prove a Merit decoder or Diamond support."""
import argparse
import collections
import hashlib
import json
import zipfile
from pathlib import Path

CLIENT_SHA = {
 "bin\\x64\\cabalmain.exe":"52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9",
 "bin\\x86\\cabalmain.exe":"7f0aa64333d5c8e1e48c1e8e8512e45b6ea91ce3efee23d8cb7dbbc63f1feb26",
}
ENC_SHA = "3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a"

def analyze(report):
 if report.get("mode")!="READ_ONLY_STATIC" or report.get("schema")!=1:
  raise ValueError("SOURCE_REPORT_MODE_OR_VERSION_INVALID")
 if any(report.get(k) is not False for k in ("game_launched","game_memory_read","file_changes","account_data_read")):
  raise ValueError("REPORT_RECORDED_UNSAFE_ACTION")
 files={f["relative_path"].lower():f for f in report["files_scanned"]}
 for name,sha in CLIENT_SHA.items():
  if name not in files or files[name].get("sha256")!=sha or files[name].get("status")!="STATIC_SCANNED":
   raise ValueError("EXACT_CLIENT_BINARY_MISSING_OR_CHANGED: "+name)
 enc=next((x for x in report["existing_enc_files"] if x["relative_path"].lower()=="data\\meritsystem.enc"),None)
 if not enc or enc["sha256"]!=ENC_SHA:
  raise ValueError("SOURCE_MERIT_ENC_HASH_CHANGED")
 counts=collections.Counter(h["Pattern"] for f in files.values() for h in f.get("hits",[]))
 vendor=[]
 for f in files.values():
  for h in f.get("hits",[]):
   if h["Pattern"] not in ("ASCII_DIAMOND_TITLE","ASCII_INSIGNIA"):
    continue
   txt=bytes.fromhex(h["ContextHex"]).decode("latin1")
   if not any(name in txt for name in ("Diamond Computer Systems","Diamond Lane Comm.","Insignia Solutions")):
    raise ValueError("POTENTIALLY_NEW_DIAMOND_HIT_REQUIRE_MANUAL_REVIEW")
   vendor.append({"file":f["relative_path"],"offset":h["Offset"],"pattern":h["Pattern"]})
 return {
  "status":"STATIC_REPORT_VERIFIED_NO_DECODER_OR_OPCODE_PROVEN",
  "files_scanned":len(files),
  "cabalmain_merit_string_offsets": {
    files[name]["relative_path"]:[
       h["Offset"] for h in files[name]["hits"] if h["Pattern"]=="ASCII_MERITSYSTEM_LOWER"
    ] for name in CLIENT_SHA
  },
  "v291_merit_encoded_bytes":enc["bytes"],
  "v291_merit_declared_xml_bytes":enc["declared_unpacked_bytes"],
  "classic_key_exact_hits":sum(v for k,v in counts.items() if "CLASSIC" in k),
  "short_xor_byte_pattern_hits_not_proof":sum(v for k,v in counts.items() if k.startswith("X86_XOR_AL_")),
  "unrelated_graphics_vendor_diamond_insignia_hits":vendor,
  "xrefs_identified":False,
  "worldsvr_diamond_opcode_identified":False,
  "codec_identified":False,
  "next":"hash-pinned read-only PE Merit-string xref scan; no server changes"
 }

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("source_zip",type=Path)
 p.add_argument("--out",type=Path)
 a=p.parse_args()
 with zipfile.ZipFile(a.source_zip) as z:
  report=json.loads(z.read("CLIENT_CODEC_STATIC_REPORT.json"))
 result=json.dumps(analyze(report),ensure_ascii=False,indent=2)+"\n"
 if a.out:a.out.write_text(result,encoding="utf-8")
 print(result)
