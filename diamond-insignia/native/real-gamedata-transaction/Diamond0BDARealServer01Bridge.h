#pragma once
// The single combined 0BDA WorldSvr -> real Server01 ODBC entrypoint.
// No procedure-map patching, no socket S2C and no silent fallthrough.
// Host must provide independent live proof and exclusive owner lease.
#include "DiamondRealGameDataOdbc.h"
#include "../grade2-ingress/Diamond0BDAAuthenticatedIngress.h"

namespace diamond_v291::real_gamedata {
struct Real0BDAHost {
    diamond_v291::WorldSessionAuthority* authority=nullptr;
    diamond_v291::gradeup0bda::LockedDataSource ownerState{};
    RealServer01OdbcContext* transaction=nullptr;
    diamond_v291::gradeup0bda::RealGameDataBackendContract sqlProof{};
};
// An omitted reservation is valid for disabled-host startup probes only.
// Every actionable rank-up needs the intent already owned by its completion.
diamond_v291::gradeup0bda::GameActionResult Execute0BDARealServer01(
    const void* worldUserCtx,const void* clientFrame,
    std::size_t verifiedFrameBytes,const Real0BDAHost& host,
    std::uint64_t reservedIntent=0) noexcept;
} // namespace diamond_v291::real_gamedata
