#include "Diamond0BDATicketSelection.h"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <vector>
using namespace diamond_v291::gradeup0bda;
namespace {
void Put32(std::uint8_t* dst,std::uint32_t v) {
    for(unsigned i=0;i<4;++i) dst[i]=static_cast<std::uint8_t>(v>>(i*8u));
}
void Slot(std::vector<std::uint8_t>& inventory,std::size_t n,
          std::uint32_t units,bool validItem=true,bool occupied=true) {
    auto* p=inventory.data()+n*kWorldInventoryEntryBytes;
    Put32(p+4,occupied?1u:0u);
    Put32(p+8,validItem?kTicket33554961:0x02000212u);
    Put32(p+0x18,units);
}
Candidate Request(std::uint16_t first,std::uint16_t second) {
    Candidate c{};
    c.state=PacketState::Candidate;c.count=2;
    c.rawEntries[0]=first;c.rawEntries[1]=second;
    return c;
}
AttestedInventory Authority(const std::uint8_t* p,std::size_t n,
                            const void* session) {
    AttestedInventory a{};
    a.authenticatedWorldSession=session;
    a.boundWorldSession=session;
    a.trustedRecords=p;
    a.trustedRecordsBytes=n;
    a.acquiredUnderExclusiveOwnerLock=true;
    a.recordsVerifiedFromWorldSession=true;
    a.registeredUserNum=9911;
    a.registeredCharacterIdx=5001;
    a.trustedRevision=21;
    a.itemCatalog.fromTrustedWorldCatalog=true;
    a.itemCatalog.catalogItemIndex=0x211u;
    a.itemCatalog.catalogVariant=1u;
    a.itemCatalog.kindField38=0xAFu;  // synthetic, NOT actual runtime ticket tag
    a.itemCatalog.stackField3C=999;
    return a;
}
void Eq(SelectionVerdict expected,const Candidate& c,
        const AttestedInventory& auth) {
    const auto r=PlanTicketDebit(c,auth);
    assert(r.status==expected);
    assert(!r.mayMutateLiveInventory);
    assert(!r.durableTransactionCommitted);
}
}
int main() {
    std::vector<std::uint8_t> inventory(
        kWorldInventorySlots*kWorldInventoryEntryBytes,0);
    Slot(inventory,5,60);
    Slot(inventory,8,80);
    Slot(inventory,521,150);
    int owner=1,other=2;
    auto a=Authority(inventory.data(),inventory.size(),&owner);
    const auto original=inventory;
    auto packet=Request(5,8);
    const auto plan=PlanTicketDebit(packet,a);
    assert(plan.status==SelectionVerdict::ExactDebitPlan);
    assert(plan.selectedCount==2 && plan.selectedUnits==140);
    assert(plan.exactPlannedDebit==100);
    assert(plan.slots[0].slot==5 && plan.slots[0].debitPlanned==60);
    assert(plan.slots[0].expectedRemaining==0);
    assert(plan.slots[0].removeEmptyRecord);
    assert(plan.slots[1].slot==8 && plan.slots[1].debitPlanned==40);
    assert(plan.slots[1].expectedRemaining==40);
    assert(!plan.slots[1].removeEmptyRecord);
    assert(inventory==original); // never changed live memory
    // A whole 150-unit stack plans a *partial* debit of exactly 100.
    packet.state=PacketState::Candidate;packet.count=1;
    packet.rawEntries[0]=521;
    auto single=PlanTicketDebit(packet,a);
    assert(single.status==SelectionVerdict::ExactDebitPlan);
    assert(single.selectedUnits==150 && single.exactPlannedDebit==100);
    assert(single.slots[0].expectedRemaining==50);
    // Overlapping per-stack selection is rejected, never double counted.
    Eq(SelectionVerdict::DuplicateSlot,Request(5,5),a);
    Eq(SelectionVerdict::SlotOutOfRange,Request(5,522),a);
    packet=Request(5,8); packet.state=PacketState::Other;
    Eq(SelectionVerdict::InvalidPacket,packet,a);
    packet=Request(5,8);packet.count=0;
    Eq(SelectionVerdict::InvalidPacket,packet,a);
    packet=Request(5,8);
    a.boundWorldSession=&other;
    Eq(SelectionVerdict::MissingOwnerAuthority,packet,a);
    a.boundWorldSession=&owner;
    a.acquiredUnderExclusiveOwnerLock=false;
    Eq(SelectionVerdict::MissingOwnerAuthority,packet,a);
    a.acquiredUnderExclusiveOwnerLock=true;
    a.recordsVerifiedFromWorldSession=false;
    Eq(SelectionVerdict::MissingOwnerAuthority,packet,a);
    a.recordsVerifiedFromWorldSession=true;
    a.trustedRecordsBytes-=1;
    Eq(SelectionVerdict::WrongSnapshotSize,packet,a);
    a.trustedRecordsBytes+=1;
    a.itemCatalog.fromTrustedWorldCatalog=false;
    Eq(SelectionVerdict::ItemMetadataMissing,packet,a);
    a.itemCatalog.fromTrustedWorldCatalog=true;
    a.itemCatalog.catalogVariant=0;
    Eq(SelectionVerdict::ItemMetadataMissing,packet,a);
    a.itemCatalog.catalogVariant=1;
    Slot(inventory,5,20);
    Slot(inventory,8,30);
    Eq(SelectionVerdict::InsufficientTickets,packet,a);
    Slot(inventory,5,60);
    Slot(inventory,8,0);
    Eq(SelectionVerdict::ZeroOrInvalidTicketCount,packet,a);
    Slot(inventory,8,80,false);
    Eq(SelectionVerdict::InvalidTicketRecord,packet,a);
    Slot(inventory,8,80,true,false);
    Eq(SelectionVerdict::InvalidTicketRecord,packet,a);
    assert(!a.itemCatalog.fromTrustedWorldCatalog==false);
    std::cout<<"GRADE2_0BDA_SELECTION_DUPLICATES_AND_AUTHORITY=PASS\n"
             <<"GRADE2_0BDA_EXACT_100_UNIT_DEBIT_PLAN=PASS\n"
             <<"GRADE2_0BDA_ZERO_REAL_GAME_INVENTORY_MUTATIONS=PASS\n";
}
