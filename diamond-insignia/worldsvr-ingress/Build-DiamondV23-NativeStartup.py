#!/usr/bin/env python3
"""Build V23 against exact original V14 plus real Diamond objects.
Stages only: no live library replacement, no SQL, no server restart.
"""
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
int cabal_diamond_native_register_v23(const diamond_v19::Host* host,
                                      const diamond_v20::Binding* binding) noexcept {
    if(!host || !binding)return static_cast<int>(diamond_v19::Status::Blocked);
    return static_cast<int>(diamond_v20::Register(*host,*binding));
}
extern "C" __attribute__((visibility("default")))
unsigned cabal_diamond_native_v23_abi() noexcept { return 23; }
'''
STARTUP_HEADER="#pragma once\n// V23: concrete OpenProcedure startup adapter for the exact active WorldSvr.\n// Observation mode ONLY. It registers one native map after the original\n// OpenProcedure has finished, and never calls SQL or sends a success reply.\n// Default disabled; do not enable on production without a restorable test.\n#include \"DiamondNativeProcedureRegistrationV19.h\"\n#include \"../native/grade2-ingress/DiamondGradeUp0BDA.h\"\n#include <atomic>\n#include <cstdio>\n#include <cstdlib>\n#include <cstring>\n#include <mutex>\n#include <new>\n\nnamespace diamond_v23 {\ninline std::mutex startupMutex;\ninline bool dispatchSeen=false;\ninline bool installAttempted=false;\ninline std::atomic<unsigned long> observations{0};\ninline void NoteDispatcherEntry() noexcept {\n    // Once first dispatch observed, no further registration is possible.\n    // Acquire lock on initial entry only; no lock on ordinary game path\n    // after publication of first dispatch.\n    static std::atomic<bool> fast{false};\n    if(fast.load(std::memory_order_acquire))return;\n    std::lock_guard<std::mutex> guard(startupMutex);\n    dispatchSeen=true;\n    fast.store(true,std::memory_order_release);\n}\ninline bool Mapped(std::uintptr_t addr,std::size_t n,bool writable,bool executable) noexcept {\n    if(n==0 || addr+n<addr)return false;\n    auto* f=std::fopen(\"/proc/self/maps\",\"r\");\n    if(!f)return false;\n    char line[512];bool ok=false;\n    while(std::fgets(line,sizeof(line),f)){\n        unsigned long a=0,b=0;char perms[5]{};\n        if(std::sscanf(line,\"%lx-%lx %4s\",&a,&b,perms)!=3)continue;\n        if(addr>=a && addr+n<=b && perms[0]=='r' &&\n           (!writable || perms[1]=='w') && (!executable || perms[2]=='x')){\n            ok=true;break;\n        }\n    }\n    std::fclose(f);return ok;\n}\ntemplate<std::size_t N> inline bool Signature(std::uintptr_t addr,const unsigned char(&s)[N]) noexcept {\n    return Mapped(addr,N,false,true) && std::memcmp(reinterpret_cast<const void*>(addr),s,N)==0;\n}\ninline int Observe(void*,diamond_v19::ContextPrefix* ctx) noexcept {\n    if(!ctx || !ctx->user || !ctx->frame)return -1;\n    const auto parsed=diamond_v291::gradeup0bda::ParseC2s(ctx->frame,ctx->length);\n    if(parsed.state!=diamond_v291::gradeup0bda::PacketState::Candidate)return -1;\n    const auto seq=observations.fetch_add(1,std::memory_order_relaxed)+1;\n    // Log only packet shape, never account identifiers, pointers or contents.\n    if(seq<=16)std::fprintf(stderr,\"DIAMOND_V23_NATIVE_INGRESS seq=%lu bytes=%zu entries=%u NO_MUTATION\\n\",\n       seq,ctx->length,static_cast<unsigned>(parsed.count));\n    // No gameplay success, no SQL, no replay. Observation mode does not\n    // implement a client response. Normal native dispatcher handles return.\n    return -1;\n}\ninline void AfterOriginalOpenProcedure() noexcept {\n    const char* enabled=std::getenv(\"CABAL_DIAMOND_V23_NATIVE_OBSERVER\");\n    if(!enabled || std::strcmp(enabled,\"1\")!=0)return;\n    std::lock_guard<std::mutex> guard(startupMutex);\n    if(dispatchSeen || installAttempted){\n        std::fprintf(stderr,\"DIAMOND_V23_NATIVE_REGISTER=BLOCKED_LATE_OR_REPEAT\\n\");return;\n    }\n    installAttempted=true;\n    // Fixed-build signatures verified from the owner's actual ELF disassembly.\n    // These guards complement, not replace, the exact ELF hash check in the\n    // deployment preflight. Never use on another executable.\n    constexpr unsigned char ctorSig[]={0x55,0x48,0x89,0xe5,0x41,0x54,0x53,0x48,0x89,0xfb,0x48,0xc7,0x07,0,0,0,0};\n    constexpr unsigned char insertSig[]={0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,0x41,0x55,0x41,0x54,0x49,0x89,0xf7};\n    constexpr unsigned char callSig[]={0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,0x48,0x8d,0x45,0xc0};\n    using namespace diamond_v19;\n    if(!Signature(kNativeCtor,ctorSig) || !Signature(kNativeVectorInsert,insertSig) ||\n       !Signature(0xb49750,callSig) ||\n       !Mapped(kNativeUserTable,kSlots*sizeof(void*),true,false) ||\n       !Mapped(kNativeOtherTable,kSlots*sizeof(void*),false,false)){\n        std::fprintf(stderr,\"DIAMOND_V23_NATIVE_REGISTER=BLOCKED_SIGNATURE_OR_MAP\\n\");return;\n    }\n    auto** user=reinterpret_cast<void**>(kNativeUserTable);\n    auto* const* other=reinterpret_cast<void* const*>(kNativeOtherTable);\n    if(!user[kPlatinum] || !user[kPlatinumCancel] ||\n       user[kPlatinum]==user[kPlatinumCancel] || user[kDiamond] || other[kDiamond]){\n        std::fprintf(stderr,\"DIAMOND_V23_NATIVE_REGISTER=BLOCKED_COLLISION_OR_PLATINUM\\n\");return;\n    }\n    // Confirm expected existing Platinum callback, not just nonnull table.\n    if(!Mapped(reinterpret_cast<std::uintptr_t>(user[kPlatinum]),kMapBytes,false,false)){\n        std::fprintf(stderr,\"DIAMOND_V23_NATIVE_REGISTER=BLOCKED_PLATINUM_MAP\\n\");return;\n    }\n    auto* first=Read<Handler*>(user[kPlatinum],0);\n    if(!first || !Mapped(reinterpret_cast<std::uintptr_t>(first),sizeof(Handler),false,false) ||\n       reinterpret_cast<std::uintptr_t>(*first)!=0xa40f00){\n        std::fprintf(stderr,\"DIAMOND_V23_NATIVE_REGISTER=BLOCKED_PLATINUM_HANDLER\\n\");return;\n    }\n    // Use the process's normal C++ allocator and actual native constructor.\n    // Native destructor ABI not yet verified: after a successful ctor any\n    // failed candidate is retained unpublished (max one per process).\n    // This deliberately avoids guessing a destructor or freeing a live timer.\n    static void* quarantined=nullptr;\n    void* map=nullptr;bool constructed=false;\n    try {\n        map=::operator new(kMapBytes);\n        std::memset(map,0,kMapBytes);\n        reinterpret_cast<void(*)(void*)>(kNativeCtor)(map);\n        constructed=true;\n        if(Read<Handler*>(map,0) || Read<Handler*>(map,8) || Read<Handler*>(map,16) ||\n           Read<std::uint8_t>(map,0x20)!=1 || Read<std::uint32_t>(map,0x24)!=0 ||\n           Read<std::uint64_t>(map,0x28)!=0){\n            quarantined=map;std::fprintf(stderr,\"DIAMOND_V23_NATIVE_REGISTER=BLOCKED_CTOR_LAYOUT\\n\");return;\n        }\n        Handler entry=&Observe;\n        reinterpret_cast<void(*)(void*,Handler*,const Handler*)>(kNativeVectorInsert)(map,nullptr,&entry);\n        auto* start=Read<Handler*>(map,0);\n        auto* end=Read<Handler*>(map,8);\n        auto* capacity=Read<Handler*>(map,16);\n        if(!start || !end || !capacity ||\n           reinterpret_cast<std::uintptr_t>(end)-reinterpret_cast<std::uintptr_t>(start)!=sizeof(Handler) ||\n           reinterpret_cast<std::uintptr_t>(capacity)<reinterpret_cast<std::uintptr_t>(end) ||\n           *start!=entry || user[kDiamond] || other[kDiamond]){\n            quarantined=map;std::fprintf(stderr,\"DIAMOND_V23_NATIVE_REGISTER=BLOCKED_INSERT\\n\");return;\n        }\n        static constexpr char name[]=\"CSC_DIAMOND_GRADEUP: V23 OBSERVE\";\n        Write<const char*>(map,0x18,name);\n        Write<std::uint8_t>(map,0x20,1);\n        user[kDiamond]=map;\n        std::fprintf(stderr,\"DIAMOND_V23_NATIVE_REGISTER=OBSERVE_ONLY opcode=3034 SQL=OFF REPLY=OFF\\n\");\n    }catch(...){\n        if(constructed)quarantined=map;\n        else if(map)::operator delete(map);\n        std::fprintf(stderr,\"DIAMOND_V23_NATIVE_REGISTER=BLOCKED_EXCEPTION\\n\");\n    }\n    (void)quarantined;\n}\n} // namespace diamond_v23\n"
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
    work=pathlib.Path(tempfile.mkdtemp(prefix="cabal-diamond-v23-",dir="/tmp"))
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
        f.write_text(re.sub(r"\bEventPassOwnerV282\b", "DiamondV23OwnerReader", f.read_text()).replace("DiamondV23OwnerReader.h", "EventPassOwnerV282.h"))
    (deps/"worldsvr-ingress/DiamondNativeStartupV23.h").write_text(STARTUP_HEADER)
    cloned=work/"original-clone"
    shutil.copytree(SRC,cloned)
    proc=cloned/"hooks/Handlers/ProcSystem.cpp"
    if sha(proc)!="59b44f522a8cfd189516b1f7c6e2434a1c7e5249c6d563b91178c3a2cc95bc19":
        raise RuntimeError("ProcSystem source hash mismatch")
    code=proc.read_text()
    def once(old,new):
        nonlocal code
        if code.count(old)!=1:raise RuntimeError("startup patch marker mismatch: "+old)
        code=code.replace(old,new)
    once('#include "../Packets/OpCodes.h"', '#include "../Packets/OpCodes.h"\n#include "worldsvr-ingress/DiamondNativeStartupV23.h"')
    once('int DoProcessDataCtx(void* pProcessLayer, PROCESSDATACONTEXT* pProcessDataCtx) {',
         'int DoProcessDataCtx(void* pProcessLayer, PROCESSDATACONTEXT* pProcessDataCtx) {\n    diamond_v23::NoteDispatcherEntry();')
    once('((void(*)())oOpenProcedure)();','((void(*)())oOpenProcedure)();\n        diamond_v23::AfterOriginalOpenProcedure();')
    proc.write_text(code)
    (deps/"entry.cpp").write_text(ENTRY)
    (deps/"smoke.cpp").write_text(SMOKE)
    out=work/"build";out.mkdir()
    container=["docker","run","--rm","--network","none","--read-only",
               "--tmpfs","/tmp:rw,nosuid,size=512m",
               "--mount","type=bind,src="+str(cloned)+",dst=/v14,readonly",
               "--mount","type=bind,src="+str(deps)+",dst=/diamond,readonly",
               "--mount","type=bind,src="+str(out)+",dst=/result",IMAGE]
    version=run(container+["g++-14","-dumpfullversion"]).strip()
    if version!="14.2.0":raise RuntimeError("wrong compiler")
    orig=sorted("/v14/"+p.relative_to(SRC).as_posix() for p in SRC.rglob("*.cpp") if p.relative_to(SRC).as_posix() not in {"hooks/Handlers/C2SHandler.cpp","hooks/Packets/EventPassInventoryPersistV282.cpp"})
    if len(orig)!=33:raise RuntimeError("original translation unit count mismatch")
    units=["/diamond/"+p for p in UNITS]
    flags=["g++-14","-std=c++17","-O2","-I/diamond"]
    libs=["-ldl","-lpthread","-lodbc"]
    print("V23_BUILD_REAL_CHAIN",flush=True)
    run(container+flags+["/diamond/smoke.cpp",*units,"-o","/result/smoke",*libs],timeout=900)
    run(container+["/result/smoke"])
    print("V23_REAL_LINK_DENIAL_SMOKE=PASS",flush=True)
    run(container+flags+["/diamond/worldsvr-ingress/test_native_rankup_v20.cpp","-o","/result/wiring-test"],timeout=120)
    run(container+["/result/wiring-test"])
    print("V23_WIRING_TEST=PASS",flush=True)
    name="libDiamondV23_NativeStartup_OFFLINE.so"
    run(container+flags+["-fPIC","-shared","-Wl,--no-undefined","-Wl,-soname,"+name,
        "-Wl,-rpath,/usr/lib/cabal","-o","/result/"+name,*orig,*units,"/diamond/entry.cpp",*libs],timeout=900)
    target=out/name
    symbols=run(["readelf","--dyn-syms","-W",str(target)])
    if "cabal_diamond_native_register_v23" not in symbols:raise RuntimeError("missing registration export")
    if manifest()!=(64,TREE_SHA):raise RuntimeError("original source changed")
    result={"artifact":str(target),"sha256":sha(target),"original_units":len(orig),"diamond_units":len(units)+1,
            "world_sha":WORLD_SHA,"real_chain_linked":True,"runtime_host_bound":False,"startup_hook_compiled":True,"observer_default_off":True,
            "install_allowed":False,"rankup_verified":False,"active_world_modified":False}
    (out/"REPORT.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    print("DIAMOND_V23=COMBINED_BUILD_COMPLETE")
if __name__=="__main__":
    try:main()
    except Exception as e:
        print("DIAMOND_V23=STOP "+str(e),file=sys.stderr);sys.exit(2)
