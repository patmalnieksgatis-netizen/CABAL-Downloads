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
struct AttestedInventory {
    const void* authenticatedWorldSession=nullptr;
    const void* boundWorldSession=nullptr;
    const std::uint8_t* trustedRecords=nullptr;
    std::size_t trustedRecordsBytes=0;
    bool acquiredUnderExclusiveOwnerLock=false;
    bool recordsVerifiedFromWorldSession=false;
    std::uint32_t registeredUserNum=0;
    std::uint32_t registeredCharacterIdx=0;
    std::uint32_t trustedRevision=0;
    AttestedItemMetadata itemCatalog{};
};
enum class SelectionVerdict : std::uint8_t {
    InvalidPacket, MissingOwnerAuthority, WrongSnapshotSize, SlotOutOfRange,
    DuplicateSlot, InvalidTicketRecord, ItemMetadataMissing,
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
// Validates EVERY submitted slot before planning a debit. Does not consume
// ticket units, overwrite records, derive item counts from client, or
// authorize an S2C success. The returned plan is bound to the snapshot at
// this moment only; the actual GameData backend must recheck under owner lock.
TicketDebitPlan PlanTicketDebit(const Candidate& untrusted,
                               const AttestedInventory& trusted) noexcept;
} // namespace diamond_v291::gradeup0bda
