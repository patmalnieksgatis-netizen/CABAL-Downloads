#include "../DiamondB0SelectedDebit30.h"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <vector>

using namespace diamond_v291::inventory;
using namespace diamond_v291::gradeup0bda;
namespace {
std::array<std::uint8_t,30> Make(std::uint64_t item,
                                  std::uint64_t serial,
                                  std::uint64_t option,
                                  std::uint16_t slot) {
    std::array<std::uint8_t,30> b{};
    internal::PutU64(b.data()+0,item);
    internal::PutU64(b.data()+8,serial);
    internal::PutU64(b.data()+16,option);
    b[24]=static_cast<std::uint8_t>(slot);
    b[25]=static_cast<std::uint8_t>(slot>>8u);
    return b;
}
void Append(std::vector<std::uint8_t>& out,
            const std::array<std::uint8_t,30>& row) {
    out.insert(out.end(),row.begin(),row.end());
}
B0SelectionPersistenceProof FakeOwner() {
    B0SelectionPersistenceProof p{};
    p.userNum=5005;p.characterIdx=24055; // synthetic owner ID
    p.authenticatedWorldOwnerLockHeld=true;
    p.sameUserAndCharacterProvenFromServer=true;
    p.worldSlotsMappedToPersistedRowsUnderOwnerLock=true;
    p.persisted.gameDataRow30LayoutIndependentlyVerified=true;
    p.persisted.sameCharacterSnapshotAndSessionVerified=true;
    p.persisted.originalSqlTableAttested=true;
    auto& codec=p.persisted.codecProof;
    codec.provenProfile=B0CountProfile::PlainPositiveOptionNoFlags;
    codec.independentlyMatchedKnownQuantity=true; // synthetic
    codec.sameGameBuildAndMaterialKindVerified=true; // synthetic
    codec.optionLayoutVerified=true; // synthetic
    codec.extraOptionFlagsProvenAbsent=true; // synthetic
    return p;
}
TicketDebitPlan Plan(std::uint16_t firstWorld,std::uint32_t firstUnits,
                     std::uint32_t firstDebit,
                     std::uint16_t secondWorld=0,std::uint32_t secondUnits=0,
                     std::uint32_t secondDebit=0) {
    TicketDebitPlan p{};
    p.status=SelectionVerdict::ExactDebitPlan;
    p.selectedCount=secondUnits?2:1;
    p.exactPlannedDebit=100;
    p.selectedUnits=firstUnits+secondUnits;
    p.slots[0]={firstWorld,firstUnits,firstDebit,
                 firstUnits-firstDebit,firstUnits==firstDebit};
    if(secondUnits) p.slots[1]={secondWorld,secondUnits,secondDebit,
                                 secondUnits-secondDebit,
                                 secondUnits==secondDebit};
    return p;
}
}
int main() {
    const auto unrelated=Make(0x02000212,60001,0xabc,48);
    // one 999-unit real-shape ticket stack, one unrelated, and another
    // untouched 20 ticket stack belonging to the *same synthetic owner*.
    std::vector<std::uint8_t> one;
    Append(one,Make(33554961,10001,999,47));
    Append(one,unrelated);
    Append(one,Make(33554961,10002,20,49));
    const auto oneBefore=one;
    const auto plan=Plan(5,999,100);
    const B0WorldToPersistedSlot map1[]={{5,47,10001}};
    auto owner=FakeOwner();
    owner.persisted.codecProof.independentlyMatchedKnownQuantity=false;
    assert(StageVerifiedB0SelectedDebit100(
        one.data(),one.size(),plan,map1,1,owner).verdict==
        B0SelectedDebitVerdict::WrongItemOrAmount);
    owner=FakeOwner();
    owner.sameUserAndCharacterProvenFromServer=false;
    assert(StageVerifiedB0SelectedDebit100(
        one.data(),one.size(),plan,map1,1,owner).verdict==
        B0SelectedDebitVerdict::UnverifiedOwner);
    owner=FakeOwner();
    auto yes=StageVerifiedB0SelectedDebit100(
        one.data(),one.size(),plan,map1,1,owner);
    assert(yes.verdict==B0SelectedDebitVerdict::PreparedClone);
    assert(yes.allTicketUnitsBefore==1019);
    assert(yes.allTicketUnitsAfter==919);
    assert(yes.consumedWholeRecords==0);
    assert(!yes.liveWorldOrSqlChanged);
    assert(yes.proposedGameData.size()==one.size());
    assert(internal::GetU64(yes.proposedGameData.data()+16)==899);
    assert(std::equal(yes.proposedGameData.begin()+30,
                      yes.proposedGameData.end(),one.begin()+30));
    assert(one==oneBefore);

    // 60+80: debit 60 entirely, 40 from second stack; without
    // independently verified deletion semantics this must FAIL.
    std::vector<std::uint8_t> multi;
    Append(multi,Make(33554961,20001,60,47));
    Append(multi,unrelated);
    Append(multi,Make(33554961,20002,80,49));
    const auto multiBefore=multi;
    const auto mixed=Plan(5,60,60,8,80,40);
    const B0WorldToPersistedSlot map2[]={{5,47,20001},{8,49,20002}};
    auto multiProof=FakeOwner();
    assert(StageVerifiedB0SelectedDebit100(
        multi.data(),multi.size(),mixed,map2,2,multiProof).verdict==
        B0SelectedDebitVerdict::CannotRemoveFullStack);
    multiProof.fullStackRecordRemovalVerified=true; // SYNTHETIC ONLY
    const auto result=StageVerifiedB0SelectedDebit100(
        multi.data(),multi.size(),mixed,map2,2,multiProof);
    assert(result.verdict==B0SelectedDebitVerdict::PreparedClone);
    assert(result.allTicketUnitsBefore==140);
    assert(result.allTicketUnitsAfter==40);
    assert(result.consumedWholeRecords==1);
    assert(result.proposedGameData.size()==60);
    // first row removed; unrelated item untouched.
    assert(std::equal(result.proposedGameData.begin(),
                      result.proposedGameData.begin()+30,unrelated.begin()));
    assert(internal::GetU64(result.proposedGameData.data()+30+8)==20002);
    assert(internal::GetU64(result.proposedGameData.data()+30+16)==40);
    assert(multi==multiBefore);
    assert(!result.liveWorldOrSqlChanged);

    // 60+40, both depleted; exact deletion requires separate proof.
    std::vector<std::uint8_t> depleted;
    Append(depleted,Make(33554961,20001,60,47));
    Append(depleted,unrelated);
    Append(depleted,Make(33554961,20002,40,49));
    const auto fullPlan=Plan(5,60,60,8,40,40);
    const auto full=StageVerifiedB0SelectedDebit100(
        depleted.data(),depleted.size(),fullPlan,map2,2,multiProof);
    assert(full.verdict==B0SelectedDebitVerdict::PreparedClone);
    assert(full.allTicketUnitsBefore==100 && full.allTicketUnitsAfter==0);
    assert(full.consumedWholeRecords==2);
    assert(full.proposedGameData.size()==30);
    assert(std::equal(full.proposedGameData.begin(),
                      full.proposedGameData.end(),unrelated.begin()));

    // A mapping from the wrong SQL physical slot or item serial is rejected.
    const B0WorldToPersistedSlot wrongSlot[]={{5,50,10001}};
    assert(StageVerifiedB0SelectedDebit100(
        one.data(),one.size(),plan,wrongSlot,1,owner).verdict==
        B0SelectedDebitVerdict::InvalidWorldToSavedSlotMap);
    const B0WorldToPersistedSlot wrongSerial[]={{5,47,20001}};
    assert(StageVerifiedB0SelectedDebit100(
        one.data(),one.size(),plan,wrongSerial,1,owner).verdict==
        B0SelectedDebitVerdict::InvalidWorldToSavedSlotMap);
    const B0WorldToPersistedSlot duplicate[]={{5,47,20001},{8,47,20002}};
    assert(StageVerifiedB0SelectedDebit100(
        multi.data(),multi.size(),mixed,duplicate,2,multiProof).verdict==
        B0SelectedDebitVerdict::InvalidWorldToSavedSlotMap);
    auto malformedPlan=plan;
    malformedPlan.exactPlannedDebit=99;
    assert(StageVerifiedB0SelectedDebit100(
        one.data(),one.size(),malformedPlan,map1,1,owner).verdict==
        B0SelectedDebitVerdict::UnverifiedSelection);
    assert(StageVerifiedB0SelectedDebit100(
        one.data(),one.size()-1,plan,map1,1,owner).verdict==
        B0SelectedDebitVerdict::InvalidBlob);
    assert(one==oneBefore && multi==multiBefore);

    std::cout<<"B0_SELECTED_ONE_STACK_999_TO_899_CLONE=PASS\n"
             <<"B0_SELECTED_TWO_STACKS_60_PLUS_80_EXACT100=PASS\n"
             <<"B0_FULL_STACK_REMOVAL_NEEDS_INDEPENDENT_PROOF=PASS\n"
             <<"B0_SELECTED_SQL_WORLD_SLOT_AND_SERIAL_MAPPING_FAIL_CLOSED=PASS\n"
             <<"B0_MULTISTACK_GAMEDATA_UNRELATED_BYTES_UNCHANGED=PASS\n";
}
