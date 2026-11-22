#!/usr/bin/env python3
"""Offline, bounded audit of v291 Merit resource candidates from a collector ZIP.

Never infers a runtime-opened path from directory inventory. Never writes game files.
Only tests a specific, statically observed first-4-byte XOR + raw DEFLATE route.
"""
import argparse
import hashlib
import io
import json
import pathlib
import sys
import zipfile
import zlib

CLIENT_SHA = "52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9"
XOR4 = bytes.fromhex("92656757")
MAX_ENTRY = 4 * 1024 * 1024
MAX_OUTPUT = 8 * 1024 * 1024
MAX_FILES = 150

def inspect_payload(raw):
    info = {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "codec": "v11_loader_mapped_plus4_xor4_raw_deflate_trailer_length",
            "success": False, "reason": None}
    if len(raw) < 13 or len(raw) > MAX_ENTRY:
        info["reason"] = "invalid_input_size"
        return info
    expected = int.from_bytes(raw[-4:], "little")
    info["prefix_le32_observed"] = int.from_bytes(raw[:4], "little")
    info["loader_trailer_uncompressed_size"] = expected
    if expected < 1 or expected > MAX_OUTPUT:
        info["reason"] = "uncompressed_size_out_of_bounds"
        return info
    stream = bytearray(raw[4:-4])
    for i in range(4):
        stream[i] ^= XOR4[i]
    info["decoded_stream_first4"] = bytes(stream[:4]).hex()
    if (stream[0] >> 1) & 3 == 3:
        info["reason"] = "reserved_deflate_btype_3"
        return info
    try:
        dec = zlib.decompressobj(wbits=-15)
        result = dec.decompress(stream, expected + 1)
        if len(result) > expected or dec.unconsumed_tail:
            info["reason"] = "output_limit_or_unconsumed_input"
            return info
        tail = dec.flush()
        result += tail
        if not dec.eof or len(result) != expected or dec.unused_data:
            info["reason"] = "stream_not_exact_or_trailing_data"
            return info
    except zlib.error:
        info["reason"] = "invalid_deflate"
        return info
    info["success"] = True
    info["reason"] = "matching_observed_codec"
    info["output_size"] = len(result)
    info["output_sha256"] = hashlib.sha256(result).hexdigest()
    return info

def audit(archive):
    with zipfile.ZipFile(archive, "r") as z:
        entries = z.infolist()
        names = [x.filename for x in entries]
        if len(names) != len(set(names)):
            raise ValueError("duplicate ZIP member names")
        if "manifest.json" not in names:
            raise ValueError("missing collector manifest")
        manifest_info = z.getinfo("manifest.json")
        if manifest_info.file_size > 128 * 1024:
            raise ValueError("manifest too large")
        manifest = json.loads(z.read("manifest.json"))
        if manifest.get("client_sha256") != CLIENT_SHA:
            raise ValueError("wrong client SHA")
        candidates = manifest.get("files")
        if not isinstance(candidates, list) or not 1 <= len(candidates) <= MAX_FILES:
            raise ValueError("invalid candidate count")
        if manifest.get("count") != len(candidates) or manifest.get("sources_modified") is not False:
            raise ValueError("unsafe or inconsistent manifest")
        result = []
        known = set()
        for row in candidates:
            path = row.get("path")
            if not isinstance(path, str) or path.startswith("/") or "\\" in path or ".." in pathlib.PurePosixPath(path).parts:
                raise ValueError("unsafe candidate path")
            if pathlib.PurePosixPath(path).name.lower() not in ("meritsystem.enc", "meritsystem_msg.enc"):
                raise ValueError("unrelated resource")
            if path in known:
                raise ValueError("duplicate candidate path")
            known.add(path)
            metadata = z.getinfo(path)
            if metadata.is_dir() or metadata.file_size > MAX_ENTRY or metadata.file_size != row.get("size_bytes"):
                raise ValueError("file size mismatch or oversized")
            with z.open(path) as f:
                raw = f.read(MAX_ENTRY + 1)
            info = inspect_payload(raw)
            if info["sha256"] != row.get("sha256"):
                raise ValueError("file SHA mismatch: " + path)
            info["path"] = path
            info["language_path"] = bool(row.get("language_path"))
            result.append(info)
        if set(names) != known | {"manifest.json"}:
            raise ValueError("ZIP has unrelated/missing entries")
    return {
        "mode": "OFFLINE_READ_ONLY",
        "client_sha256": CLIENT_SHA,
        "runtime_opened_path_proven": False,
        "diamond_ui_or_packet_proven": False,
        "tested_codec_is_only_one_observed_route": True,
        "loader_binding_to_these_assets_proven": False,
        "candidates": result,
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=pathlib.Path)
    parser.add_argument("--report", type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = audit(args.archive)
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print("CANDIDATE_AUDIT=REJECTED: " + str(exc), file=sys.stderr)
        return 2
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.report:
        if args.report.resolve() == args.archive.resolve():
            print("REFUSE_OVERWRITE_ARCHIVE", file=sys.stderr)
            return 2
        args.report.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
