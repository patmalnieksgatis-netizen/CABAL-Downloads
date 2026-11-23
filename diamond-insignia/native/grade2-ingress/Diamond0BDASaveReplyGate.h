#pragma once
// Candidate CABAL v291 0BDA S2C minimal client-status reply encoder.
// The client callback reads [packet+6] status; this is NOT proof that the
// original newer WorldSvr ever emits exactly this seven-byte wire shape.
// No network send and production builds never permit success serialization.
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
    bool canSendToClient=false; // ALWAYS false until real S2C ABI is proved
};
// The staging/clone encoder REQUIRES reconciled durable GameData/WExp plus
// committed receipt and a separate runtime-proven candidate response ABI.
// No call site in this repository sends the bytes to real clients.
ReplyGate StageCandidateSuccess(const DiamondWorldSaveBarrier& durableSave,
                                bool clientStatusReadAt6Verified,
                                bool matchingRuntimeS2cResponseAbiVerified) noexcept;
} // namespace diamond_v291::gradeup0bda
