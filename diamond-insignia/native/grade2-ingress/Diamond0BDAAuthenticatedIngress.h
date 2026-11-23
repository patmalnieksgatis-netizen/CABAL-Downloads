#pragma once
// Trusted WorldSvr 0x0BDA ingress using the EXISTING v14 owner reader.
// No incoming packet UserNum or CharacterIdx is trusted. No SQL or socket.
// This adapter is not a procedure registry hook; that remains unimplemented.
#include "Diamond0BDAGameplayAction.h"
#include "../world-session-bridge/DiamondWorldSessionBridge.h"
#include <cstddef>
#include <cstdint>

namespace diamond_v291::gradeup0bda {
struct AttestedLiveWorldUser {
    const void* worldUserCtx=nullptr;
    const void* userData=nullptr;
    std::uint32_t userNum=0;
    std::uint32_t characterIdx=0;
    std::uint64_t sessionGeneration=0;
};
struct LockedDataSource {
    // Server host must verify the exact WorldSvr data layout and owner
    // registry before this point. The adapter validates the v14 offsets,
    // but an offline test cannot prove the real v291 runtime's liveness.
    bool exactWorldSvrLayoutAndHashVerified=false;
    bool (*readLockedState)(void* host,
                            const AttestedLiveWorldUser& user,
                            LockedGameOwner& result) noexcept=nullptr;
    void* hostContext=nullptr;
};
struct AuthenticatedIngressHost {
    // AcquireExclusive must prevent disconnect and concurrent char
    // changes/saves, guarantee readability of USERCONTEXT[0..0xF0]
    // and USERDATACONTEXT[0..0xA28], and remain held through DB commit.
    diamond_v291::WorldSessionAuthority* authority=nullptr;
    LockedDataSource data{};
    GameHost game{};
};
GameActionResult ExecuteAuthenticated0BDA(
    const void* worldUserCtx,
    const void* clientFrame,
    std::size_t verifiedFrameBytes,
    const AuthenticatedIngressHost& host) noexcept;
} // namespace diamond_v291::gradeup0bda
