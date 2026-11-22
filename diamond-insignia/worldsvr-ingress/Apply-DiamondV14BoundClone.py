#!/usr/bin/env python3
"""Hash-pinned, SOURCE-COPY ONLY CABAL v282/v291 v14 Diamond ABI-v2 adapter.

Never touches a running WorldSvr, compiled lib.so, database, client or VM.
The synthetic test ingress deliberately still forwards game packets to the
original server's dispatcher. It is NOT a playable Diamond feature.
"""
import argparse
import hashlib
import pathlib
import shutil
import sys
import tempfile

ROOT=pathlib.Path(__file__).resolve().parent
V14_TREE_SHA="2efba153ae4d7bfcbeee2203f7b7d7a47f0a5686e31dc20dd8638ca7ac3947c2"
V14_FILE_COUNT=64
PROC_SHA="59b44f522a8cfd189516b1f7c6e2434a1c7e5249c6d563b91178c3a2cc95bc19"
TYPES_SHA="32ae9931ac8e779c9de58a25b6e903f03ecfdd46324c334f3a417f8a4be0fa3c"
V14_NATIVE_SOURCE="diamond_merit_world_entry_v2.cpp"

def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def files(root):
    result=sorted((p for p in root.rglob("*") if p.is_file()),
                  key=lambda p:p.relative_to(root).as_posix())
    if any(p.is_symlink() for p in root.rglob("*")):
        raise RuntimeError("STOP: symlink in v14 source")
    return result

def manifest(root):
    entries=files(root)
    data="".join(sha_bytes(p.read_bytes())+"  "+
                 p.relative_to(root).as_posix()+"\n" for p in entries)
    return len(entries),sha_bytes(data.encode("utf-8"))

def replace_one(s,old,new):
    if s.count(old)!=1:
        raise RuntimeError("STOP: original v14 source marker changed: "+repr(old[:70]))
    return s.replace(old,new)

def patch(source,output):
    source=source.resolve();output=output.resolve()
    if not source.is_dir() or output.exists() or source==output or (
        source in output.parents or output in source.parents):
        raise RuntimeError("STOP: source absent, output exists, or paths overlap")
    n,digest=manifest(source)
    if n!=V14_FILE_COUNT or digest!=V14_TREE_SHA:
        raise RuntimeError("STOP: v14 source-tree file manifest differs")
    if sha_bytes((source/"hooks/Handlers/ProcSystem.cpp").read_bytes())!=PROC_SHA or (
        sha_bytes((source/"include/Types.h").read_bytes())!=TYPES_SHA):
        raise RuntimeError("STOP: critical v14 files changed")
    native=ROOT.parent/"native"
    dependencies={
        "DiamondIngress.h":ROOT/"DiamondIngress.h",
        "DiamondBoundIngress.h":ROOT/"DiamondBoundIngress.h",
        "diamond_abi.h":native/"diamond_abi.h",
        "diamond_world_bridge.h":native/"diamond_world_bridge.h",
        "diamond_merit_world_entry.h":native/"diamond_merit_world_entry.h",
        V14_NATIVE_SOURCE:native/"diamond_merit_world_entry.cpp",
    }
    if any(not p.is_file() for p in dependencies.values()):
        raise RuntimeError("STOP: missing native ABI-v2 source/header")
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="diamond-v14-stage-",dir=str(output.parent)) as tmp:
        staged=pathlib.Path(tmp)/"src"
        shutil.copytree(source,staged)
        target=staged/"include/Types.h"
        t=target.read_text()
        t=replace_one(t,"    char* cpPacket;\n    // ... other fields",
          "    char* cpPacket;\n"
          "    std::size_t iLen; // WorldSvr native request length, offset 16\n"
          "    // ... other fields")
        t+='\nstatic_assert(offsetof(PROCESSDATACONTEXT,iLen)==16, "packet context ABI changed");\n'
        target.write_text(t)
        proc=staged/"hooks/Handlers/ProcSystem.cpp"
        p=proc.read_text()
        p=replace_one(p,'#include "../Packets/OpCodes.h"',
                       '#include "../Packets/OpCodes.h"\n'
                       '#include "DiamondIngress.h"\n'
                       '#include "DiamondBoundIngress.h"')
        p=replace_one(p,'    UINT16 opcode = header->wMainCmd;\n',
'''    UINT16 opcode = header->wMainCmd;
    // SYNTHETIC SHADOW ONLY: existing EventPass, Gold, Platinum and
    // original WorldSvr dispatch remain untouched on every code path.
    if (opcode == DiamondIngress::kMasteryLevelUp &&
        DiamondIngress::Enabled() && pProcessDataCtx->iLen == 18) {
        const auto observation=DiamondIngress::Inspect(
            pProcessDataCtx->cpPacket,pProcessDataCtx->iLen);
        if(observation.candidate) {
            const auto decision=DiamondBoundIngress::Process(
                pProcessDataCtx->pUserCtx,pProcessDataCtx->cpPacket,
                pProcessDataCtx->iLen);
            if(decision==DiamondBoundIngress::Result::ShadowApplied &&
               DiamondIngress::ShouldLog()) {
                Log::Print(LOG_INFO,"DiamondV14Offline",__LINE__,
                           "SYNTHETIC shadow commit; original dispatch untouched");
            }
        }
    }
''')
        p+='''
#if defined(DIAMOND_ENABLE_SHADOW_TRIAL)
extern "C" __attribute__((visibility("default")))
int cabal_diamond_proc_bind_shadow_clone_v3(
    const DiamondBoundIngress::Binding* binding) {
    return DiamondBoundIngress::InstallOnce(binding)?0:-1;
}
extern "C" __attribute__((visibility("default")))
int cabal_diamond_proc_test_ingress_clone_v3(
    const void* context,const void* bytes,std::size_t length) {
    return static_cast<int>(DiamondBoundIngress::Process(context,bytes,length));
}
#endif
'''
        proc.write_text(p)
        for name,origin in dependencies.items():
            dest=proc.parent/name
            if dest.exists():raise RuntimeError("STOP: v14 source has Diamond ABI collision: "+name)
            shutil.copy2(origin,dest)
        if manifest(source)!=(V14_FILE_COUNT,V14_TREE_SHA):
            raise RuntimeError("STOP: original v14 source changed during staging")
        staged.rename(output)
    print("DIAMOND_EXACT_V14_SOURCE_CLONE_PATCH=PASS")
    print("V14_SOURCE_SHA256_MANIFEST="+V14_TREE_SHA)
    print("SOURCE_UNMODIFIED=YES")
    print("CURRENT_GAME_SERVER_SQL_CLIENT=UNTOUCHED")
    print("CLONE_PATH="+str(output))

if __name__=="__main__":
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--source",type=pathlib.Path,required=True)
    a.add_argument("--output",type=pathlib.Path,required=True)
    args=a.parse_args()
    try:patch(args.source,args.output)
    except Exception as e:
        print("DIAMOND_EXACT_V14_SOURCE_CLONE_PATCH=STOP: "+str(e),file=sys.stderr)
        sys.exit(1)
