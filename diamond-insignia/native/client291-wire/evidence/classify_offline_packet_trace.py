#!/usr/bin/env python3
"""Read-only CABAL v291 Merit/Dimension frame trace classifier.

Input: one frame per line: C2S|S2C followed by whitespace and hex bytes.
No network, process memory, VM, SQL or mutation. Classification is intentionally
NOT an assertion that any frame represents a Diamond purchase.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MAGIC = bytes.fromhex("e2 b7")
KNOWN = {
    0x09F3: "MeritMasteryLvUp",
    0x09F9: "DimensionInventoryList",
    0x09FB: "DimensionInventoryExpend",
    0x09FD: "DimensionInventoryMoveProcess",
}
HEX_LINE = re.compile(r"^\s*(C2S|S2C)\s+((?:[0-9a-fA-F]{2}[\s:]*)+)\s*$", re.I)


def classify(direction: str, frame: bytes) -> dict:
    record = {"direction": direction.upper(), "actual_bytes": len(frame)}
    if len(frame) < 6:
        return {**record, "classification": "invalid", "reason": "short_header"}
    if frame[:2] != MAGIC:
        return {**record, "classification": "invalid", "reason": "bad_magic"}
    declared = int.from_bytes(frame[2:4], "little")
    record["declared_bytes"] = declared
    if declared != len(frame):
        return {**record, "classification": "invalid", "reason": "length_mismatch"}
    opcode_at = 8 if direction.upper() == "C2S" else 4
    if len(frame) < opcode_at + 2:
        return {**record, "classification": "invalid", "reason": "short_opcode"}
    opcode = int.from_bytes(frame[opcode_at:opcode_at + 2], "little")
    record["opcode"] = f"0x{opcode:04X}"
    record["known_handler"] = KNOWN.get(opcode, "unverified")
    if opcode != 0x09F3:
        return {**record, "classification": "other_opcode", "diamond_confirmed": False}
    if direction.upper() == "C2S":
        if len(frame) != 18:
            return {**record, "classification": "unexpected_merit_c2s_length", "diamond_confirmed": False}
        record["transport_field"] = int.from_bytes(frame[4:8], "little")
        record["state118_raw"] = int.from_bytes(frame[10:14], "little")
        record["state11C_raw"] = int.from_bytes(frame[14:18], "little")
        return {**record, "classification": "merit_c2s_shape_verified", "diamond_confirmed": False}
    if len(frame) < 7:
        return {**record, "classification": "invalid", "reason": "short_merit_status"}
    record["status_byte"] = frame[6]
    if frame[6] != 1:
        classification = "merit_s2c_non_success_status"
    elif len(frame) == 7:
        classification = "merit_s2c_7b_route_unobserved"
    elif len(frame) >= 11:
        classification = "merit_s2c_11plus_semantics_unverified"
        record["payload_dword_plus7_raw"] = int.from_bytes(frame[7:11], "little")
    else:
        classification = "merit_s2c_8_to_10b_unknown"
    return {**record, "classification": classification, "diamond_confirmed": False}


def parse_line(line: str, lineno: int) -> dict | None:
    if not line.strip() or line.lstrip().startswith("#"):
        return None
    match = HEX_LINE.fullmatch(line)
    if not match:
        return {"line": lineno, "classification": "invalid", "reason": "line_syntax"}
    direction, raw = match.groups()
    data = bytes.fromhex(raw.replace(":", " "))
    return {"line": lineno, **classify(direction, data)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path, help="read-only text file: C2S|S2C hex")
    args = parser.parse_args(argv)
    with args.trace.open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            record = parse_line(line, lineno)
            if record is not None:
                print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
