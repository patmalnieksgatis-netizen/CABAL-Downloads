#include "DiamondWorld48TicketUnits.h"
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>
using namespace diamond_v291::gradeup0bda;
namespace {
void U32(std::uint8_t* p,std::uint32_t x){
    for(unsigned i=0;i<4;++i)p[i]=static_cast<std::uint8_t>(x>>(8u*i));
}
std::array<std::uint8_t,kWorldInventoryEntryBytes> Ticket(std::uint32_t opt) {
    std::array<std::uint8_t,kWorldInventoryEntryBytes> record{};
    U32(record.data()+4,1);
    U32(record.data()+8,kTicket33554961);
    U32(record.data()+0x18,opt);
    return record;
}
AttestedItemMetadata Meta(std::uint32_t kind,std::int32_t stack) {
    AttestedItemMetadata m{};
    m.fromTrustedWorldCatalog=true;
    m.catalogItemIndex=0x211;
    m.catalogVariant=1;
    m.kindField38=kind;
    m.stackField3C=stack;
    return m;
}
TicketUnitsResult Read(const std::array<std::uint8_t,48>& slot,
                       const AttestedItemMetadata& m) {
    return DecodeTicketSlot48(slot.data(),slot.size(),m);
}
void Expect(const std::array<std::uint8_t,48>& record,
            const AttestedItemMetadata& meta,std::uint32_t expected) {
    auto result=Read(record,meta);
    assert(result.verdict==TicketUnitsVerdict::DecodedTicketQuantity);
    assert(result.quantity==expected);
    assert((result.rawItemKind&kWorldNormalizedItemMask)==kTicket33554961);
}
} // namespace
int main() {
    assert(kWorldInventoryEntryBytes==48u && kWorldInventoryMaxSlot==521u);
    assert(kWorldNormalizedItemMask==0x06000FFFu);
    auto record=Ticket(0);
    // The exact helper returns 1 when metadata stackField3C <=1.
    Expect(record,Meta(0x46,1),1);
    Expect(record,Meta(0x46,0),1);
    // For original WorldSvr metadata field +0x38==0x46/0x43:
    Expect(Ticket(100u<<22u),Meta(0x46,1000),100);
    Expect(Ticket(100u<<22u),Meta(0x43,1000),100);
    // For metadata tag 0xAF/0xB8 use the low 16 option bits.
    Expect(Ticket(100),Meta(0xAF,1000),100);
    Expect(Ticket(100),Meta(0xB8,1000),100);
    // For tags 0x10 / 0x1B / 0x66 use the low 7 bits.
    Expect(Ticket(100),Meta(0x10,1000),100);
    Expect(Ticket(100),Meta(0x1B,1000),100);
    Expect(Ticket(100),Meta(0x66,1000),100);
    // Unrecognized type yields numerical 1 in original 0xAE0E90, but
    // MUST NOT be accepted as verified quantity for a stack configured >1.
    const auto unknownFallback=Read(Ticket(123),Meta(0x47,1000));
    assert(unknownFallback.verdict==TicketUnitsVerdict::UnverifiedStackQuantity);
    assert(unknownFallback.quantity==1);
    // REAL VM metadata captured 2026-11-23: item 33554961 kind=0xB0,
    // metadata signed stack field=999. The helper returns numerical 1,
    // but this is NOT evidence that the actual stack has one ticket.
    const auto realB0a=Read(Ticket(123),Meta(0xB0,999));
    const auto realB0b=Read(Ticket(500),Meta(0xB0,999));
    assert(realB0a.verdict==TicketUnitsVerdict::UnverifiedStackQuantity);
    assert(realB0b.verdict==TicketUnitsVerdict::UnverifiedStackQuantity);
    assert(realB0a.quantity==1 && realB0b.quantity==1);
    // Real 999/999 raw Option evidence can fit BOTH low10 and low16.
    // It must never switch the live decoder on its own.
    auto observed=diamond_v291::inventory::
        InspectUnprovenB0Option(0x3e7ULL);
    assert(observed.low10==999 && observed.low16==999);
    assert(observed.bothMatchObserved999 && !observed.profileIdentified);
    auto proven=Meta(0xB0,999);
    using diamond_v291::inventory::B0CountProfile;
    proven.b0QuantityProof.provenProfile=B0CountProfile::OptionLow10;
    proven.b0QuantityProof.sameGameBuildAndMaterialKindVerified=true;
    proven.b0QuantityProof.optionLayoutVerified=true;
    proven.b0QuantityProof.extraOptionFlagsProvenAbsent=true;
    // Without independent observed UI/native count, still reject.
    assert(Read(Ticket(999),proven).verdict==
           TicketUnitsVerdict::UnverifiedStackQuantity);
    proven.b0QuantityProof.independentlyMatchedKnownQuantity=true;
    // SYNTHETIC future proof fixture, not the user's current VM state.
    Expect(Ticket(999),proven,999);
    Expect(Ticket(899),proven,899);
    Expect(Ticket(100),proven,100);
    assert(Read(Ticket(1000),proven).verdict==
           TicketUnitsVerdict::UnverifiedStackQuantity);
    assert(Read(Ticket(0),proven).verdict==
           TicketUnitsVerdict::UnverifiedStackQuantity);
    assert(Read(Ticket(0x1000u|899u),proven).verdict==
           TicketUnitsVerdict::UnverifiedStackQuantity);
    // Low16 candidate also requires separate independent attestation.
    proven.b0QuantityProof.provenProfile=B0CountProfile::OptionLow16;
    Expect(Ticket(899),proven,899);
    assert(Read(Ticket(0x10000u|899u),proven).verdict==
           TicketUnitsVerdict::UnverifiedStackQuantity);
    auto none=Read(Ticket(0),Meta(0x46,1000));
    assert(none.verdict==TicketUnitsVerdict::ZeroUnits);
    auto unknown=Meta(0x46,1000);
    unknown.fromTrustedWorldCatalog=false;
    assert(Read(Ticket(100u<<22u),unknown).verdict==
           TicketUnitsVerdict::UnverifiedMetadata);
    unknown=Meta(0x46,1000);unknown.catalogVariant=0;
    assert(Read(Ticket(100u<<22u),unknown).verdict==
           TicketUnitsVerdict::UnverifiedMetadata);
    unknown=Meta(0x46,1000);unknown.catalogItemIndex=0x210;
    assert(Read(Ticket(100u<<22u),unknown).verdict==
           TicketUnitsVerdict::UnverifiedMetadata);
    record=Ticket(100);
    U32(record.data()+8,0x02000212u);
    assert(Read(record,Meta(0xAF,1000)).verdict==TicketUnitsVerdict::NotTicket);
    record=Ticket(100);
    U32(record.data()+4,0);
    assert(Read(record,Meta(0xAF,1000)).verdict==
           TicketUnitsVerdict::MalformedRecord);
    record=Ticket(100);
    assert(DecodeTicketSlot48(nullptr,48,Meta(0xAF,1000)).verdict==
           TicketUnitsVerdict::MalformedRecord);
    assert(DecodeTicketSlot48(record.data(),47,Meta(0xAF,1000)).verdict==
           TicketUnitsVerdict::MalformedRecord);
    std::cout<<"WORLDSVR_LIVE_B0_999_LOW10_VS_LOW16_UNRESOLVED=PASS\n"
             <<"WORLDSVR_B0_INDEPENDENT_UI_PROOF_REQUIRED_FOR_COUNT=PASS\n"
             <<"WORLDSVR_LIVE_TICKET_B0_999_FALLBACK_SINGLETON_ONLY=PASS\n"
             <<"WORLDSVR_0xAE0E90_QUANTITY_BRANCHES=PASS\n"
             <<"WORLD_48_BYTE_SLOT_ITEM_ID_AND_OPTION_OFFSETS=PASS\n"
             <<"TICKET_CLASS_METADATA_REQUIRED=PASS\n"
             <<"NO_UNVERIFIED_GAME_STACK_DEBIT=PASS\n";
}
