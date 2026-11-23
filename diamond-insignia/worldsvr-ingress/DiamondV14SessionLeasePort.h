#pragma once
// WorldSvr v14 session-to-Diamond ABI-v3 bridge. SYNTHETIC CLONE ONLY.
// Requires an EXTERNAL authoritative WorldSvr registry (not implemented here)
// and an independent, server-owned Merit catalog selector. Never use client
// packet fields as authoritative identity or catalog state.
#include "DiamondBoundIngress.h"
#include "../native/world-session-bridge/DiamondWorldSessionBridge.h"
#include <cstdint>

namespace diamond_v291 {
struct CatalogSelection {
    std::uint32_t trustedRevision=0;
    std::uint32_t serverMasteryId=0;
    std::uint32_t serverSecondDword=0;
    bool isDiamondGrade=false;
    bool serverMeritSelectorIsDiamond=false;
};

// Implemented by an independently trusted WorldSvr catalog, never by a
// C2S ID-range check. Invoked while the registry lease is held.
class MeritCatalogAuthority {
public:
    virtual ~MeritCatalogAuthority()=default;
    virtual bool ReadUnderExclusiveLease(
        const LockedWorldSession& lease,const SessionProof& proof,
        CatalogSelection& out) noexcept=0;
};

class DiamondV14SessionLeasePort final {
public:
    DiamondV14SessionLeasePort(WorldSessionAuthority& sessions,
                              MeritCatalogAuthority& catalog) noexcept
        :sessions_(sessions),catalog_(catalog){}
    DiamondV14SessionLeasePort(const DiamondV14SessionLeasePort&)=delete;
    DiamondV14SessionLeasePort& operator=(const DiamondV14SessionLeasePort&)=delete;

    static int Acquire(void* authorityContext,const void* worldUserCtx,
       const DiamondIngress::Observation* candidate,void** leaseToken,
       DiamondBoundIngress::VerifiedIdentity* result) noexcept;
    static void Release(void* authorityContext,void* leaseToken) noexcept;
private:
    WorldSessionAuthority& sessions_;
    MeritCatalogAuthority& catalog_;
};
} // namespace diamond_v291
