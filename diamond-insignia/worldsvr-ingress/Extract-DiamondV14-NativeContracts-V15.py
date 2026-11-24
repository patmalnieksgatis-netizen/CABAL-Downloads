#!/usr/bin/env python3
"""Extract the original V14 native dispatch contracts required for Diamond.
Read-only, no binary loading, SQL connection, live patch or restart.
"""
import hashlib,pathlib,re,sys

ROOT=pathlib.Path("/root/CABAL_V282_LIVE_MERGE_CANDIDATE_v14/source_tree/src")
MANIFEST="2efba153ae4d7bfcbeee2203f7b7d7a47f0a5686e31dc20dd8638ca7ac3947c2"
FILES={
 "hooks/Handlers/ProcSystem.cpp",
 "include/Types.h",
}
NAMES={"ProcSystem.h","SockHandler.h","SockHandler.cpp","OpCodes.h"}
TERMS=re.compile(r"\b(?:AddProc|RegisterExtendedHandler|ForceRegisterHandlers|OpenProcedure|DoProcessDataCtx|PROCEDUREMAP_V2|PROCESSDATACONTEXT|SendBuf|USERCONTEXT|USERDATACONTEXT|GameData|SaveGameData|CharacterSave|WarExp|DBAgent)\b",re.I)

def main():
    paths=sorted((p for p in ROOT.rglob("*") if p.is_file()),key=lambda p:p.relative_to(ROOT).as_posix())
    if any(p.is_symlink() for p in ROOT.rglob("*")):raise RuntimeError("unexpected symlink")
    manifest="".join(hashlib.sha256(p.read_bytes()).hexdigest()+"  "+p.relative_to(ROOT).as_posix()+"\n" for p in paths)
    if len(paths)!=64 or hashlib.sha256(manifest.encode()).hexdigest()!=MANIFEST:
        raise RuntimeError("original V14 source manifest mismatch")
    print("BEGIN_DIAMOND_V15_NATIVE_CONTRACTS")
    print("V14_SOURCE_MANIFEST_VERIFIED=YES")
    for p in paths:
        if p.suffix not in (".h",".hpp",".cpp"):continue
        rel=p.relative_to(ROOT).as_posix()
        lines=p.read_text(encoding="utf-8",errors="replace").splitlines()
        if rel in FILES or p.name in NAMES:
            chosen=set(range(len(lines))) if len(lines)<=320 else set()
            if not chosen:
                for i,line in enumerate(lines):
                    if TERMS.search(line):chosen.update(range(max(0,i-5),min(len(lines),i+8)))
        else:
            chosen=set()
            for i,line in enumerate(lines):
                if TERMS.search(line):chosen.update(range(max(0,i-3),min(len(lines),i+4)))
        if not chosen:continue
        print("\nFILE "+rel+" LINES="+str(len(lines)))
        limit=320 if rel in FILES or p.name in NAMES else 65
        for i in sorted(chosen)[:limit]:
            print(str(i+1)+": "+lines[i])
        if len(chosen)>limit:print("EXCERPT_TRUNCATED=YES")
    print("END_DIAMOND_V15_NATIVE_CONTRACTS")
if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("DIAMOND_V15=STOP: "+str(exc),file=sys.stderr)
        sys.exit(2)
