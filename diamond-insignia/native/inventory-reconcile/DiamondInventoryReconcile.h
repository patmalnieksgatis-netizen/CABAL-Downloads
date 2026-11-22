#pragma once
// CABAL v291: read-only game-inventory persistence reconciliation.
// Record30 layout is derived from the owner's v14 EventPass inventory reader.
// A row is NOT a quantity: the real stack codec is UNKNOWN. Never report
// verified resources without an independently supplied authoritative decoder.
#include <cstddef>
#include <cstdint>

namespace diamond_v291::inventory {
constexpr std::size_t kPersistedRowBytes=30;
constexpr std::uint64_t kExchangeTicketItemId=33554961ULL;
constexpr std::size_t kMaxInventoryRows=512;
struct Record30 {
    std::uint64_t itemId=0;      // offset 0x00
    std::uint64_t itemSerial=0;  // offset 0x08
    std::uint64_t itemOption=0;  // offset 0x10; DO NOT assume quantity
    std::uint16_t physicalSlot=0;// offset 0x18
    std::uint32_t duration=0;    // offset 0x1A
};
struct PersistedBlob {
    const void* bytes=nullptr;
    std::size_t length=0;
    bool independentGameDataRead=false;
};
// The caller MUST provide a verified game-specific item-quantity codec.
// The callback must be pure and must reject unrecognized stacks/options.
// nullptr NEVER means one item per row.
using QuantityDecoder=bool (*)(void* context,const Record30& row,
                               std::uint32_t* itemUnits) noexcept;
enum class AuditStatus : std::uint8_t {
    Verified,
    UnattestedSnapshot,
    MalformedSnapshot,
    InvalidRecord,
    DuplicateSerialOrSlot,
    MissingQuantityCodec,
    QuantityCodecFailed,
    UnrelatedInventoryChanged,
    TicketIdentityChanged,
    TicketTotalsMismatch,
};
struct Audit {
    AuditStatus status=AuditStatus::UnattestedSnapshot;
    std::uint64_t beforeUnits=0;
    std::uint64_t afterUnits=0;
    std::size_t beforeTargetRows=0;
    std::size_t afterTargetRows=0;
    bool Verified() const noexcept {return status==AuditStatus::Verified;}
};
Audit VerifyPersistedTicketDebit(
    PersistedBlob before,PersistedBlob after,
    std::uint64_t expectedBeforeUnits,std::uint64_t expectedAfterUnits,
    QuantityDecoder decoder,void* decoderContext) noexcept;
const char* Name(AuditStatus status) noexcept;
} // namespace diamond_v291::inventory
