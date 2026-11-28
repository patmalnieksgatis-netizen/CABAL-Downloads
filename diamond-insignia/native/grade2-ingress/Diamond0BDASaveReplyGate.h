#pragma once
// CABAL v291 0BDA seven-byte status encoder. The exact client reader and
// original WorldSvr seven-byte Platinum send call establish the two sides
// of this custom server implementation; EP45 serialization is not copied.
// No network send here. Production builds do not permit serialization.
#include "../world-save-barrier/DiamondWorldSaveBarrier.h"
#include <array>
#include <cstdint>
namespace diamond_v291::gradeup0bda {
constexpr std::uint16_t k0bdaServerReplyOpcode=0x0BDAu;
constexpr std::size_t k0bdaCandidateReplyBytes=7;
enum class ReplyGateResult : std::uint8_t {
    Blocked, CloneCandidateEncoded, NoWorldSaveProof, MissingResponseAbiAttestation
};
struct ReplyGate {
    ReplyGateResult result=ReplyGateResult::Blocked;
    std::array<std::uint8_t,k0bdaCandidateReplyBytes> bytes{};
    bool canSendToClient=false; // clone flag + both independent ABI proofs only
};
// The staging/clone encoder REQUIRES reconciled durable GameData/WExp plus
// committed receipt, exact client reader and matched native send ABI.
ReplyGate StageCandidateSuccess(const DiamondWorldSaveBarrier& durableSave,
                                bool clientStatusReadAt6Verified,
                                bool matchingNativeSendAbiVerified) noexcept;
} // namespace diamond_v291::gradeup0bda
