#pragma once
// V19: native WorldSvr registration contract, based on owner ELF evidence.
// No absolute-address dereference, no automatic registration or SQL.
// Bind ONLY during verified startup before dispatch threads can run.
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace diamond_v19 {
constexpr std::size_t kMapBytes=0x50;
constexpr std::size_t kSlots=4000;
constexpr std::size_t kDiamond=0x0BDA;
constexpr std::size_t kPlatinum=0x0B10;
constexpr std::size_t kPlatinumCancel=0x0B13;
constexpr std::uintptr_t kNativeCtor=0x63f300;
constexpr std::uintptr_t kNativeVectorInsert=0x641b10;
constexpr std::uintptr_t kNativeUserTable=0x235f8c0;
constexpr std::uintptr_t kNativeOtherTable=0x2357bc0;
struct ContextPrefix {
    void* user;
    const void* frame;
    std::size_t length;
};
static_assert(sizeof(void*)==8 && sizeof(std::size_t)==8);
static_assert(offsetof(ContextPrefix,length)==0x10);
using Handler=int(*)(void*,ContextPrefix*);
struct MapPrefix {
    Handler* start;
    Handler* end;
    Handler* capacity;
    const char* name;
    std::uint8_t locking;
};
static_assert(offsetof(MapPrefix,name)==0x18);
static_assert(offsetof(MapPrefix,locking)==0x20);
struct Host {
    // These must be independently verified by the owner implementation.
    // A test mock or hash alone cannot establish real startup exclusivity.
    bool exactElfVerified=false;
    bool startupBeforeAnyDispatch=false;
    bool nativeObjectLifetimeVerified=false;
    bool realGameBackendReady=false;
    void** userTable=nullptr;
    void* const* otherTable=nullptr;
    std::size_t readableSlots=0;
    // createMap MUST allocate 0x50 bytes via native C++ allocation and
    // call native constructor, including its ACE timer. destroyMap must
    // match native destructor and allocator, including failure cleanup.
    void* (*createMap)() noexcept=nullptr;
    void (*destroyMap)(void*) noexcept=nullptr;
    // Native insert signature is (vector address, iterator, &handler).
    bool (*append)(void*,Handler) noexcept=nullptr;
};
enum class Status {
    Blocked, PlatinumMissing, Collision, AllocationFailed, InvalidMap,
    InsertFailed, Installed
};
template<class T> inline T Read(const void* p,std::size_t off) noexcept {
    T v{};std::memcpy(&v,static_cast<const unsigned char*>(p)+off,sizeof(v));return v;
}
template<class T> inline void Write(void* p,std::size_t off,T v) noexcept {
    std::memcpy(static_cast<unsigned char*>(p)+off,&v,sizeof(v));
}
// Caller must own a real startup barrier for both registry tables.
// Map is never published partially initialized. No fallback to another
// handler after a Diamond write, no changes to existing Platinum slots.
inline Status Register(const Host& h,Handler handler) noexcept {
    if(!h.exactElfVerified || !h.startupBeforeAnyDispatch ||
       !h.nativeObjectLifetimeVerified || !h.realGameBackendReady ||
       !h.userTable || !h.otherTable || h.readableSlots<kSlots ||
       !h.createMap || !h.destroyMap || !h.append || !handler)
        return Status::Blocked;
    if(!h.userTable[kPlatinum] || !h.userTable[kPlatinumCancel] ||
       h.userTable[kPlatinum]==h.userTable[kPlatinumCancel])
        return Status::PlatinumMissing;
    if(h.userTable[kDiamond] || h.otherTable[kDiamond])
        return Status::Collision;
    auto* map=h.createMap();
    if(!map)return Status::AllocationFailed;
    if(Read<Handler*>(map,0) || Read<Handler*>(map,8) ||
       Read<Handler*>(map,16) || Read<std::uint8_t>(map,0x20)!=1 ||
       Read<std::uint32_t>(map,0x24)!=0 || Read<std::uint64_t>(map,0x28)!=0){
        h.destroyMap(map);return Status::InvalidMap;
    }
    if(!h.append(map,handler)){
        h.destroyMap(map);return Status::InsertFailed;
    }
    const auto first=Read<Handler*>(map,0);
    const auto last=Read<Handler*>(map,8);
    const auto cap=Read<Handler*>(map,16);
    if(!first || !last || !cap ||
       reinterpret_cast<std::uintptr_t>(last)-reinterpret_cast<std::uintptr_t>(first)!=sizeof(Handler) ||
       reinterpret_cast<std::uintptr_t>(cap)<reinterpret_cast<std::uintptr_t>(last) ||
       *first!=handler){
        h.destroyMap(map);return Status::InvalidMap;
    }
    static constexpr char name[]="CSC_DIAMOND_GRADEUP: v291";
    Write<const char*>(map,0x18,name);
    Write<std::uint8_t>(map,0x20,1);
    if(h.userTable[kDiamond] || h.otherTable[kDiamond]){
        h.destroyMap(map);return Status::Collision;
    }
    h.userTable[kDiamond]=map;
    return Status::Installed;
}
} // namespace diamond_v19
