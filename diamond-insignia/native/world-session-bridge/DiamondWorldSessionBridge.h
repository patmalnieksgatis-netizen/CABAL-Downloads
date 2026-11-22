#pragma once
// Diamond Insignia v291: v14 WorldSvr session-bound entry to clone-only ODBC.
// NO WorldSvr hook, no networking, no production database writes.
// Requires a host-supplied session authority which owns the WorldSvr
// registry and holds its lock through the *whole* Execute().
#include "DiamondLabOdbcBackend.h"
#include <cstdint>
#include <string>
namespace diamond_v291 {
struct LockedWorldSession {
    // These fields MUST originate from trusted WorldSvr registry, not C2S.
    const void* userData = nullptr;
    std::uint32_t registeredUserNum = 0;
    std::uint32_t registeredCharacterIdx = 0;
    std::uint64_t sessionGeneration = 0;
    std::int64_t labNonce = 0; // clone DB only; never a client credential
};
class WorldSessionAuthority {
public:
    virtual ~WorldSessionAuthority() = default;
    // Acquire MUST guarantee both memory regions are valid to read:
    // >=0xF0 bytes for userCtx and >=0xA28 bytes for userData.
    // Lock must block disconnect, character switch, and competing saves
    // until ReleaseExclusive. A true production authority is NOT present.
    virtual bool AcquireExclusive(const void* worldUserCtx,
                                  LockedWorldSession& result) noexcept = 0;
    virtual void ReleaseExclusive(const void* worldUserCtx) noexcept = 0;
};
enum class SessionProofError : std::uint8_t {
    Valid, MissingAuthority, NoLiveSession, InvalidLease,
    UserDataPointerMismatch, RegistryIdentityMismatch, OwnerReadFailure
};
struct SessionProof {
    SessionProofError error = SessionProofError::MissingAuthority;
    VerifiedSession account{};
    std::uint64_t generation = 0;
    bool Verified() const noexcept { return error==SessionProofError::Valid; }
};
// Call only under a valid WorldSessionAuthority-held exclusive lease.
SessionProof ProveWorldSessionV14(const void* worldUserCtx,
                                 const LockedWorldSession& lease) noexcept;
// TEST-CLONE ONLY; existing backend fails closed outside Server01_DiamondLab.
Result ExecuteAttestedDiamondLab(const cabal_diamond_engine* engine,
                                 WorldSessionAuthority& authority,
                                 const void* worldUserCtx,
                                 const Request& request,
                                 const std::string& odbcConnectionString);
const char* SessionProofErrorName(SessionProofError error) noexcept;
} // namespace diamond_v291
