#!/usr/bin/env python3
"""Read-only Procmon CSV audit for CABAL v291 Merit file access.

Works on an existing user-exported Process Monitor CSV. Does not attach to or
launch the client, install drivers, inspect memory, alter Windows, or write game files.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path, PureWindowsPath

TARGETS = {"meritsystem.enc", "meritsystem_msg.enc"}
OPEN_EVENTS = {"CreateFile", "QueryOpen"}
READ_EVENTS = {"ReadFile"}
MAX_LOG_BYTES = 100 * 1024 * 1024
MAX_ROWS = 800000
MAX_PATH = 4096

def norm(s):
    return (s or "").strip().casefold()

def is_target(p):
    if not isinstance(p, str) or not p or len(p) > MAX_PATH:
        return False
    return PureWindowsPath(p).name.casefold() in TARGETS

def parse_csv(path):
    if path.stat().st_size > MAX_LOG_BYTES:
        raise ValueError("oversized Procmon CSV")
    observations = {}
    total = 0
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as stream:
        reader = csv.DictReader(stream)
        required = {"Process Name", "Operation", "Path", "Result"}
        if not required.issubset(reader.fieldnames or ()):
            raise ValueError("not a supported Process Monitor CSV export")
        for row in reader:
            total += 1
            if total > MAX_ROWS:
                raise ValueError("too many log rows")
            if norm(row.get("Process Name")) != "cabalmain.exe":
                continue
            operation = (row.get("Operation") or "").strip()
            if operation not in OPEN_EVENTS | READ_EVENTS:
                continue
            filename = (row.get("Path") or "").strip()
            if not is_target(filename):
                continue
            status = (row.get("Result") or "").strip()
            pid = (row.get("PID") or "").strip()
            key = (pid, filename.casefold())
            item = observations.setdefault(key, {
                "pid": pid or "UNKNOWN", "path": filename,
                "open_success": 0, "read_success": 0,
                "open_failure": 0, "read_failure": 0,
                "first_time": (row.get("Time of Day") or "").strip()
            })
            ok = norm(status) == "success"
            kind = "open" if operation in OPEN_EVENTS else "read"
            item[kind + ("_success" if ok else "_failure")] += 1
    results = sorted(observations.values(), key=lambda x: (x["pid"], x["path"].casefold()))
    confirmed = [x for x in results if x["open_success"]]
    read = [x for x in results if x["read_success"]]
    return {
        "mode": "READ_ONLY_PROCMON_CSV",
        "log_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "total_rows": total,
        "matched_paths": results,
        "opened_path_count": len(confirmed),
        "read_path_count": len(read),
        "opened_by_cabalmain": [x["path"] for x in confirmed],
        "read_by_cabalmain": [x["path"] for x in read],
        "not_proven": [
            "which resource ID triggered any particular open",
            "whether a successful file read produced a valid decoded Merit resource",
            "Diamond UI, C2S opcode, gameplay or persistence"
        ],
        "game_files_modified": False,
        "game_process_modified": False
    }

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", type=Path, help="existing CSV exported from Process Monitor")
    ap.add_argument("--output", type=Path, help="new JSON output; refuses overwrite")
    args = ap.parse_args()
    try:
        if args.output and args.output.exists():
            raise ValueError("refuse to overwrite existing report")
        data = parse_csv(args.csv)
        report = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(report, encoding="utf-8")
        else:
            print(report, end="")
    except (ValueError, OSError, csv.Error) as e:
        ap.exit(2, "AUDIT_FAILED: " + str(e) + "\n")

if __name__ == "__main__":
    main()
