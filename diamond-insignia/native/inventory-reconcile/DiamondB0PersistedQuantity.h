#pragma once
// Native v291 Diamond read-only persisted inventory 30-byte row decoder.
// This adapter allows reconciliation of an independently VERIFIED Material
// B0/999 quantity profile. No SQL, no GameData writes, no WorldSvr hook.
// Merely observing two ItemOption=999 rows DOES NOT authenticate the profile.
#include "DiamondB0QuantityCodec.h"
#include "DiamondInventoryReconcile.h"
#include <cstdint>

namespace diamond_v291::inventory {
struct PersistedB0QuantityAuthority {
    B0QuantityEvidence codecProof{};
    bool gameDataRow30LayoutIndependentlyVerified=false;
    bool sameCharacterSnapshotAndSessionVerified=false;
    bool originalSqlTableAttested=false;
};
inline bool DecodeVerifiedB0PersistedRecord(
    void* opaque,const Record30& row,std::uint32_t* units) noexcept {
    if(!opaque || !units || row.itemId!=kRealB0TicketItem)
        return false;
    *units=0;
    const auto* source=static_cast<const PersistedB0QuantityAuthority*>(opaque);
    if(!source->gameDataRow30LayoutIndependentlyVerified ||
       !source->sameCharacterSnapshotAndSessionVerified ||
       !source->originalSqlTableAttested)
        return false;
    const auto result=DecodeB0QuantityWithIndependentProof(
        row.itemOption,kRealB0MaterialKind,999,source->codecProof);
    if(result.verdict!=B0QuantityVerdict::VerifiedCount) return false;
    *units=result.quantity;
    return true;
}
} // namespace diamond_v291::inventory
