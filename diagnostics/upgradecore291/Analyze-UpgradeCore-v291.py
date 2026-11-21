#!/usr/bin/env python3
"""Offline comparison of v291 Upgrade Core, Perfect Core and Force Core captures.

No network, server, DB, patches or gameplay actions. Input logs stay private.
The result is a triage heuristic, NOT a validated game fix.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

KEYWORDS = {
    "crash": re.compile(r"sig(segv|abrt|bus|ill)|segmentation fault|core dump|assertion failed|fatal signal", re.I),
    "rejected": re.compile(r"invalid|mismatch|unknown|unregistered|refus|reject|bad packet|packet length", re.I),
    "disconnect": re.compile(r"disconnect|kick|close(d)? (socket|connection)|session.*terminat", re.I),
    "upgrade": re.compile(r"upgrad|perfect|enchant|core", re.I),
}

def load(path, expected):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or obj.get("case") != expected or obj.get("read_only") is not True:
        raise ValueError(f"{path}: invalid case or read-only collector format")
    return obj

def log_lines(doc):
    lines = []
    for row in doc.get("after", {}).get("files", []):
        if isinstance(row, dict):
            lines.extend(str(x) for x in row.get("matched_lines", []))
    lines.extend(str(x) for x in doc.get("docker_logs", {}).get("matched_lines", []))
    return lines

def core_delta(doc):
    def index(rows):
        return {row["path"]: (row.get("size"), row.get("mtime"))
                for row in rows if isinstance(row, dict) and "path" in row}
    before = index(doc.get("before", {}).get("corefiles", []))
    after = index(doc.get("after", {}).get("corefiles", []))
    return sum(1 for path, state in after.items() if before.get(path) != state)

def classify(doc):
    obs = doc.get("status", {}).get("world_observation", "")
    lines = log_lines(doc)
    counts = Counter({name: sum(bool(regex.search(x)) for x in lines)
                      for name, regex in KEYWORDS.items()})
    gaps = []
    if doc.get("before", {}).get("error"): gaps.append("initial logs unavailable")
    if doc.get("after", {}).get("error"): gaps.append("final logs unavailable")
    samples = doc.get("samples", [])
    if not samples or any("error" in s.get("snapshot", {}) for s in samples):
        gaps.append("incomplete process status observations")
    dumps = core_delta(doc)
    if obs in ("WORLD_PID_CHANGED_RESTART_POSSIBLE", "WORLD_NON_RUNNING_STATE_SEEN") or dumps:
        category = "WORLD_RESTART_OR_CRASH_SUSPECTED"
    elif obs == "WORLD_PROCESS_NOT_OBSERVED":
        category = "WORLD_STATUS_UNAVAILABLE"
    elif counts["rejected"] or counts["disconnect"]:
        category = "SERVER_LOG_REJECTION_OR_DISCONNECT_INDICATION"
    elif obs == "WORLD_PID_STABLE_IN_SAMPLES":
        category = "WORLD_STABLE_CLIENT_DISCONNECT_NOT_EXPLAINED"
    else:
        category = "INSUFFICIENT_EVIDENCE"
    return {"case": doc["case"], "observation": obs, "category": category,
            "new_or_changed_corefiles": dumps, "matching_log_lines_count": len(lines),
            "keyword_counts": dict(counts), "collection_gaps": gaps}

def interpret(trials):
    bad = [trials[k] for k in ("upgrade", "perfect")]
    force = trials["force-control"]
    if any(t["collection_gaps"] for t in trials.values()):
        return ("COLLECTION_INCOMPLETE", "Repair missing diagnostics in TEST VM; do not infer packet offsets.")
    if any(t["category"] == "WORLD_RESTART_OR_CRASH_SUSPECTED" for t in bad):
        return ("INSPECT_WORLD_CRASH", "Inspect WorldSvr crash/restart timestamps and symbolicate handler offline before patching.")
    if force["category"] == "WORLD_RESTART_OR_CRASH_SUSPECTED":
        return ("CONTROL_NOT_STABLE", "Resolve baseline WorldSvr instability first.")
    if all(t["category"] == "SERVER_LOG_REJECTION_OR_DISCONNECT_INDICATION" for t in bad) and force["category"] == "WORLD_STABLE_CLIENT_DISCONNECT_NOT_EXPLAINED":
        return ("NORMAL_UPGRADE_REJECTION_SUSPECTED", "Find exact rejection cause and valid failure-response path.")
    if all(t["category"] == "WORLD_STABLE_CLIENT_DISCONNECT_NOT_EXPLAINED" for t in bad) and force["category"] == "WORLD_STABLE_CLIENT_DISCONNECT_NOT_EXPLAINED":
        return ("NEEDS_PROTOCOL_TRACING", "Inspect authenticated LAB C2S request, WorldSvr handler and S2C response.")
    return ("MIXED_OR_INSUFFICIENT_EVIDENCE", "Correlate timestamps and compare with Force Core control.")

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--upgrade", type=Path, required=True)
    ap.add_argument("--perfect", type=Path, required=True)
    ap.add_argument("--force", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    trials = {k: classify(load(p, k)) for k, p in (
        ("upgrade", a.upgrade), ("perfect", a.perfect), ("force-control", a.force))}
    state, next_step = interpret(trials)
    result = {
        "overall": state, "next_step": next_step, "trials": trials,
        "limitations": [
            "This is offline process/log triage, not an actual gameplay test.",
            "Stable WorldSvr PID does not establish protocol compatibility.",
            "Incomplete/truncated logs may hide the error; no keywords is not proof of no error.",
            "Polling and dump discovery may miss rapid restarts and external core locations.",
            "No opcode or root cause is proven without trustworthy protocol/runtime evidence.",
        ],
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"overall": state, "next_step": next_step, "summary": str(a.out)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
