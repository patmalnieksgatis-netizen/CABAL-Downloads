#pragma once
// v291 0x0BDD grade-2 C2S candidate. Static client evidence supports the
// same successful UI refresh path as Platinum 0x0B10 (state 2 vs state 1).
// NOT a proven gameplay transaction. No hooks, no S2C wire encoder.
#include "../diamond_transaction.hpp"
#include <cstddef>
#include <cstdint>

namespace diamond_v291::grade2 {
constexpr std::uint16_t kCandidateOpcode=0x0BDDu;
constexpr std::size_t kC2sBytes=14;
constexpr std::uint32_t kInvalidClientSelector=0xFFFFFFFFu;

enum class PacketKind : std::uint8_t { Other, Invalid, Candidate };
struct CandidatePacket {
    PacketKind kind=PacketKind::Invalid;
    std::uint32_t rawClientSelector=0;
};
CandidatePacket ParseC2s(const void* data,std::size_t size) noexcept;

// These fields MUST come from a trusted WorldSvr authenticated session,
// authoritative server-side Merit catalog/selector and verified persistence
// backend, not from client packet fields or a guessed Mastery range.
struct Proof {
    bool authenticatedSession=false;
    bool catalogGrade2Verified=false;
    bool selectorSemanticVerified=false;
    bool actualInventoryWexpBackendReady=false;
    const void* boundWorldSession=nullptr;
    std::uint32_t authenticatedUserNum=0;
    std::uint64_t trustedSessionNonce=0;
    std::uint32_t trustedRevision=0;
    std::uint32_t serverVerifiedSelector=0;
};
enum class Route : std::uint8_t {
    Original, Invalid, Disabled, Rejected, BackendAppliedPendingSaveProof
};
struct Result {
    Route route=Route::Invalid;
    diamond::OperationResult transaction{};
    bool maySendS2cSuccess=false;  // always false in this module
};
// The product MUST separately verify cmd46/47, independently persisted
// inventory/WExp, receipt, and exact S2C serializer before sending success.
// Normal builds are disabled. Clone-only test harness can explicitly compile
// with DIAMOND_ENABLE_GRADE2_CLONE_TRIAL for a mock authoritative backend.
Result ExecuteCandidate(const void* data,std::size_t size,
                        const Proof& serverProof,
                        diamond::DiamondCommandService& rules) noexcept;
} // namespace diamond_v291::grade2
