#!/usr/bin/env python3
"""Hash-pinned two-stage binding into a COPY of archived WorldSvr lib source.

Never alters original source, game process, SQL server, binary, VM or game data.
Both normal and synthetic-trial dispatcher builds ONLY observe real packets.
A separately exported isolated test-only entry may exercise synthetic writes
without forwarding to the original game handler.
"""
import argparse
import hashlib
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT=pathlib.Path(__file__).resolve().parent
PASSIVE_PROC_SHA="56d8c200fcdd0c215426e77cba6c5bd4df93536b5d341ff788a3b54252abdb06"
PASSIVE_TYPES_SHA="5718170c4ecd957ab3e3cc4ba4db3ff48273bd7d4a0caf6ee860f8f98776b47f"

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def one(data,old,new):
    if data.count(old)!=1:
        raise RuntimeError("STOP: ambiguous / changed original ProcSystem marker: "+repr(old[:65]))
    return data.replace(old,new)

def copy_native_headers(dest):
    """Copy ABI-v3 headers into an isolated clone, all prerequisites checked."""
    dest=pathlib.Path(dest)
    headers={
        "DiamondBoundIngress.h": ROOT/"DiamondBoundIngress.h",
        "diamond_abi.h": ROOT.parent/"native"/"diamond_abi.h",
        "diamond_world_bridge.h": ROOT.parent/"native"/"diamond_world_bridge.h",
        "diamond_merit_world_entry.h": ROOT.parent/"native"/"diamond_merit_world_entry.h",
    }
    for name,origin in headers.items():
        if dest.joinpath(name).exists() or not origin.is_file():
            raise RuntimeError("STOP: missing or already installed header: "+name)
    for name,origin in headers.items():
        shutil.copy2(origin,dest/name)


def run(original,output):
    original=original.resolve();output=output.resolve()
    if not original.is_dir():raise RuntimeError("STOP: original source absent")
    if output.exists():raise RuntimeError("STOP: output already exists; no overwrite")
    if original==output or original in output.parents or output in original.parents:
        raise RuntimeError("STOP: source/output paths overlap")
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="diamond-world-pre-",dir=str(output.parent)) as tmp:
        staged=pathlib.Path(tmp)/"passive"
        subprocess.run([sys.executable,str(ROOT/"Apply-DiamondIngressClone.py"),
                        "--source",str(original),"--output",str(staged)],check=True)
        proc=staged/"hooks/Handlers/ProcSystem.cpp"
        types=staged/"include/Types.h"
        if sha(proc)!=PASSIVE_PROC_SHA or sha(types)!=PASSIVE_TYPES_SHA:
            raise RuntimeError("STOP: passive stage hash changed; no compatible binding")
        data=proc.read_bytes()
        data=one(data,b'#include "DiamondIngress.h"\r\n',
                    b'#include "DiamondIngress.h"\r\n#include "DiamondBoundIngress.h"\r\n')
        # IMPORTANT: keep original C2S dispatcher observation-only.
        # The original WorldSvr handler is ALWAYS invoked afterwards.
        # Calling Process here would mutate a shadow transaction and then
        # forward the same packet to the original handler (double debit).
        # The synthetic gate is exercised exclusively by the separately
        # exported cabal_diamond_proc_test_ingress_clone_v3 function.
        if b"DiamondBoundIngress::Process(" in data:
            raise RuntimeError("STOP: game dispatcher unexpectedly writes Diamond")
        data+=b'''\r\n#if defined(DIAMOND_ENABLE_SHADOW_TRIAL)\r\n// Explicit authenticated adapter registration for isolated synthetic clone.\r\n// This symbol is ABSENT from default builds. No host binding => fail closed.\r\nextern "C" __attribute__((visibility("default")))\r\nint cabal_diamond_proc_bind_shadow_clone_v3(\r\n    const DiamondBoundIngress::Binding* binding) {\r\n    return DiamondBoundIngress::InstallOnce(binding) ? 0 : -1;\r\n}\r\n// Synthetic, offline-only test entrance: validates the actual linked clone\r\n// binding without calling the archived WorldSvr dispatcher or using sockets.\r\n// ABSENT from all normal builds, never install this object as game lib.so.\r\nextern "C" __attribute__((visibility("default")))\r\nint cabal_diamond_proc_test_ingress_clone_v3(\r\n    const void* serverOwnedContext,const void* bytes,std::size_t length) {\r\n    return static_cast<int>(\r\n        DiamondBoundIngress::Process(serverOwnedContext,bytes,length));\r\n}\r\n#endif\r\n'''
        proc.write_bytes(data)
        dest=proc.parent
        copy_native_headers(dest)
        shutil.copytree(staged,output,symlinks=False)
        assert sha(original/"hooks/Handlers/ProcSystem.cpp")== \
               "b687c3bb9607aa886f37bcf203dcf4fb1a315cf6e9a23d4e67adea69e1486d88"
    print("DIAMOND_BOUND_CLONE_SOURCE_PATCH=PASS")
    print("CLONE_PATH="+str(output))
    print("DEFAULT_BUILD_HAS_NO_DB_WRITES=YES")
    print("ACTIVE_WORLDSVR_OR_LIBSO_CHANGED=NO")

if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source",type=pathlib.Path,required=True)
    ap.add_argument("--output",type=pathlib.Path,required=True)
    args=ap.parse_args()
    try:run(args.source,args.output)
    except Exception as e:
        print("DIAMOND_BOUND_CLONE_SOURCE_PATCH=STOP: "+str(e),file=sys.stderr)
        sys.exit(1)
