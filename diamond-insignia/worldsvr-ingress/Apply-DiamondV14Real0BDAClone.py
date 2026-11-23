#!/usr/bin/env python3
"""Add a NO-WRITE 0BDA branch to an EXACT HASH-MATCHED v14 source COPY.

Creates an isolated source tree; NEVER builds/replaces lib.so, invokes
supervisorctl, modifies Docker, MSSQL or game content. The 0BDA branch is
connected to the real proc dispatch hook, but its port is intentionally
unbound until save barrier + verified S2C reply ABI can be supplied.
"""
from __future__ import annotations
import argparse
import importlib.util
import pathlib
import shutil
import sys
import tempfile

HERE=pathlib.Path(__file__).resolve().parent
BASE=HERE/"Apply-DiamondV14BoundClone.py"
HEADER=HERE/"DiamondReal0BDAIngressPort.h"

def base_module():
    spec=importlib.util.spec_from_file_location("diamond_v14_copy_patcher",BASE)
    if spec is None or spec.loader is None:
        raise RuntimeError("STOP: v14 base patcher is unavailable")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def patch(source:pathlib.Path, output:pathlib.Path)->None:
    source=source.resolve()
    output=output.resolve()
    if not source.is_dir() or not HEADER.is_file():
        raise RuntimeError("STOP: verified v14 source and hook header required")
    if output.exists() or source==output or source in output.parents or output in source.parents:
        raise RuntimeError("STOP: destination exists or source/destination overlap")
    base=base_module()
    # Verify the 64-file source manifest before even creating a copy.
    if base.manifest(source)!=(base.V14_FILE_COUNT,base.V14_TREE_SHA):
        raise RuntimeError("STOP: v14 source manifest does not match the running core reference")
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="diamond-v14-real0bda-",dir=str(output.parent)) as tmp:
        stage=pathlib.Path(tmp)/"source"
        base.patch(source,stage)  # independently pins ProcSystem.cpp and Types.h
        target=stage/"hooks/Handlers/ProcSystem.cpp"
        original=target.read_text(encoding="utf-8")
        replaced=base.replace_one(
            original,
            '#include "DiamondBoundIngress.h"',
            '#include "DiamondBoundIngress.h"\n#include "DiamondReal0BDAIngressPort.h"')
        replaced=base.replace_one(
            replaced,
            '    UINT16 opcode = header->wMainCmd;\n',
            '''    UINT16 opcode = header->wMainCmd;
    // v291 grade-up candidate 0x0BDA. NEVER CONSUME a real packet
    // without a complete authenticated GameData + cmd46/47 + S2C
    // adapter. The compiled default port always forwards unchanged.
    // 0x0B10 Platinum and 0x09F3 Merit keep original dispatch.
    if (opcode == DiamondReal0BDAIngressPort::kOpcode &&
        pProcessDataCtx->pUserCtx &&
        DiamondReal0BDAIngressPort::IsCandidate(
            pProcessDataCtx->cpPacket,pProcessDataCtx->iLen)) {
        int nativeReturn=0;
        if (DiamondReal0BDAIngressPort::Process(
                pProcessDataCtx->pUserCtx,
                pProcessDataCtx->cpPacket,
                pProcessDataCtx->iLen,
                &nativeReturn)) {
            // This can never execute in default build. Future complete
            // adapter must have already sent a verified real S2C reply
            // and reconciled both WorldSvr memory and GameData.
            return nativeReturn;
        }
    }
''')
        target.write_text(replaced,encoding="utf-8")
        dst=target.parent/"DiamondReal0BDAIngressPort.h"
        if dst.exists():
            raise RuntimeError("STOP: exact v14 source unexpectedly already has a 0BDA port")
        shutil.copy2(HEADER,dst)
        if "    return ((int(*)(void*, PROCESSDATACONTEXT*))oDoProcessDataCtx)(pProcessLayer, pProcessDataCtx);" not in replaced:
            raise RuntimeError("STOP: original fallback dispatcher no longer recognizable")
        if base.manifest(source)!=(base.V14_FILE_COUNT,base.V14_TREE_SHA):
            raise RuntimeError("STOP: original input changed during source-copy patch")
        stage.rename(output)
    print("DIAMOND_V14_REAL0BDA_SOURCE_HOOK=CONNECTED_OFFLINE")
    print("OPCODE=0x0BDA")
    print("ORIGINAL_DISPATCH_PASSTHROUGH=YES")
    print("WORLD_SQL_CLIENT_MODIFIED=NO")
    print("BINDER_ENABLED=NO")
    print("IN_GAME_RANKUP_WORKING=NO")
    print("CLONE_SOURCE="+str(output))

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",required=True,type=pathlib.Path)
    parser.add_argument("--output",required=True,type=pathlib.Path)
    args=parser.parse_args()
    try:
        patch(args.source,args.output)
    except Exception as ex:
        print("DIAMOND_V14_REAL0BDA_SOURCE_HOOK=STOP: "+str(ex),file=sys.stderr)
        raise SystemExit(2)
