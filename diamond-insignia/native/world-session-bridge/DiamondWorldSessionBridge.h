#pragma once
// Diamond Insignia v291: v14 WorldSvr session-bound entry to clone-only ODBC.
// NO WorldSvr hook, no networking, no production database writes.
// Requires a host-supplied session authority which owns the WorldSvr
// registry and holds its lock through the *whole* Execute().
#include "DiamondLabOdbcBackend.h"
#include "DiamondWorldSessionAuthority.h"
#include <cstdint>
#include <string>
namespace diamond_v291 {
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
