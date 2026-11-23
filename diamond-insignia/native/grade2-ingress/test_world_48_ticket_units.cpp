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
    // Unrecognized type returns singleton rather than guessed count.
    Expect(Ticket(123),Meta(0x47,1000),1);
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
    std::cout<<"WORLDSVR_0xAE0E90_QUANTITY_BRANCHES=PASS\n"
             <<"WORLD_48_BYTE_SLOT_ITEM_ID_AND_OPTION_OFFSETS=PASS\n"
             <<"TICKET_CLASS_METADATA_REQUIRED=PASS\n"
             <<"NO_UNVERIFIED_GAME_STACK_DEBIT=PASS\n";
}
