#!/usr/bin/env python3
"""Patch a COPY of the exact archived lib.so source. No VM or production writes.

Never patches the source tree in place. Exact SHA gating prevents silent use on
an unrelated customized WorldSvr extension checkout.
"""
import argparse
import hashlib
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent
TARGETS = {
    'include/Types.h': 'c32a66118f439cf1a1279f703c3a9a1e272a4dfbb89a0745c93983ce5a2e3b61',
    'hooks/Handlers/ProcSystem.cpp': 'b687c3bb9607aa886f37bcf203dcf4fb1a315cf6e9a23d4e67adea69e1486d88',
}

def replace_one(blob: bytes, old: bytes, new: bytes) -> bytes:
    if blob.count(old) != 1:
        raise RuntimeError(f'STOP: expected exact, unique marker ({old[:70]!r})')
    return blob.replace(old, new)

def patch(root: pathlib.Path, out: pathlib.Path) -> None:
    root, out = root.resolve(), out.resolve()
    if root == out or root in out.parents:
        # Never write inside the original tree (recursive copying is unsafe).
        raise RuntimeError('STOP: do not patch the original source tree')
    if out.exists():
        raise RuntimeError('STOP: destination already exists, will not overwrite')
    for file, expected in TARGETS.items():
        p = root / file
        if not p.is_file():
            raise RuntimeError(f'STOP: archived source file missing: {file}')
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if digest != expected:
            raise RuntimeError(f'STOP: source changed for {file}: SHA256={digest}')
    extra = root / 'hooks/Handlers/DiamondIngress.h'
    if extra.exists():
        raise RuntimeError('STOP: DiamondIngress already present in source')
    shutil.copytree(root, out)
    types = out / 'include/Types.h'
    blob = types.read_bytes()
    blob = replace_one(blob, b'#include <cstdint>\r\n',
                       b'#include <cstdint>\r\n#include <cstddef>\r\n')
    blob = replace_one(blob, b'    char* cpPacket;\r\n    // ... other fields',
                       b'    char* cpPacket;\r\n    // ABI candidate from archived C2SHandler.cpp: +0x10\r\n'
                       b'    std::size_t iLen;\r\n    // ... other fields')
    blob += (b'\r\nstatic_assert(offsetof(PROCESSDATACONTEXT, iLen)==16,\r\n'
             b'              "C2S input packet context ABI mismatch");\r\n')
    types.write_bytes(blob)
    proc = out / 'hooks/Handlers/ProcSystem.cpp'
    blob = proc.read_bytes()
    blob = replace_one(blob, b'#include "../Packets/OpCodes.h"\r\n',
                       b'#include "../Packets/OpCodes.h"\r\n#include "DiamondIngress.h"\r\n')
    marker = b'    UINT16 opcode = header->wMainCmd;\r\n'
    block = b'''    UINT16 opcode = header->wMainCmd;\r\n
    // PASSIVE ONLY: always return through the unchanged original dispatcher.\r\n
    // No WorldBridge callbacks, MSSQL writes, packet replacements or replies.\r\n
    if (opcode == DiamondIngress::kMasteryLevelUp && DiamondIngress::Enabled()) {\r\n
        const auto sample = DiamondIngress::Inspect(\r\n
            pProcessDataCtx->cpPacket, pProcessDataCtx->iLen);\r\n
        if (sample.candidate && DiamondIngress::ShouldLog()) {\r\n
            Log::Print(LOG_INFO, "DiamondIngress", __LINE__,\r\n
                       "PASSIVE Merit grade2 candidate: mastery_id=%u; original dispatch preserved",\r\n
                       sample.mastery_id);\r\n
        }\r\n
    }\r\n'''.replace(b'\r\n\n', b'\r\n')
    blob = replace_one(blob, marker, block)
    proc.write_bytes(blob)
    shutil.copy2(ROOT / 'DiamondIngress.h', out / 'hooks/Handlers/DiamondIngress.h')
    for key in TARGETS:
        assert (out / key).read_bytes() != (root / key).read_bytes()
        assert hashlib.sha256((root / key).read_bytes()).hexdigest() == TARGETS[key]
    print('DIAMOND_INGRESS_CLONE_PATCH=PASS')
    print(f'OUTPUT={out}')
    print('PRODUCTION_SOURCE_UNMODIFIED=YES')
    print('LIVE_SERVER_PATCH=NO;GAMEPLAY_DIAMOND=NO')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        patch(args.source, args.output)
    except Exception as exc:
        print(f'DIAMOND_INGRESS_CLONE_PATCH=STOP: {exc}', file=sys.stderr)
        sys.exit(1)
