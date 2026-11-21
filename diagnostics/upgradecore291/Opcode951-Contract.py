#!/usr/bin/env python3
"""Verified legacy WorldSvr opcode-951 *header* contract, offline only.

Grounded in exact native SHA caec7772... static disassembly at 0x7AC0F0:
 length must equal 0x8B + 2*escapeSlotCount, escape count <=0x209;
 coreSlotCount in [1, 60]; main slot <=0x209.
This is not a protocol conversion, not a patch, and not client v291 proof.
"""
import struct

MIN_LEN = 0x8B
MAX_SLOTS = 0x209
MAX_CORES = 60

def read_shape(payload):
    if len(payload)<0x13:
        return {"valid":False,"reasons":["shorter_than_19_byte_header"]}
    declared=struct.unpack_from("<H",payload,0x02)[0]
    main_slot=struct.unpack_from("<H",payload,0x0E)[0]
    cores=payload[0x10]
    escapes=struct.unpack_from("<H",payload,0x11)[0]
    expected=MIN_LEN+2*escapes
    reasons=[]
    if declared!=expected:reasons.append("declared_length_mismatch")
    if len(payload)!=declared:reasons.append("captured_length_mismatch")
    if escapes>MAX_SLOTS:reasons.append("escape_slot_count_invalid")
    if not 1<=cores<=MAX_CORES:reasons.append("core_slot_count_invalid")
    if main_slot>MAX_SLOTS:reasons.append("main_slot_invalid")
    return {"valid":not reasons,"reasons":reasons,
            "declared_packet_length":declared,"captured_length":len(payload),
            "expected_packet_length":expected,"escape_slot_count":escapes,
            "core_slot_count":cores,"main_slot":main_slot}
