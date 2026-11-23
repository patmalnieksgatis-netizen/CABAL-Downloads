#!/usr/bin/env python3
"""Correlate Procmon file events with SHA-verified v291 Merit collector assets.

Only assesses path identity, opening and reading observations; never infers
successful decompression or Diamond gameplay. Reads previously exported files.
"""
import argparse
import json
from pathlib import Path, PureWindowsPath

from audit_procmon_merit_paths import parse_csv
from audit_merit_candidates import audit

def normalize_path(path):
    win = PureWindowsPath(path)
    if not win.is_absolute():
        raise ValueError("expected absolute Windows client root")
    return str(win).replace("/", "\\").casefold().rstrip("\\")

def correlate(procmon_csv, assets_zip, client_root):
    proc = parse_csv(procmon_csv)
    assets = audit(assets_zip)
    root = normalize_path(client_root)
    by_path = {}
    for candidate in assets["candidates"]:
        rel = candidate["path"].replace("/", "\\")
        full = root + "\\" + rel.casefold()
        if full in by_path:
            raise ValueError("duplicate case-insensitive asset path")
        by_path[full] = candidate
    observations = []
    for row in proc["matched_paths"]:
        full = str(PureWindowsPath(row["path"])).casefold()
        candidate = by_path.get(full)
        classification = ("opened_and_read" if row["open_success"] and row["read_success"]
                          else "opened" if row["open_success"]
                          else "read_observed_no_open_in_capture" if row["read_success"]
                          else "query_only" if row["query_success"]
                          else "failed_or_unresolved")
        observations.append({
            "path": row["path"],
            "pid": row["pid"],
            "classification": classification,
            "procmon_open_success": row["open_success"],
            "procmon_read_success": row["read_success"],
            "procmon_query_success": row["query_success"],
            "matches_collected_asset": candidate is not None,
            "asset_sha256": candidate["sha256"] if candidate is not None else None,
            "asset_size": candidate["size"] if candidate is not None else None,
            "v11_candidate_codec_success": candidate["success"] if candidate is not None else None,
            "v11_candidate_codec_reason": candidate["reason"] if candidate is not None else None,
            "note": ("Path-only match: cannot prove file bytes were unchanged at runtime"
                     if candidate is not None else "Not among collected files; do not assume same bytes")
        })
    match = [x for x in observations if x["matches_collected_asset"] and
             x["classification"] in ("opened", "opened_and_read")]
    return {
        "mode": "READ_ONLY_PROCMON_TO_COLLECTED_ASSETS",
        "client_root": client_root,
        "procmon_log_sha256": proc["log_sha256"],
        "client_sha256": assets["client_sha256"],
        "candidate_count": len(assets["candidates"]),
        "observed_merit_path_count": len(observations),
        "confirmed_open_matching_collected_path_count": len(match),
        "observations": observations,
        "actual_runtime_byte_identity_proven": False,
        "resource_id_52_53_binding_proven": False,
        "actual_decode_success_proven": False,
        "diamond_gameplay_proven": False,
        "client_or_server_modified": False
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--procmon", type=Path, required=True)
    p.add_argument("--assets", type=Path, required=True)
    p.add_argument("--client-root", default=r"F:\CABAL_291_TEST")
    p.add_argument("--out", type=Path)
    args=p.parse_args()
    if args.out and args.out.exists():
        p.error("refusing to overwrite existing report")
    try:
        report=correlate(args.procmon,args.assets,args.client_root)
    except (OSError, ValueError, KeyError, RuntimeError) as e:
        p.error(str(e))
    result=json.dumps(report,indent=2,ensure_ascii=False)+"\n"
    if args.out: args.out.write_text(result,encoding="utf-8")
    else: print(result,end="")

if __name__=="__main__":
    main()
