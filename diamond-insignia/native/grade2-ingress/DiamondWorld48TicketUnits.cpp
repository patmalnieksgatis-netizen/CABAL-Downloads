#include "DiamondWorld48TicketUnits.h"
namespace diamond_v291::gradeup0bda {
namespace {
std::uint32_t U32(const std::uint8_t* p) noexcept {
    return std::uint32_t(p[0]) | (std::uint32_t(p[1])<<8) |
           (std::uint32_t(p[2])<<16) | (std::uint32_t(p[3])<<24);
}
} // namespace
TicketUnitsResult DecodeTicketSlot48(
    const void* raw,std::size_t bytes,
    const AttestedItemMetadata& meta) noexcept {
    TicketUnitsResult out{};
    if(!raw || bytes<kWorldInventoryEntryBytes)
        return out;
    const auto* p=static_cast<const std::uint8_t*>(raw);
    // Actual 0B10 validates used item before calling the count function.
    if(U32(p+4)==0)return out;
    const auto kind=U32(p+8);
    out.rawItemKind=kind;
    if((kind&kWorldNormalizedItemMask)!=kTicket33554961) {
        out.verdict=TicketUnitsVerdict::NotTicket;
        return out;
    }
    // Actual 0xAE0E90 metadata index formula uses itemId&0xfff and
    // (itemId>>25)&3. For 0x02000211 this is index529, variant1.
    if(!meta.fromTrustedWorldCatalog ||
       meta.catalogItemIndex!=(kind&0xFFFu) ||
       meta.catalogVariant!=((kind>>25u)&3u)) {
        out.verdict=TicketUnitsVerdict::UnverifiedMetadata;
        return out;
    }
    const std::uint32_t option=U32(p+0x18);
    out.rawOptionLow32=option;
    // Exact 0xAE0E90: metadata +0x3C <=1 means one item; otherwise
    // metadata +0x38 selects one of three option-count encodings.
    std::uint32_t units=1u;
    if(meta.stackField3C>1) {
        switch(meta.kindField38) {
            case 0x46u: case 0x43u:
                units=option>>22u;break;
            case 0xAFu: case 0xB8u:
                units=option&0xFFFFu;break;
            case 0x10u: case 0x1Bu: case 0x66u:
                units=option&0x7Fu;break;
            case 0xB0u: {
                // This is NOT original 0xAE0E90: it is a separately
                // attested *new* materials-stack decode path. The
                // real 999/999 sample alone leaves its proof disabled.
                const auto verified=diamond_v291::inventory::
                    DecodeB0QuantityWithIndependentProof(
                        option,meta.kindField38,meta.stackField3C,
                        meta.b0QuantityProof);
                if(verified.verdict!=diamond_v291::inventory::
                   B0QuantityVerdict::VerifiedCount) {
                    out.quantity=1u; // original helper fallback, NEVER debit
                    out.verdict=TicketUnitsVerdict::UnverifiedStackQuantity;
                    return out;
                }
                units=verified.quantity;
                break;
            }
            default:
                // Exact original WorldSvr 0xAE0E90 returns 1 here, but
                // 0xB0/999 was OBSERVED for item 33554961 on the VM.
                // A 999-configured stack cannot be safely charged using
                // this fallback without the real item quantity encoding.
                out.quantity=1u; // original helper's numeric return
                out.verdict=TicketUnitsVerdict::UnverifiedStackQuantity;
                return out;
        }
    }
    if(units==0) {
        out.verdict=TicketUnitsVerdict::ZeroUnits;
        return out;
    }
    out.quantity=units;
    out.verdict=TicketUnitsVerdict::DecodedTicketQuantity;
    return out;
}
} // namespace diamond_v291::gradeup0bda
