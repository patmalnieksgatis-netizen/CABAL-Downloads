#pragma once
// Exact original WorldSvr Platinum inventory helper 0xAE0E90 (read-only).
// The 48-byte entry stride is proven at 0x587E30; its selected-item
// count is metadata-dependent and MUST NOT be inferred from client slots.
// Intended as a verified future GameData quantity read adapter, not a writer.
#include <cstddef>
#include <cstdint>
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
// A metadata +0x3C > 1 with unrecognized +0x38 type (the REAL B0/999
// case) reports UnverifiedStackQuantity even though the original helper
// falls through and returns numerical 1. Consumers must never debit it.
//
// Reads +4 occupancy, +8 itemKind and +0x18 item option, which is
// exactly +0x10 from the item pointer passed to original 0xAE0E90.
// Caller must attest original x64 slot memory, exclusive owner lock,
// and actual runtime item catalog fields 0x38/0x3C.
TicketUnitsResult DecodeTicketSlot48(
    const void* originalEntry,std::size_t verifiedBytes,
    const AttestedItemMetadata& verifiedCatalog) noexcept;
} // namespace diamond_v291::gradeup0bda
