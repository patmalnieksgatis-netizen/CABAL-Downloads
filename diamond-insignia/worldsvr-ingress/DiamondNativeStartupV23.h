#pragma once
// V23: concrete OpenProcedure startup adapter for the exact active WorldSvr.
// Observation mode ONLY. It registers one native map after the original
// OpenProcedure has finished, and never calls SQL or sends a success reply.
// Default disabled; do not enable on production without a restorable test.
#include "DiamondNativeProcedureRegistrationV19.h"
#include "../native/grade2-ingress/DiamondGradeUp0BDA.h"
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <new>

namespace diamond_v23 {
inline std::mutex startupMutex;
inline bool dispatchSeen=false;
inline bool installAttempted=false;
inline std::atomic<unsigned long> observations{0};
inline void NoteDispatcherEntry() noexcept {
    // Once first dispatch observed, no further registration is possible.
    // Acquire lock on initial entry only; no lock on ordinary game path
    // after publication of first dispatch.
    static std::atomic<bool> fast{false};
    if(fast.load(std::memory_order_acquire))return;
    std::lock_guard<std::mutex> guard(startupMutex);
    dispatchSeen=true;
    fast.store(true,std::memory_order_release);
}
inline bool Mapped(std::uintptr_t addr,std::size_t n,bool writable,bool executable) noexcept {
    if(n==0 || addr+n<addr)return false;
    auto* f=std::fopen("/proc/self/maps","r");
    if(!f)return false;
    char line[512];bool ok=false;
    while(std::fgets(line,sizeof(line),f)){
        unsigned long a=0,b=0;char perms[5]{};
        if(std::sscanf(line,"%lx-%lx %4s",&a,&b,perms)!=3)continue;
        if(addr>=a && addr+n<=b && perms[0]=='r' &&
           (!writable || perms[1]=='w') && (!executable || perms[2]=='x')){
            ok=true;break;
        }
    }
    std::fclose(f);return ok;
}
template<std::size_t N> inline bool Signature(std::uintptr_t addr,const unsigned char(&s)[N]) noexcept {
    return Mapped(addr,N,false,true) && std::memcmp(reinterpret_cast<const void*>(addr),s,N)==0;
}
inline int Observe(void*,diamond_v19::ContextPrefix* ctx) noexcept {
    if(!ctx || !ctx->user || !ctx->frame)return -1;
    const auto parsed=diamond_v291::gradeup0bda::ParseC2s(ctx->frame,ctx->length);
    if(parsed.state!=diamond_v291::gradeup0bda::PacketState::Candidate)return -1;
    const auto seq=observations.fetch_add(1,std::memory_order_relaxed)+1;
    // Log only packet shape, never account identifiers, pointers or contents.
    if(seq<=16)std::fprintf(stderr,"DIAMOND_V23_NATIVE_INGRESS seq=%lu bytes=%zu entries=%u NO_MUTATION\n",
       seq,ctx->length,static_cast<unsigned>(parsed.count));
    // No gameplay success, no SQL, no replay. Observation mode does not
    // implement a client response. Normal native dispatcher handles return.
    return -1;
}
inline void AfterOriginalOpenProcedure() noexcept {
    const char* enabled=std::getenv("CABAL_DIAMOND_V23_NATIVE_OBSERVER");
    if(!enabled || std::strcmp(enabled,"1")!=0)return;
    std::lock_guard<std::mutex> guard(startupMutex);
    if(dispatchSeen || installAttempted){
        std::fprintf(stderr,"DIAMOND_V23_NATIVE_REGISTER=BLOCKED_LATE_OR_REPEAT\n");return;
    }
    installAttempted=true;
    // Fixed-build signatures verified from the owner's actual ELF disassembly.
    // These guards complement, not replace, the exact ELF hash check in the
    // deployment preflight. Never use on another executable.
    constexpr unsigned char ctorSig[]={0x55,0x48,0x89,0xe5,0x41,0x54,0x53,0x48,0x89,0xfb,0x48,0xc7,0x07,0,0,0,0};
    constexpr unsigned char insertSig[]={0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,0x41,0x55,0x41,0x54,0x49,0x89,0xf7};
    constexpr unsigned char callSig[]={0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,0x48,0x8d,0x45,0xc0};
    using namespace diamond_v19;
    if(!Signature(kNativeCtor,ctorSig) || !Signature(kNativeVectorInsert,insertSig) ||
       !Signature(0xb49750,callSig) ||
       !Mapped(kNativeUserTable,kSlots*sizeof(void*),true,false) ||
       !Mapped(kNativeOtherTable,kSlots*sizeof(void*),false,false)){
        std::fprintf(stderr,"DIAMOND_V23_NATIVE_REGISTER=BLOCKED_SIGNATURE_OR_MAP\n");return;
    }
    auto** user=reinterpret_cast<void**>(kNativeUserTable);
    auto* const* other=reinterpret_cast<void* const*>(kNativeOtherTable);
    if(!user[kPlatinum] || !user[kPlatinumCancel] ||
       user[kPlatinum]==user[kPlatinumCancel] || user[kDiamond] || other[kDiamond]){
        std::fprintf(stderr,"DIAMOND_V23_NATIVE_REGISTER=BLOCKED_COLLISION_OR_PLATINUM\n");return;
    }
    // Confirm expected existing Platinum callback, not just nonnull table.
    if(!Mapped(reinterpret_cast<std::uintptr_t>(user[kPlatinum]),kMapBytes,false,false)){
        std::fprintf(stderr,"DIAMOND_V23_NATIVE_REGISTER=BLOCKED_PLATINUM_MAP\n");return;
    }
    auto* first=Read<Handler*>(user[kPlatinum],0);
    if(!first || !Mapped(reinterpret_cast<std::uintptr_t>(first),sizeof(Handler),false,false) ||
       reinterpret_cast<std::uintptr_t>(*first)!=0xa40f00){
        std::fprintf(stderr,"DIAMOND_V23_NATIVE_REGISTER=BLOCKED_PLATINUM_HANDLER\n");return;
    }
    // Use the process's normal C++ allocator and actual native constructor.
    // Native destructor ABI not yet verified: after a successful ctor any
    // failed candidate is retained unpublished (max one per process).
    // This deliberately avoids guessing a destructor or freeing a live timer.
    static void* quarantined=nullptr;
    void* map=nullptr;bool constructed=false;
    try {
        map=::operator new(kMapBytes);
        std::memset(map,0,kMapBytes);
        reinterpret_cast<void(*)(void*)>(kNativeCtor)(map);
        constructed=true;
        if(Read<Handler*>(map,0) || Read<Handler*>(map,8) || Read<Handler*>(map,16) ||
           Read<std::uint8_t>(map,0x20)!=1 || Read<std::uint32_t>(map,0x24)!=0 ||
           Read<std::uint64_t>(map,0x28)!=0){
            quarantined=map;std::fprintf(stderr,"DIAMOND_V23_NATIVE_REGISTER=BLOCKED_CTOR_LAYOUT\n");return;
        }
        Handler entry=&Observe;
        reinterpret_cast<void(*)(void*,Handler*,const Handler*)>(kNativeVectorInsert)(map,nullptr,&entry);
        auto* start=Read<Handler*>(map,0);
        auto* end=Read<Handler*>(map,8);
        auto* capacity=Read<Handler*>(map,16);
        if(!start || !end || !capacity ||
           reinterpret_cast<std::uintptr_t>(end)-reinterpret_cast<std::uintptr_t>(start)!=sizeof(Handler) ||
           reinterpret_cast<std::uintptr_t>(capacity)<reinterpret_cast<std::uintptr_t>(end) ||
           *start!=entry || user[kDiamond] || other[kDiamond]){
            quarantined=map;std::fprintf(stderr,"DIAMOND_V23_NATIVE_REGISTER=BLOCKED_INSERT\n");return;
        }
        static constexpr char name[]="CSC_DIAMOND_GRADEUP: V23 OBSERVE";
        Write<const char*>(map,0x18,name);
        Write<std::uint8_t>(map,0x20,1);
        user[kDiamond]=map;
        std::fprintf(stderr,"DIAMOND_V23_NATIVE_REGISTER=OBSERVE_ONLY opcode=3034 SQL=OFF REPLY=OFF\n");
    }catch(...){
        if(constructed)quarantined=map;
        else if(map)::operator delete(map);
        std::fprintf(stderr,"DIAMOND_V23_NATIVE_REGISTER=BLOCKED_EXCEPTION\n");
    }
    (void)quarantined;
}
} // namespace diamond_v23
