#!/usr/bin/env python3
"""Analyze a locally captured *single* decoded CABAL opcode 951 header.

Read-only. It does not mutate/send/replay packets, game state or executables.
A candidate moved field is a hypothesis, not sufficient proof for patching.
Usage:
  python3 Analyze-Opcode951-Header.py --declared 151 --hex '...'
"""
import argparse
import json
import re
import struct
from pathlib import Path

BASE = 139
LEGACY_COUNT_OFF = 0x11
MAX_ESCAPE = 0x209

def analyze_header(declared, packet):
    observations = []
    if len(packet) < 19:
        return {"error": "header_too_short", "captured_bytes": len(packet)}
    actual_declared = struct.unpack_from("<H",packet,2)[0]
    core_count = packet[0x10]
    legacy_count = struct.unpack_from("<H",packet,0x11)[0]
    main_slot = struct.unpack_from("<H",packet,0x0e)[0]
    valid_legacy = (
        declared == actual_declared and
        declared == BASE + 2*legacy_count and
        legacy_count <= MAX_ESCAPE and
        1 <= core_count <= 60 and
        main_slot <= MAX_ESCAPE
    )
    expected_count = (declared-BASE)//2 if declared>=BASE and (declared-BASE)%2==0 else None
    if expected_count is not None and expected_count<=MAX_ESCAPE:
        for off in range(0x0e,min(len(packet)-1,0x31)):
            count=struct.unpack_from("<H",packet,off)[0]
            if count == expected_count:
                observations.append({"candidate_offset":hex(off),
                                     "count":count,
                                     "delta_from_legacy":off-LEGACY_COUNT_OFF})
    if valid_legacy:
        status = "LEGACY_951_HEADER_COMPATIBLE"
        note="Full packet length and later item authorization still require actual server validation."
    elif expected_count is None:
        status="FIXED_SIZE_OR_LAYOUT_MISMATCH"
        note="Length does not match any 139+2N body; do not spoof count or trim data."
    elif not observations:
        status="NO_COUNT_FIELD_AT_EXPECTED_VALUE_IN_CAPTURED_HEADER"
        note="Could be a new body format or a different length definition; no safe automatic patch."
    elif len(observations)==1:
        status="ONE_POSSIBLE_SHIFTED_COUNT_FIELD"
        note="One candidate matches length formula, but the whole structure must be mapped before patching."
    else:
        status="AMBIGUOUS_COUNT_FIELD_CANDIDATES"
        note="Several fields match the length-derived count; need source-side layout evidence."
    return {
        "status":status,"declared":declared,"header_declared":actual_declared,
        "legacy_escape_count":legacy_count,"legacy_expected_len":BASE+2*legacy_count,
        "core_count":core_count,"legacy_main_slot":main_slot,
        "length_implied_count":expected_count,"count_field_candidates":observations,
        "note":note
    }

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--declared",type=int,required=True)
    a.add_argument("--hex",required=True,dest="header_hex")
    a.add_argument("--out",type=Path,default=None)
    x=a.parse_args()
    packet=bytes.fromhex(re.sub(r"[^a-fA-F0-9]","",x.header_hex))
    result=analyze_header(x.declared,packet)
    if x.out:
        import os
        os.umask(0o077)
        x.out.write_text(json.dumps(result,indent=2),encoding="utf-8")
        x.out.chmod(0o600)
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
