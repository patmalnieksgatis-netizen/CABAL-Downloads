#pragma once
// Shared, ODBC-independent WorldSvr exclusive-session lease contract.
// Existing v14 Lab bridge and new 0BDA GameData ingress both consume
// the SAME authority, so no duplicate synthetic account identity source.
#include <cstdint>
namespace diamond_v291 {
struct LockedWorldSession {
    const void* userData=nullptr;
    std::uint32_t registeredUserNum=0;
    std::uint32_t registeredCharacterIdx=0;
    std::uint64_t sessionGeneration=0;
    std::int64_t labNonce=0; // historic Lab adapter only; no live credential
};
class WorldSessionAuthority {
public:
    virtual ~WorldSessionAuthority()=default;
    // WorldSvr registry lease must guarantee readability for USERCONTEXT
    // >=0xF0 bytes and USERDATACONTEXT >=0xA28 bytes while the lock is held.
    // It must block disconnect, character switch, and conflicting saves.
    virtual bool AcquireExclusive(const void* worldUserCtx,
                                  LockedWorldSession& result) noexcept=0;
    virtual void ReleaseExclusive(const void* worldUserCtx) noexcept=0;
};
} // namespace diamond_v291
