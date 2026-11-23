#!/usr/bin/env python3
"""Read-only exact CABAL MeritSystem.scp grade gate.

A game-ready Diamond catalog requires independently verified protocol, session
and GameData persistence beyond this purely static SCP check. No mutations.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import zipfile

class CatalogError(ValueError): pass
REQUIRED_DIAMOND_GRADE=2
DIAMOND_RANK_WEXP=30000
EXCHANGE_ITEM=33554961
RANK_TICKET_COUNT=100

def extract_sections(raw:bytes):
    try: lines=raw.decode("utf-8-sig").splitlines()
    except UnicodeError as exc:raise CatalogError("SCP_NOT_UTF8") from exc
    sections={}
    current=None
    for line in lines:
        line=line.strip()
        if not line or line.startswith(("#",";","//")):continue
        if line.startswith("["):
            match=re.match(r"^\[([^\]]+)\](.*)$",line)
            if not match:raise CatalogError("BAD_SECTION_HEADER")
            name=match.group(1)
            if name in sections:raise CatalogError("DUPLICATE_SECTION_"+name)
            headings=match.group(2).split()
            sections[name]={"headings":headings,"rows":[]}
            current=name
            continue
        if current is None:raise CatalogError("ROW_BEFORE_SECTION")
        fields=line.split()
        expected=len(sections[current]["headings"])+1
        if len(fields)!=expected:
            raise CatalogError(f"ROW_FIELD_COUNT_{current}")
        if not fields[0].isdigit():
            raise CatalogError("ROW_INDEX_NOT_INTEGER")
        sections[current]["rows"].append(fields)
    return sections

def section_rows(sections,name,required):
    if name not in sections:raise CatalogError("MISSING_SECTION_"+name)
    section=sections[name]
    head=section["headings"]
    for key in required:
        if key not in head:raise CatalogError("MISSING_HEADER_"+key)
    if len(head)!=len(set(head)):raise CatalogError("DUPLICATE_HEADINGS")
    rows=[]
    ids=set()
    for fields in section["rows"]:
        idx=int(fields[0])
        if idx in ids:raise CatalogError("DUPLICATE_RECORD_INDEX_"+name)
        ids.add(idx)
        row=dict(zip(head,fields[1:]))
        rows.append(row)
    return rows

def parse_int(value,field):
    if not re.fullmatch(r"\d+",value):raise CatalogError("NON_INTEGER_"+field)
    return int(value)

def audit(raw:bytes):
    sections=extract_sections(raw)
    rows=section_rows(sections,"MeritMastery_Base",
                      ("Badge_Grade","Mastery_Index","Mastery_Category"))
    counts=Counter()
    mastery_ids=set()
    for row in rows:
        grade=parse_int(row["Badge_Grade"],"Badge_Grade")
        mid=parse_int(row["Mastery_Index"],"Mastery_Index")
        if mid in mastery_ids:raise CatalogError("DUPLICATE_MASTERY_ID")
        mastery_ids.add(mid)
        counts[grade]+=1
    upgrades=section_rows(sections,"UpGrade_Material",
                          ("Badge_Grade","Wexp","Need_Item","Need_Count"))
    upgrade_options=[]
    for row in upgrades:
        option={k:parse_int(row[k],k) for k in ("Badge_Grade","Wexp","Need_Item","Need_Count")}
        upgrade_options.append(option)
    grade2_rows=counts.get(REQUIRED_DIAMOND_GRADE,0)
    matching=[v for v in upgrade_options
              if v["Badge_Grade"]==REQUIRED_DIAMOND_GRADE
              and v["Wexp"]==DIAMOND_RANK_WEXP
              and v["Need_Item"]==EXCHANGE_ITEM
              and v["Need_Count"]==RANK_TICKET_COUNT]
    has_config_candidate=bool(grade2_rows and matching)
    return {
        "source_sha256":hashlib.sha256(raw).hexdigest(),
        "mode":"READ_ONLY_SCP_STATIC_AUDIT",
        "mastery_row_count":len(rows),
        "mastery_grade_counts":{str(k):v for k,v in sorted(counts.items())},
        "upgrade_material":upgrade_options,
        "diamond_mastery_rows":grade2_rows,
        "diamond_rank_upgrade_matching_30000_wexp_100_item_33554961":bool(matching),
        "diamond_config_candidate":has_config_candidate,
        "installable_product_confirmed":False,
        "status":"CONFIG_CANDIDATE_ONLY" if has_config_candidate else "BLOCKED_BY_SCP",
        "gameplay_proven":False,
        "live_sql_or_game_modified":False,
    }

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources-zip",type=Path,required=True)
    parser.add_argument("--require-candidate",action="store_true",
                        help="exit nonzero when grade-2 definitions/upgrade absent")
    args=parser.parse_args(argv)
    with zipfile.ZipFile(args.sources_zip) as z:
        names=[x for x in z.namelist() if x.replace("\\","/").endswith(
            "/server/active-v291/MeritSystem.scp")]
        # ZIP may have backslash entries without an initial slash.
        if not names:
            names=[x for x in z.namelist() if x.replace("\\","/")==
                   "server/active-v291/MeritSystem.scp"]
        if len(names)!=1 or z.testzip() is not None:
            raise CatalogError("EXPECTED_ONE_VALID_ACTIVE_SCP")
        result=audit(z.read(names[0]))
    print(json.dumps(result,indent=2))
    return 2 if args.require_candidate and not result["diamond_config_candidate"] else 0

if __name__=="__main__":
    raise SystemExit(main())
