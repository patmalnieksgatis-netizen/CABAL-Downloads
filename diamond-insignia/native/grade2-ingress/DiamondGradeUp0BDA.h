#pragma once
// CABAL v291 grade-2 candidate 0x0BDA. Exact client static pairing with
// Platinum 0x0B10 is verified; real grade2 gameplay/commit ABI is NOT.
// Offline-only, normal builds never run a transaction.
#include "../diamond_transaction.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
namespace diamond_v291::gradeup0bda {
constexpr std::uint16_t kOpcode=0x0BDAu;
constexpr std::size_t kMaxAttestableEntries=128;
enum class PacketState : std::uint8_t { Other, Invalid, Candidate };
struct Candidate {
    PacketState state=PacketState::Invalid;
    std::uint16_t count=0;
    std::array<std::uint16_t,kMaxAttestableEntries> rawEntries{};
};
Candidate ParseC2s(const void*,std::size_t) noexcept;

// Only the authenticated WorldSvr / native inventory provider may supply
// these fields. No caller may fill them from packet bytes or a guessed ID
// range. The authoritative adapter must independently verify EACH selected
// entry and the exact 100-ticket debit before enabling clone tests.
struct WorldProof {
    bool authenticatedSession=false;
    bool grade2ServerCatalogVerified=false;
    bool gradeUpSemanticsVerified=false;    // runtime button/action proof
    bool entriesAuthoritativelyMatched=false;
    bool actualGameDataWexpBackendVerified=false;
    const void* boundWorldSession=nullptr;
    std::uint32_t userNum=0;
    std::uint64_t sessionNonce=0;
    std::uint32_t revision=0;
    std::uint16_t expectedCount=0;
    std::array<std::uint16_t,kMaxAttestableEntries> serverEntries{};
};
enum class Route : std::uint8_t {
    Original, Invalid, Disabled, Rejected, CloneBackendAppliedPendingSaveProof
};
struct Result {
    Route route=Route::Invalid;
    diamond::OperationResult transaction{};
    bool maySendS2cSuccess=false; // ALWAYS false: cmd47 and durable reconciliation missing
};
// A synthetically attested clone trial is only compiled under
// DIAMOND_ENABLE_0BDA_CLONE_TRIAL. Even there, it never sends S2C.
Result ExecuteCandidate(const void*,std::size_t,const WorldProof&,
                        diamond::DiamondCommandService&) noexcept;
} // namespace diamond_v291::gradeup0bda
