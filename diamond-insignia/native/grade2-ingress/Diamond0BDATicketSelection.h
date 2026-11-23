#pragma once
// 0BDA client-listed WorldSvr inventory slot proposals -> exactly 100
// authoritative ticket units. READ ONLY: a plan, never an inventory write.
// The host must hold an authenticated owner/character lock while obtaining
// a truthful 48-byte live-inventory snapshot and a verified item catalog.
#include "DiamondGradeUp0BDA.h"
#include "DiamondWorld48TicketUnits.h"
#include <array>
#include <cstddef>
#include <cstdint>

namespace diamond_v291::gradeup0bda {
constexpr std::size_t kWorldInventorySlots=kWorldInventoryMaxSlot+1u; // 0..521
constexpr std::uint32_t kRequiredRankUpTickets=100u;
// Verified from the running EP36_291_TEST exact WorldSvr, Nov 23 2026.
// For B0 + stack setting 999, original 0xAE0E90 falls through to 1,
// which may NOT represent the actual quantity of a stackable item.
constexpr std::uint32_t kObservedTicketKind38=0xB0u;
constexpr std::int32_t kObservedTicketStack3C=999;
struct AttestedInventory {
    const void* authenticatedWorldSession=nullptr;
    const void* boundWorldSession=nullptr;
    const std::uint8_t* trustedRecords=nullptr;
    std::size_t trustedRecordsBytes=0;
    bool acquiredUnderExclusiveOwnerLock=false;
    bool recordsVerifiedFromWorldSession=false;
    // CRITICAL: still UNPROVEN whether 0BDA's u16 list selects ticket
    // slots. Only an independently verified WorldSvr grade-up handler
    // or isolated gameplay trace may set these true. Default false.
    bool opcode0bdaSelectionMeansTicketSlotsVerified=false;
    bool selectionSemanticsBoundToGradeUpVerified=false;
    std::uint32_t registeredUserNum=0;
    std::uint32_t registeredCharacterIdx=0;
    std::uint32_t trustedRevision=0;
    AttestedItemMetadata itemCatalog{};
};
enum class SelectionVerdict : std::uint8_t {
    InvalidPacket, MissingOwnerAuthority, UnverifiedSelectionSemantics,
    WrongSnapshotSize, SlotOutOfRange,
    DuplicateSlot, InvalidTicketRecord, ItemMetadataMissing,
    UnsupportedStackQuantityEncoding,
    ZeroOrInvalidTicketCount, InsufficientTickets, ExactDebitPlan
};
struct SlotDebit {
    std::uint16_t slot=0;
    std::uint32_t availableBefore=0;
    std::uint32_t debitPlanned=0;
    std::uint32_t expectedRemaining=0;
    bool removeEmptyRecord=false;
};
struct TicketDebitPlan {
    SelectionVerdict status=SelectionVerdict::InvalidPacket;
    std::uint16_t selectedCount=0;
    std::uint32_t selectedUnits=0;
    std::uint32_t exactPlannedDebit=0;
    std::array<SlotDebit,kMaxAttestableEntries> slots{};
    bool mayMutateLiveInventory=false;  // always false: plan only
    bool durableTransactionCommitted=false;
};
// WARNING: 0BDA inventory-list meaning is not yet proven. Default
// behavior MUST return UnverifiedSelectionSemantics, not a debit plan.
// Validates EVERY submitted slot before planning a debit. Does not consume
// ticket units, overwrite records, derive item counts from client, or
// authorize an S2C success. The returned plan is bound to the snapshot at
// this moment only; the actual GameData backend must recheck under owner lock.
TicketDebitPlan PlanTicketDebit(const Candidate& untrusted,
                               const AttestedInventory& trusted) noexcept;
} // namespace diamond_v291::gradeup0bda
