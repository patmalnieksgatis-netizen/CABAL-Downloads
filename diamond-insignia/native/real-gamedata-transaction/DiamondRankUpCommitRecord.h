#pragma once
// Owned result of the real SQL transaction. No native USERCONTEXT pointer
// survives in this record. Completion still requires a live native lease.
#include "../world-save-barrier/DiamondWorldSaveBarrier.h"
#include "../inventory-reconcile/DiamondB0SelectedDebit30.h"
#include <vector>

namespace diamond_v291::real_gamedata {
struct RankUpCommitRecord {
    Operation operation{};
    std::uint64_t sessionGeneration=0;
    std::vector<std::uint8_t> inventoryBefore{};
    std::vector<std::uint8_t> inventoryAfter{};
    std::vector<inventory::B0WorldToPersistedSlot> selectedSlots{};
    gradeup0bda::TicketDebitPlan ticketDebit{};
};
} // namespace diamond_v291::real_gamedata
