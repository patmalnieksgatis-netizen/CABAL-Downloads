#!/usr/bin/env python3
"""Standalone startup adapter. Build + synthetic forwarding test + read-only ELF evidence.
No changes to the active game, launcher, core, SQL or supervisor."""
import pathlib,sys,subprocess,hashlib,tempfile,zipfile,json,re,collections
IMAGE="sha256:2805f2cd7dacf0547b8762437009a4814ab0c352f913b15c87b3e856f04528bb"
BASE="6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab"
WORLD="caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3"
V27=pathlib.Path("/tmp/cabal-diamond-v27-0tr0mzt9/build/Diamond291_V27_OFFLINE.so")
V27_SHA="6d97091d3019464b15c5f8fe4a11e7cf490c0ed55660c3108936c2ec7fd4e965"
HEADER="#pragma once\n// V28: standalone OpenProcedure startup adapter for the exact active WorldSvr.\n// Observation mode ONLY. It registers one native map after the original\n// OpenProcedure has finished, and never calls SQL or sends a success reply.\n// Default disabled; do not enable on production without a restorable test.\n#include \"DiamondNativeProcedureRegistrationV19.h\"\n#include \"../native/grade2-ingress/DiamondGradeUp0BDA.h\"\n#include <atomic>\n#include <cstdio>\n#include <cstdlib>\n#include <cstring>\n#include <mutex>\n#include <new>\n\nnamespace diamond_v28 {\ninline std::mutex startupMutex;\ninline bool installAttempted=false;\ninline std::atomic<unsigned long> observations{0};\ninline bool Mapped(std::uintptr_t addr,std::size_t n,bool writable,bool executable) noexcept {\n    if(n==0 || addr+n<addr)return false;\n    auto* f=std::fopen(\"/proc/self/maps\",\"r\");\n    if(!f)return false;\n    char line[512];bool ok=false;\n    while(std::fgets(line,sizeof(line),f)){\n        unsigned long a=0,b=0;char perms[5]{};\n        if(std::sscanf(line,\"%lx-%lx %4s\",&a,&b,perms)!=3)continue;\n        if(addr>=a && addr+n<=b && perms[0]=='r' &&\n           (!writable || perms[1]=='w') && (!executable || perms[2]=='x')){\n            ok=true;break;\n        }\n    }\n    std::fclose(f);return ok;\n}\ntemplate<std::size_t N> inline bool Signature(std::uintptr_t addr,const unsigned char(&s)[N]) noexcept {\n    return Mapped(addr,N,false,true) && std::memcmp(reinterpret_cast<const void*>(addr),s,N)==0;\n}\ninline int Observe(void*,diamond_v19::ContextPrefix* ctx) noexcept {\n    if(!ctx || !ctx->user || !ctx->frame)return -1;\n    const auto parsed=diamond_v291::gradeup0bda::ParseC2s(ctx->frame,ctx->length);\n    if(parsed.state!=diamond_v291::gradeup0bda::PacketState::Candidate)return -1;\n    const auto seq=observations.fetch_add(1,std::memory_order_relaxed)+1;\n    // Log only packet shape, never account identifiers, pointers or contents.\n    if(seq<=16)std::fprintf(stderr,\"DIAMOND_V28_NATIVE_INGRESS seq=%lu bytes=%zu entries=%u NO_MUTATION\\n\",\n       seq,ctx->length,static_cast<unsigned>(parsed.count));\n    // No gameplay success, no SQL, no replay. Observation mode does not\n    // implement a client response. Normal native dispatcher handles return.\n    return -1;\n}\ninline void AfterOriginalOpenProcedure() noexcept {\n    const char* enabled=std::getenv(\"CABAL_DIAMOND_V28_NATIVE_OBSERVER\");\n    if(!enabled || std::strcmp(enabled,\"1\")!=0)return;\n    std::lock_guard<std::mutex> guard(startupMutex);\n    if(installAttempted){\n        std::fprintf(stderr,\"DIAMOND_V28_NATIVE_REGISTER=BLOCKED_LATE_OR_REPEAT\\n\");return;\n    }\n    installAttempted=true;\n    // Fixed-build signatures verified from the owner's actual ELF disassembly.\n    // These guards complement, not replace, the exact ELF hash check in the\n    // deployment preflight. Never use on another executable.\n    constexpr unsigned char ctorSig[]={0x55,0x48,0x89,0xe5,0x41,0x54,0x53,0x48,0x89,0xfb,0x48,0xc7,0x07,0,0,0,0};\n    constexpr unsigned char insertSig[]={0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,0x41,0x55,0x41,0x54,0x49,0x89,0xf7};\n    constexpr unsigned char callSig[]={0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,0x48,0x8d,0x45,0xc0};\n    using namespace diamond_v19;\n    if(!Signature(kNativeCtor,ctorSig) || !Signature(kNativeVectorInsert,insertSig) ||\n       !Signature(0xb49750,callSig) ||\n       !Mapped(kNativeUserTable,kSlots*sizeof(void*),true,false) ||\n       !Mapped(kNativeOtherTable,kSlots*sizeof(void*),false,false)){\n        std::fprintf(stderr,\"DIAMOND_V28_NATIVE_REGISTER=BLOCKED_SIGNATURE_OR_MAP\\n\");return;\n    }\n    auto** user=reinterpret_cast<void**>(kNativeUserTable);\n    auto* const* other=reinterpret_cast<void* const*>(kNativeOtherTable);\n    if(!user[kPlatinum] || !user[kPlatinumCancel] ||\n       user[kPlatinum]==user[kPlatinumCancel] || user[kDiamond] || other[kDiamond]){\n        std::fprintf(stderr,\"DIAMOND_V28_NATIVE_REGISTER=BLOCKED_COLLISION_OR_PLATINUM\\n\");return;\n    }\n    // Confirm expected existing Platinum callback, not just nonnull table.\n    if(!Mapped(reinterpret_cast<std::uintptr_t>(user[kPlatinum]),kMapBytes,false,false)){\n        std::fprintf(stderr,\"DIAMOND_V28_NATIVE_REGISTER=BLOCKED_PLATINUM_MAP\\n\");return;\n    }\n    auto* first=Read<Handler*>(user[kPlatinum],0);\n    if(!first || !Mapped(reinterpret_cast<std::uintptr_t>(first),sizeof(Handler),false,false) ||\n       reinterpret_cast<std::uintptr_t>(*first)!=0xa40f00){\n        std::fprintf(stderr,\"DIAMOND_V28_NATIVE_REGISTER=BLOCKED_PLATINUM_HANDLER\\n\");return;\n    }\n    // Use the process's normal C++ allocator and actual native constructor.\n    // Native destructor ABI not yet verified: after a successful ctor any\n    // failed candidate is retained unpublished (max one per process).\n    // This deliberately avoids guessing a destructor or freeing a live timer.\n    static void* quarantined=nullptr;\n    void* map=nullptr;bool constructed=false;\n    try {\n        map=::operator new(kMapBytes);\n        std::memset(map,0,kMapBytes);\n        reinterpret_cast<void(*)(void*)>(kNativeCtor)(map);\n        constructed=true;\n        if(Read<Handler*>(map,0) || Read<Handler*>(map,8) || Read<Handler*>(map,16) ||\n           Read<std::uint8_t>(map,0x20)!=1 || Read<std::uint32_t>(map,0x24)!=0 ||\n           Read<std::uint64_t>(map,0x28)!=0){\n            quarantined=map;std::fprintf(stderr,\"DIAMOND_V28_NATIVE_REGISTER=BLOCKED_CTOR_LAYOUT\\n\");return;\n        }\n        Handler entry=&Observe;\n        reinterpret_cast<void(*)(void*,Handler*,const Handler*)>(kNativeVectorInsert)(map,nullptr,&entry);\n        auto* start=Read<Handler*>(map,0);\n        auto* end=Read<Handler*>(map,8);\n        auto* capacity=Read<Handler*>(map,16);\n        if(!start || !end || !capacity ||\n           reinterpret_cast<std::uintptr_t>(end)-reinterpret_cast<std::uintptr_t>(start)!=sizeof(Handler) ||\n           reinterpret_cast<std::uintptr_t>(capacity)<reinterpret_cast<std::uintptr_t>(end) ||\n           *start!=entry || user[kDiamond] || other[kDiamond]){\n            quarantined=map;std::fprintf(stderr,\"DIAMOND_V28_NATIVE_REGISTER=BLOCKED_INSERT\\n\");return;\n        }\n        static constexpr char name[]=\"CSC_DIAMOND_GRADEUP: V28 OBSERVE\";\n        Write<const char*>(map,0x18,name);\n        Write<std::uint8_t>(map,0x20,1);\n        user[kDiamond]=map;\n        std::fprintf(stderr,\"DIAMOND_V28_NATIVE_REGISTER=OBSERVE_ONLY opcode=3034 SQL=OFF REPLY=OFF\\n\");\n    }catch(...){\n        if(constructed)quarantined=map;\n        else if(map)::operator delete(map);\n        std::fprintf(stderr,\"DIAMOND_V28_NATIVE_REGISTER=BLOCKED_EXCEPTION\\n\");\n    }\n    (void)quarantined;\n}\n} // namespace diamond_v28\n"
ADAPTER="\n#include \"worldsvr-ingress/DiamondNativeStartupV28.h\"\n#include <dlfcn.h>\n#include <unistd.h>\n#include <sys/syscall.h>\n#include <cerrno>\n#include <cstdint>\nnamespace {\nusing Open = void(*)();\nconstexpr char symbol[]=\"_ZN10ProcSystem13OpenProcedureEv\";\n}\nnamespace ProcSystem {\n__attribute__((visibility(\"default\"),noinline))\nvoid OpenProcedure() {\n    const auto caller=reinterpret_cast<std::uintptr_t>(__builtin_extract_return_addr(__builtin_return_address(0)));\n    auto next=reinterpret_cast<Open>(dlsym(RTLD_NEXT,symbol));\n    if(!next || next==&OpenProcedure) {\n        std::fprintf(stderr,\"DIAMOND_V28_OPEN=NEXT_MISSING\\n\");\n        std::abort(); // Do not silently skip the server's original initialization.\n    }\n    // Always preserve original core and its existing Costume ForceRegisterHandlers chain.\n    Dl_info info{};\n    const bool original=dladdr(reinterpret_cast<void*>(next),&info) && info.dli_fname &&\n        std::strcmp(info.dli_fname,\"/usr/lib/cabal/lib.so\")==0 &&\n        reinterpret_cast<std::uintptr_t>(next)-reinterpret_cast<std::uintptr_t>(info.dli_fbase)==0x6a30;\n    next();\n    const char* flag=std::getenv(\"CABAL_DIAMOND_V28_NATIVE_OBSERVER\");\n    if(!flag || std::strcmp(flag,\"1\")!=0)return;\n    if(!original) {\n        std::fprintf(stderr,\"DIAMOND_V28_OPEN=BLOCKED_PROVIDER\\n\");return;\n    }\n    // Do not publish unless a separately attested native startup call site\n    // is explicitly supplied. Never assume startup simply from the symbol name.\n    const char* raw=std::getenv(\"CABAL_DIAMOND_V28_STARTUP_RETURN\");\n    char* end=nullptr;errno=0;\n    auto expected=raw?std::strtoull(raw,&end,16):0;\n    if(!raw || !end || *end || errno || !expected || caller!=expected ||\n       syscall(SYS_gettid)!=getpid()) {\n        std::fprintf(stderr,\"DIAMOND_V28_OPEN=BLOCKED_STARTUP_CALLSITE\\n\");return;\n    }\n    std::fprintf(stderr,\"DIAMOND_V28_OPEN=ORIGINAL_RETURNED\\n\");\n    diamond_v28::AfterOriginalOpenProcedure();\n}\n}\n"

def run(a,timeout=120):
    p=subprocess.run(a,capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError("rc="+str(p.returncode)+" "+repr(a[:5])+"\n"+p.stderr[-8000:])
    return p.stdout
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def d(*a):return run(["docker","exec","cabal_main",*a])
def main():
    pid=d("supervisorctl","pid","WorldSvr_01_01").strip()
    if not pid.isdigit() or int(pid)<2:raise RuntimeError("WorldSvr not running")
    exe="/proc/"+pid+"/exe"
    if d("sha256sum",exe).split()[0]!=WORLD or d("sha256sum","/usr/lib/cabal/lib.so").split()[0]!=BASE:
        raise RuntimeError("live hashes differ")
    if sha(V27)!=V27_SHA:raise RuntimeError("V27 artifact changed")
    work=pathlib.Path(tempfile.mkdtemp(prefix="cabal-diamond-v28-",dir="/tmp"))
    src=work/"src";src.mkdir();out=work/"build";out.mkdir()
    with zipfile.ZipFile(sys.argv[1]) as z:
        for n in z.namelist():
            p=pathlib.PurePosixPath(n.replace("\\","/"))
            if p.is_absolute() or ".." in p.parts:raise RuntimeError("bad zip path")
            if not n.endswith(("/","\\")):
                f=src.joinpath(*p.parts);f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(z.read(n))
    (src/"worldsvr-ingress/DiamondNativeStartupV28.h").write_text(HEADER)
    (src/"adapter.cpp").write_text(ADAPTER)
    (src/"exports.map").write_text("{ global: _ZN10ProcSystem13OpenProcedureEv; local: *; };\n")
    (src/"fixture.cpp").write_text(r'''
namespace ProcSystem { void OpenProcedure(); }
static int calls=0;
void ProcSystem::OpenProcedure(){++calls;}
extern "C" void fixture_invoke(){ProcSystem::OpenProcedure();}
extern "C" int fixture_calls(){return calls;}
''')
    (src/"fixture_main.cpp").write_text(r'''
#include <cassert>
extern "C" void fixture_invoke();
extern "C" int fixture_calls();
int main(){fixture_invoke();assert(fixture_calls()==1);}
''')
    c=["docker","run","--rm","--network","none","--read-only","--tmpfs","/tmp:rw,nosuid,size=512m",
       "--mount","type=bind,src="+str(src)+",dst=/src,readonly",
       "--mount","type=bind,src="+str(out)+",dst=/out",IMAGE]
    g=["g++-14","-std=c++17","-O2","-I/src"]
    name="Diamond291_Startup_V28.so"
    run(c+g+["-shared","-fPIC","-fvisibility=hidden","-Wl,--no-undefined","-Wl,--version-script=/src/exports.map",
        "/src/adapter.cpp","/src/native/grade2-ingress/DiamondGradeUp0BDA.cpp","-ldl","-pthread","-o","/out/"+name],900)
    run(c+g+["-shared","-fPIC","/src/fixture.cpp","-o","/out/libfixture.so"])
    run(c+g+["/src/fixture_main.cpp","-L/out","-lfixture","-Wl,-rpath,$ORIGIN","-o","/out/fixture"])
    run(c+["env","LD_PRELOAD=/out/"+name,"/out/fixture"])
    # The enabled flag must still forward to the fixture and block registration
    # because it is not the exact real core provider.
    run(c+["env","LD_PRELOAD=/out/"+name,"CABAL_DIAMOND_V28_NATIVE_OBSERVER=1","/out/fixture"])
    syms=run(["readelf","--dyn-syms","-W",str(out/name)])
    exported=set()
    for l in syms.splitlines():
        w=l.split()
        if len(w)>=8 and w[0].rstrip(":").isdigit() and w[6]!="UND" and w[4] in ("GLOBAL","WEAK","UNIQUE") and w[5] in ("DEFAULT","PROTECTED"):
            exported.add(w[7])
    if exported!={"_ZN10ProcSystem13OpenProcedureEv"}:raise RuntimeError("unexpected exports "+repr(exported))
    print("V28_FORWARDING_TEST=PASS",flush=True)
    print("V28_EXPORT_ISOLATION=PASS",flush=True)
    # All existing preload libraries must remain in their actual order. Reject
    # any competing OpenProcedure definition before preparing a later trial.
    env=subprocess.run(["docker","exec","cabal_main","cat","/proc/"+pid+"/environ"],capture_output=True,check=True).stdout
    pre=[x[len(b"LD_PRELOAD="):].decode().split() for x in env.split(b"\0") if x.startswith(b"LD_PRELOAD=")]
    if len(pre)!=1:raise RuntimeError("missing actual preload list")
    providers=[]
    for lib in pre[0]:
        lines=d("nm","-D","--defined-only",lib)
        if any(x.split()[-1].split("@")[0]=="_ZN10ProcSystem13OpenProcedureEv" for x in lines.splitlines() if x.split()):
            providers.append(lib)
    print("V28_EXISTING_OPEN_PROVIDERS="+json.dumps(providers),flush=True)
    if providers!=["/usr/lib/cabal/lib.so"]:raise RuntimeError("existing OpenProcedure provider collision")
    # Find actual native call sites and preserve surrounding instructions.
    # No debugger, no process memory access, no game execution.
    lines=d("objdump","-d","-M","intel",exe).splitlines()
    sites=[]
    for i,l in enumerate(lines):
        if re.search(r"\bcall\s+(?:0x)?8eda80\b",l):
            chunk=lines[max(0,i-18):i+20]
            print("V28_NATIVE_OPEN_CALLSITE_BEGIN\n"+"\n".join(chunk)+"\nV28_NATIVE_OPEN_CALLSITE_END",flush=True)
            if i+1<len(lines):
                m=re.match(r"\s*([0-9a-f]+):",lines[i+1])
                if m:sites.append("0x"+m.group(1))
    if d("supervisorctl","pid","WorldSvr_01_01").strip()!=pid or d("sha256sum","/usr/lib/cabal/lib.so").split()[0]!=BASE or sha(V27)!=V27_SHA:
        raise RuntimeError("live baseline changed during build")
    result={"adapter":str(out/name),"sha256":sha(out/name),"v27_preserved":True,"core_unchanged":True,
        "forwarding_fixture_pass":True,"native_return_candidates":sites,"existing_open_providers":providers,
        "observer_default_off":True,"startup_exclusion_verified":False,"install_allowed":False,
        "rankup_verified":False,"active_world_modified":False}
    (out/"REPORT.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    print("DIAMOND_V28=ADAPTER_BUILD_COMPLETE")
if __name__=="__main__":
    try:main()
    except Exception as e:
        print("DIAMOND_V28=STOP "+str(e),file=sys.stderr);sys.exit(2)
