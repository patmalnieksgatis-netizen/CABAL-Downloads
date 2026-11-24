#!/usr/bin/env python3
"""V27 standalone module: no core replacement or auto-hook. Offline build only."""
import hashlib,json,pathlib,subprocess,sys,zipfile,tempfile,shutil
SRC=pathlib.Path("/root/CABAL_V282_LIVE_MERGE_CANDIDATE_v14/source_tree/src")
IMAGE="sha256:2805f2cd7dacf0547b8762437009a4814ab0c352f913b15c87b3e856f04528bb"
WORLD_SHA="caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3"
TREE_SHA="2efba153ae4d7bfcbeee2203f7b7d7a47f0a5686e31dc20dd8638ca7ac3947c2"
UNITS=[
"native/grade2-ingress/DiamondWorld48TicketUnits.cpp",
"native/world-session-bridge/deps/EventPassOwnerV282.cpp",
"native/inventory-reconcile/DiamondInventoryReconcile.cpp",
"native/grade2-ingress/DiamondGradeUp0BDA.cpp",
"native/grade2-ingress/Diamond0BDATicketSelection.cpp",
"native/grade2-ingress/Diamond0BDAGameplayAction.cpp",
"native/grade2-ingress/Diamond0BDAAuthenticatedIngress.cpp",
"native/real-gamedata-transaction/DiamondRealGameDataOdbc.cpp",
"native/real-gamedata-transaction/Diamond0BDARealServer01Bridge.cpp",
"native/world-save-barrier/DiamondWorldSaveBarrier.cpp",
"native/grade2-ingress/Diamond0BDASaveReplyGate.cpp"]
ENTRY=r'''
#include "worldsvr-ingress/DiamondNativeRankUpV20.h"
extern "C" __attribute__((visibility("default")))
unsigned cabal_diamond291_abi() noexcept { return 27; }
extern "C" __attribute__((visibility("default")))
int cabal_diamond291_register(const diamond_v19::Host* host,
                             const diamond_v20::Binding* binding) noexcept {
    if(!host || !binding)return static_cast<int>(diamond_v19::Status::Blocked);
    return static_cast<int>(diamond_v20::Register(*host,*binding));
}
'''
SMOKE=r'''
#include "worldsvr-ingress/DiamondNativeRankUpV20.h"
#include <cassert>
int main(){
    unsigned char f[14]={0xe2,0xb7,14,0,0,0,0,0,0xda,0x0b,1,0,3,0};
    auto r=diamond_v291::real_gamedata::Execute0BDARealServer01(nullptr,f,sizeof(f),{});
    assert(r.state==diamond_v291::gradeup0bda::GameActionState::MissingWorldAuthority);
    assert(!r.maySendClientSuccess);
    f[8]=0x10;
    r=diamond_v291::real_gamedata::Execute0BDARealServer01(nullptr,f,sizeof(f),{});
    assert(r.state==diamond_v291::gradeup0bda::GameActionState::NotDiamondCommand);
    diamond_v19::Host h{};
    diamond_v20::Binding b{};
    assert(diamond_v20::Register(h,b)==diamond_v19::Status::Blocked);
}
'''
def run(args,timeout=60):
    p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError("rc="+str(p.returncode)+" "+repr(args[:5])+"\n"+p.stderr[-8000:])
    return p.stdout
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def manifest():
    entries=sorted((p for p in SRC.rglob("*") if p.is_file()),key=lambda p:p.relative_to(SRC).as_posix())
    if any(p.is_symlink() for p in SRC.rglob("*")):raise RuntimeError("source symlink")
    return len(entries),hashlib.sha256("".join(sha(p)+"  "+p.relative_to(SRC).as_posix()+"\n" for p in entries).encode()).hexdigest()
def main():
    if manifest()!=(64,TREE_SHA):raise RuntimeError("original source manifest mismatch")
    pid=run(["docker","exec","cabal_main","supervisorctl","pid","WorldSvr_01_01"]).strip()
    if not pid.isdigit() or int(pid)<1:raise RuntimeError("WorldSvr not running")
    if run(["docker","exec","cabal_main","sha256sum","/proc/"+pid+"/exe"]).split()[0]!=WORLD_SHA:raise RuntimeError("WorldSvr hash mismatch")
    work=pathlib.Path(tempfile.mkdtemp(prefix="cabal-diamond-v27-",dir="/tmp"))
    deps=work/"src";deps.mkdir()
    with zipfile.ZipFile(sys.argv[1]) as z:
        for name in z.namelist():
            p=pathlib.PurePosixPath(name.replace("\\","/"))
            if p.is_absolute() or ".." in p.parts:raise RuntimeError("bad archive path")
            if not name.endswith(("/", "\\")):
                dest=deps.joinpath(*p.parts);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(name))
    # Keep the bundled Diamond owner reader in a separate namespace so the
    # original V14 EventPass symbols remain unmodified and link unambiguously.
    for rel in ("native/world-session-bridge/deps/EventPassOwnerV282.h",
                "native/world-session-bridge/deps/EventPassOwnerV282.cpp",
                "native/grade2-ingress/Diamond0BDAAuthenticatedIngress.cpp"):
        f=deps/rel
        import re
        f.write_text(re.sub(r"\bEventPassOwnerV282\b", "DiamondV27OwnerReader", f.read_text()).replace("DiamondV27OwnerReader.h", "EventPassOwnerV282.h"))
    (deps/"entry.cpp").write_text(ENTRY)
    (deps/"smoke.cpp").write_text(SMOKE)
    out=work/"build";out.mkdir()
    container=["docker","run","--rm","--network","none","--read-only",
               "--tmpfs","/tmp:rw,nosuid,size=512m",
               "--mount","type=bind,src="+str(deps)+",dst=/diamond,readonly",
               "--mount","type=bind,src="+str(out)+",dst=/result",IMAGE]
    version=run(container+["g++-14","-dumpfullversion"]).strip()
    if version!="14.2.0":raise RuntimeError("wrong compiler")
    units=["/diamond/"+p for p in UNITS]
    flags=["g++-14","-std=c++17","-O2","-I/diamond"]
    libs=["-ldl","-lpthread","-lodbc"]
    print("V27_BUILD_REAL_CHAIN",flush=True)
    run(container+flags+["/diamond/smoke.cpp",*units,"-o","/result/smoke",*libs],timeout=900)
    run(container+["/result/smoke"])
    print("V27_REAL_LINK_DENIAL_SMOKE=PASS",flush=True)
    run(container+flags+["/diamond/worldsvr-ingress/test_native_rankup_v20.cpp","-o","/result/wiring-test"],timeout=120)
    run(container+["/result/wiring-test"])
    print("V27_WIRING_TEST=PASS",flush=True)
    name="Diamond291_V27_OFFLINE.so"
    (deps/"exports.map").write_text("{ global: cabal_diamond291_abi; cabal_diamond291_register; local: *; };\n")
    (deps/"load_test.cpp").write_text(r"""
#include <dlfcn.h>
#include <cassert>
#include "worldsvr-ingress/DiamondNativeProcedureRegistrationV19.h"
int main(int argc,char** argv) {
    assert(argc==2);
    void* h=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
    assert(h);
    auto abi=reinterpret_cast<unsigned(*)()>(dlsym(h,"cabal_diamond291_abi"));
    auto reg=reinterpret_cast<int(*)(const diamond_v19::Host*,const void*)>(dlsym(h,"cabal_diamond291_register"));
    assert(abi && abi()==27 && reg);
    assert(reg(nullptr,nullptr)==static_cast<int>(diamond_v19::Status::Blocked));
    assert(dlclose(h)==0);
}
""")
    run(container+flags+["-fPIC","-fvisibility=hidden","-shared","-Wl,--no-undefined",
        "-Wl,--version-script=/diamond/exports.map","-Wl,-soname,"+name,
        "-o","/result/"+name,*units,"/diamond/entry.cpp",*libs],timeout=900)
    target=out/name
    symbols=run(["readelf","--dyn-syms","-W",str(target)])
    exported=set()
    for line in symbols.splitlines():
        w=line.split()
        if len(w)>=8 and w[0].rstrip(":").isdigit() and w[6]!="UND" and w[4] in ("GLOBAL","WEAK","UNIQUE") and w[5] in ("DEFAULT","PROTECTED"):
            exported.add(w[7])
    if exported!={"cabal_diamond291_abi","cabal_diamond291_register"}:raise RuntimeError("unexpected exported symbols: "+repr(sorted(exported)))
    run(container+flags+["/diamond/load_test.cpp","-ldl","-o","/result/load-test"])
    run(container+["/result/load-test","/result/"+name])
    print("V27_ISOLATED_DLOPEN_DENIAL=PASS",flush=True)
    print("V27_EXPORT_ISOLATION=PASS",flush=True)
    base="/usr/lib/cabal/lib.so"
    baseline="6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab"
    def d(*a):return run(["docker","exec","cabal_main",*a])
    if d("sha256sum",base).split()[0]!=baseline:raise RuntimeError("live core hash mismatch")
    print("V27_CORE_UNCHANGED=PASS",flush=True)
    for lib in [base,"/etc/cabal/migration_tools/ep36-costume-trial-v1/mileage-v1/EP36CostumeMileage.so",
                "/usr/lib/cabal/cashshop291/CashShop291.so"]:
        print("V27_EXISTING_MODULE="+lib,flush=True)
        p=subprocess.run(["docker","exec","cabal_main","nm","-D","-C",lib],capture_output=True,text=True)
        if p.returncode:
            print("V27_SYMBOL_READ_UNAVAILABLE",flush=True)
            continue
        for line in p.stdout.splitlines():
            if any(k in line.lower() for k in ("openprocedure","addproc","register","attach","dlsym","runserver")):
                print(line[:300])
    if manifest()!=(64,TREE_SHA):raise RuntimeError("original source changed")
    result={"artifact":str(target),"sha256":sha(target),"original_units":0,"diamond_units":len(units)+1,
            "exported_symbols":sorted(exported),"isolated_load_test":True,"core_sha256":baseline,
            "runtime_host_bound":False,"auto_hook":False,"install_allowed":False,"rankup_verified":False,"active_world_modified":False}
    (out/"REPORT.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    print("DIAMOND_V27=STANDALONE_BUILD_COMPLETE")
if __name__=="__main__":
    try:main()
    except Exception as e:
        print("DIAMOND_V27=STOP "+str(e),file=sys.stderr);sys.exit(2)
