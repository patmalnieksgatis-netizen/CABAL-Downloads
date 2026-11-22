// Read-only C2S observer: ABI-preserving sidecar for the exact v14 lib.so.
// No WorldSvr patch, no customer game-data mutation, no SQL.
#include <dlfcn.h>
#include <cstdint>
#include <cstddef>
#include <atomic>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <fcntl.h>
#include <unistd.h>
#include <sys/types.h>

struct PROCESSDATACONTEXT {
    void* pUserCtx;   // observed v14 ABI offset 0x00
    char* cpPacket;  // observed v14 ABI offset 0x08
    size_t iLen;     // observed v14 ABI offset 0x10
};
static_assert(offsetof(PROCESSDATACONTEXT,cpPacket)==8,"packet ABI mismatch");
static_assert(offsetof(PROCESSDATACONTEXT,iLen)==16,"length ABI mismatch");

namespace {
using Handler = int (*)(void*,PROCESSDATACONTEXT*);
constexpr const char* kSymbol="_ZN10ProcSystem16DoProcessDataCtxEPvP18PROCESSDATACONTEXT";
std::atomic<Handler> real{nullptr};
std::atomic<unsigned> logCount{0};
std::atomic<bool> logEnabled{false};
std::atomic<bool> isWorld{false};

uint16_t u16(const unsigned char* b){return static_cast<uint16_t>(b[0])|static_cast<uint16_t>(b[1])<<8;}
uint32_t u32(const unsigned char* b){return static_cast<uint32_t>(u16(b))|static_cast<uint32_t>(u16(b+2))<<16;}

void logLine(const char* s) {
    int fd=open("/tmp/diamond_v291_sidecar.log",O_WRONLY|O_APPEND|O_CREAT|O_CLOEXEC,0644);
    if(fd<0)return;
    (void)write(fd,s,strlen(s));
    close(fd);
}

Handler resolveOriginal() {
    Handler fn=real.load(std::memory_order_acquire);
    if(fn)return fn;
    dlerror();
    fn=reinterpret_cast<Handler>(dlsym(RTLD_NEXT,kSymbol));
    if(!fn)return nullptr;
    real.store(fn,std::memory_order_release);
    return fn;
}

void observe(PROCESSDATACONTEXT* ctx) {
    if(!logEnabled.load(std::memory_order_relaxed) || !ctx || !ctx->cpPacket) return;
    // The source-validated length field must match the classic header to log.
    const size_t len=ctx->iLen;
    if(len<10 || len>512) return;
    const auto* p=reinterpret_cast<const unsigned char*>(ctx->cpPacket);
    if(u16(p)!=0xB7E2 || u16(p+2)!=len) return;
    const uint16_t opcode=u16(p+8);
    if(opcode!=0x09F3 && opcode!=0x0B10)return;
    unsigned current=logCount.fetch_add(1,std::memory_order_relaxed);
    if(current>=32)return;
    char buf[200];
    if(opcode==0x09F3 && len>=14) {
        const uint32_t id=u32(p+10);
        // candidate range requires confirmation from live client; read only.
        const int n=snprintf(buf,sizeof(buf),"DIAMOND_SIDECAR_C2S opcode=0x09F3 len=%zu mastery_id=%u passthrough=YES\n",len,id);
        if(n>0) logLine(buf);
    } else {
        const int n=snprintf(buf,sizeof(buf),"DIAMOND_SIDECAR_C2S opcode=0x%04X len=%zu passthrough=YES\n",opcode,len);
        if(n>0) logLine(buf);
    }
}
}

// Export the *exact* symbol referenced via R_X86_64_GLOB_DAT by the
// original lib.so's ProcSystem::Attach() at GOT offset 0x16f78.
namespace ProcSystem {
__attribute__((visibility("default")))
int DoProcessDataCtx(void* layer,PROCESSDATACONTEXT* ctx) {
    Handler target=resolveOriginal();
    if(!target || reinterpret_cast<void*>(target)==reinterpret_cast<void*>(&DoProcessDataCtx)){
        // No fallback to a wrong server callback: diagnostic fail-closed.
        static std::atomic<bool> once{false};
        if(!once.exchange(true)) logLine("DIAMOND_SIDECAR_ERROR original dispatcher unavailable; aborting dispatch\n");
        return -1;
    }
    if(isWorld.load(std::memory_order_relaxed)) observe(ctx);
    return target(layer,ctx);
}
}

__attribute__((constructor)) static void diamond_sidecar_init(){
    char path[512]={};
    ssize_t n=readlink("/proc/self/exe",path,sizeof(path)-1);
    if(n>0) {
        path[n]='\0';
        if(strstr(path,"WorldSvr")!=nullptr){
            isWorld.store(true,std::memory_order_relaxed);
            const char* env=getenv("CABAL_DIAMOND_SIDECAR_LOG");
            if(env && strcmp(env,"1")==0) logEnabled.store(true,std::memory_order_relaxed);
            logLine("DIAMOND_SIDECAR_LOADED;ORIGINAL_LIB_UNMODIFIED=YES\n");
        }
    }
}
