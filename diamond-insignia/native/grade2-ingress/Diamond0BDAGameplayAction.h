#pragma once
// Real WorldSvr host-facing 0BDA grade-up action: the authoritative request,
// ticket-selection plan and Diamond rules are checked in ONE owner-locked path.
// It never trusts a client-selected quantity, invents a DB/GameData write,
// sends an unproven S2C packet, or patches WorldSvr's procedure registry.
#include "DiamondGradeUp0BDA.h"
#include "Diamond0BDATicketSelection.h"
#include "../diamond_rules.hpp"
#include <cstddef>
#include <cstdint>

namespace diamond_v291::gradeup0bda {
struct LockedGameOwner {
    const void* worldUserCtx=nullptr;
    std::uint32_t registeredUserNum=0;
    std::uint32_t registeredCharacterIdx=0;
    std::uint64_t sessionGeneration=0;
    std::uint64_t durableIntentId=0;
    bool ownerExclusiveLockHeld=false;
    bool exactGradeUpCommandSemanticsVerified=false;
    bool actualGameDataAtomicBackendVerified=false;
    bool authoritativePlatinumStateVerified=false;
    bool authoritativeWexpVerified=false;
    bool authoritativeTotalTicketCountVerified=false;
    diamond::TrustedState before{};
    AttestedInventory selectedInventory{};
};
struct AtomicGradeUpRequest {
    std::uint64_t durableIntentId=0;
    std::uint32_t userNum=0;
    std::uint32_t characterIdx=0;
    std::uint64_t sessionGeneration=0;
    diamond::TrustedState expectedBefore{};
    diamond::TrustedState intendedAfter{};
    TicketDebitPlan selectedTicketDebit{};
};
enum class AtomicCommitState : std::uint8_t {
    RolledBackOrRejected, CommittedNeedsIndependentSaveVerification,
    InDoubtRecoveryRequired
};
struct AtomicCommitOutcome {
    AtomicCommitState state=AtomicCommitState::RolledBackOrRejected;
    std::uint64_t recordedIntentId=0;
    std::uint32_t appliedRevision=0;
};
// IMPLEMENTATION REQUIRED IN MATCHED REAL WorldSvr + actual GameData/DBAgent.
// Commit MUST be idempotent by (characterIdx, intentId), verify that the
// character is still at expected revision, debit 30k WExp and exactly 100
// units of item 33554961 from the selected *server-owned* inventory slots,
// save rank grade 2, atomically persist to actual GameData, then return status.
// On any partial write or timeout, report InDoubtRecoveryRequired and suspend
// the character until independent reconciliation. A callback that writes only
// to Server01_DiamondLab shadow tables is INVALID.
using AtomicCommitCallback = AtomicCommitOutcome (*)(
    void* trustedHostContext,const void* worldUserCtx,
    const AtomicGradeUpRequest&) noexcept;
struct GameHost {
    std::uint32_t abiVersion=1;
    void* context=nullptr;
    AtomicCommitCallback commit=nullptr; // null: fail CLOSED
};
enum class GameActionState : std::uint8_t {
    NotDiamondCommand, InvalidPacket, MissingWorldAuthority,
    InventoryNotVerified, RuleRejected, MissingRealCommitBackend,
    RolledBack, InDoubtRecoveryRequired, CommittedPendingSaveProof
};
struct GameActionResult {
    GameActionState state=GameActionState::InvalidPacket;
    diamond::Error rule=diamond::Error::InvalidConfig;
    SelectionVerdict inventory=SelectionVerdict::InvalidPacket;
    std::uint32_t plannedTickets=0;
    std::uint64_t plannedWexp=0;
    std::uint32_t proposedRevision=0;
    // Never send an S2C from this module. It cannot prove cmd46/47 +
    // independent persisted state or the actual client reply length/fields.
    bool maySendClientSuccess=false;
};
// Call only while original WorldSvr's authoritative per-character owner lock
// is held. The host must prove its own pointers/fields under that lock.
GameActionResult PrepareAndCommitRealGradeUp(
    const void* clientFrame,std::size_t verifiedFrameBytes,
    const LockedGameOwner& lockedOwner,const GameHost& host) noexcept;
} // namespace diamond_v291::gradeup0bda
