#pragma once
// Exact original WorldSvr Platinum inventory helper 0xAE0E90 (read-only).
// The 48-byte entry stride is proven at 0x587E30; its selected-item
// count is metadata-dependent and MUST NOT be inferred from client slots.
// Reads native quantities only. No item mutation or GameData writes.
#include <cstddef>
#include <cstdint>
#include "../inventory-reconcile/DiamondB0QuantityCodec.h"
namespace diamond_v291::gradeup0bda {
constexpr std::uint32_t kTicket33554961=33554961u;
constexpr std::uint32_t kWorldNormalizedItemMask=0x06000FFFu;
constexpr std::size_t kWorldInventoryEntryBytes=48;
constexpr std::size_t kWorldInventoryMaxSlot=521;
struct AttestedItemMetadata {
    bool fromTrustedWorldCatalog=false;
    std::uint32_t catalogItemIndex=0;
    std::uint32_t catalogVariant=0;
    std::uint32_t kindField38=0; // exact WorldSvr metadata +0x38
    std::int32_t stackField3C=0; // exact WorldSvr signed comparison at +0x3C
    // Retained for callers carrying persisted-record quantity evidence.
    // The native B0 numeric branch is verified by original instructions.
    diamond_v291::inventory::B0QuantityEvidence b0QuantityProof{};
};
enum class TicketUnitsVerdict : std::uint8_t {
    MalformedRecord, NotTicket, UnverifiedMetadata, ZeroUnits,
    DecodedTicketQuantity, UnverifiedStackQuantity
};
struct TicketUnitsResult {
    TicketUnitsVerdict verdict=TicketUnitsVerdict::MalformedRecord;
    std::uint32_t quantity=0;
    std::uint32_t rawItemKind=0;
    std::uint32_t rawOptionLow32=0;
};
// Metadata +0x3C <=1 reports one item. For larger stacks, AE0E90
// selects masked option counts for known packed types and returns the
// numeric option for B0. B0 accepts the observed stack limit 999 and a
// plain positive option in 1..999. Unrecognized metadata is rejected.
//
// Reads +4 occupancy, +8 itemKind and the 8-byte +0x18 item option, which is
// exactly +0x10 from the item pointer passed to original 0xAE0E90.
// Caller must attest original x64 slot memory, exclusive owner lock,
// and actual runtime item catalog fields 0x38/0x3C.
TicketUnitsResult DecodeTicketSlot48(
    const void* originalEntry,std::size_t verifiedBytes,
    const AttestedItemMetadata& verifiedCatalog) noexcept;
} // namespace diamond_v291::gradeup0bda
