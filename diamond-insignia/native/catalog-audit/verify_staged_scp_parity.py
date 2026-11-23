#!/usr/bin/env python3
"""Read-only, SHA-pinned active v291 -> staged Diamond SCP preservation gate.

No live SQL, VM, WorldSvr or SCP files are modified. This verifies configuration
row preservation ONLY, never playable Diamond or safe binary injection.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
from audit_real_merit_grade import audit, extract_sections, CatalogError

ACTIVE_SHA="307fc981ec3efe66f6cc1b0606ed7d86cd9e5a6e46205769a9bb34b012464295"
STAGED_SHA="26c9c4cbe3136f67f0298c8e412a4aa7620ba46d62b5c3950880fe821f2ee2e5"
ADDED_EXPECTED={
    "MeritMastery_Base":316,
    "MeritMastery_Value":1096,
    "UpGrade_Material":1,
    "SlotOpen_Material":616,
    "SlotOpen_Time":308,
    "SpecialMastery_Material":1,
    "SpecialMastery_Value":100,
    "SpecialMastery_Active":4,
}
BASE_MEMBER="server/active-v291/MeritSystem.scp"
STAGE_MEMBER="MeritSystem.DIAMOND_STAGED_DO_NOT_INSTALL.scp"

def compare_scp(active:bytes,staged:bytes,check_sha:bool=True)->dict:
    hashes={"active_sha256":hashlib.sha256(active).hexdigest(),
            "staged_sha256":hashlib.sha256(staged).hexdigest()}
    if check_sha and (hashes["active_sha256"]!=ACTIVE_SHA or
                      hashes["staged_sha256"]!=STAGED_SHA):
        raise CatalogError("EXACT_ACTIVE_OR_STAGED_SHA_MISMATCH")
    old=extract_sections(active); new=extract_sections(staged)
    if list(old)!=list(new):
        raise CatalogError("SECTION_LIST_OR_ORDER_CHANGED")
    changed={}
    for name in old:
        before,after=old[name],new[name]
        if before["headings"]!=after["headings"]:
            raise CatalogError("HEADER_CHANGED_"+name)
        if before["rows"]!=after["rows"][:len(before["rows"])]:
            raise CatalogError("ACTIVE_ROWS_MODIFIED_"+name)
        added=len(after["rows"])-len(before["rows"])
        if added!=ADDED_EXPECTED.get(name,0):
            raise CatalogError(f"UNEXPECTED_ADDED_ROWS_{name}_{added}")
        if added:changed[name]=added
    staged_audit=audit(staged)
    if (staged_audit["diamond_mastery_rows"]!=316 or
        not staged_audit["diamond_rank_upgrade_matching_30000_wexp_100_item_33554961"]):
        raise CatalogError("DIAMOND_STAGED_CONFIG_INCOMPLETE")
    active_audit=audit(active)
    if active_audit["diamond_config_candidate"]:
        raise CatalogError("ACTIVE_BASELINE_NOT_PLATINUM_ONLY")
    if sum(changed.values())!=2442:
        raise CatalogError("UNEXPECTED_TOTAL_ADDITIONS")
    return {**hashes,"status":"STATIC_STAGED_SCP_PARITY_PASS",
            "sections_preserved":len(old),
            "old_mastery_count":active_audit["mastery_row_count"],
            "staged_mastery_count":staged_audit["mastery_row_count"],
            "grade_2_mastery_rows":staged_audit["diamond_mastery_rows"],
            "added_row_counts":changed,
            "added_rows_total":sum(changed.values()),
            "original_rows_all_preserved":True,
            "confirmed_gameplay":False,
            "world_server_integration":False,
            "live_assets_modified":False}

def read_member(archive:Path,member:str)->bytes:
    with zipfile.ZipFile(archive) as z:
        selected=[name for name in z.namelist() if name.replace("\\","/")==member]
        if len(selected)!=1 or z.testzip() is not None:
            raise CatalogError("EXPECTED_ONE_VALID_SCP_MEMBER")
        return z.read(selected[0])

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--active-zip",type=Path,required=True)
    p.add_argument("--staged-zip",type=Path,required=True)
    args=p.parse_args(argv)
    report=compare_scp(read_member(args.active_zip,BASE_MEMBER),
                       read_member(args.staged_zip,STAGE_MEMBER))
    print(json.dumps(report,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
