#include "../DiamondB0PartialDebit30.h"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <vector>

using namespace diamond_v291::inventory;
namespace {
void U64(unsigned char* p,std::uint64_t n){
    for(unsigned i=0;i<8;++i)p[i]=static_cast<unsigned char>(n>>(i*8u));
}
void U16(unsigned char* p,std::uint16_t n){
    for(unsigned i=0;i<2;++i)p[i]=static_cast<unsigned char>(n>>(i*8u));
}
std::array<std::uint8_t,30> Make(
    std::uint64_t item,std::uint64_t serial,
    std::uint64_t option,std::uint16_t slot) {
    std::array<std::uint8_t,30> v{};
    U64(v.data()+0,item);
    U64(v.data()+8,serial);
    U64(v.data()+16,option);
    U16(v.data()+24,slot);
    return v;
}
B0PartialDebitOwnerProof SyntheticAuthority(){
    B0PartialDebitOwnerProof a{};
    a.persisted.codecProof.provenProfile=B0CountProfile::OptionLow10;
    a.persisted.codecProof.independentlyMatchedKnownQuantity=true;
    a.persisted.codecProof.sameGameBuildAndMaterialKindVerified=true;
    a.persisted.codecProof.optionLayoutVerified=true;
    a.persisted.codecProof.extraOptionFlagsProvenAbsent=true;
    a.persisted.gameDataRow30LayoutIndependentlyVerified=true;
    a.persisted.sameCharacterSnapshotAndSessionVerified=true;
    a.persisted.originalSqlTableAttested=true;
    a.worldUserAndCharacterOwnerLockVerified=true;
    a.persistedPhysicalSlotMatchesWorldSelectionVerified=true;
    a.callerHoldsExclusiveGameInventoryLease=true;
    a.expectedItemSerial=12345; // SYNTHETIC ONLY
    a.expectedPhysicalSlot=47;
    a.expectedStackAmount=999;
    return a;
}
}
int main() {
    auto ticket=Make(kRealB0TicketItem,12345,999,47);
    auto unrelated=Make(0x02000212,54321,0xABCD,48);
    std::vector<std::uint8_t> blob(ticket.begin(),ticket.end());
    blob.insert(blob.end(),unrelated.begin(),unrelated.end());
    const auto original=blob;
    auto authority=SyntheticAuthority();
    authority.persisted.codecProof.independentlyMatchedKnownQuantity=false;
    assert(StageB0TicketPartialDebit100(
        blob.data(),blob.size(),authority).status==
        B0PartialDebitStatus::WrongTicketOrQuantity);
    authority=SyntheticAuthority();
    authority.persistedPhysicalSlotMatchesWorldSelectionVerified=false;
    assert(StageB0TicketPartialDebit100(
        blob.data(),blob.size(),authority).status==
        B0PartialDebitStatus::MissingOwnerOrSlotProof);
    authority=SyntheticAuthority();
    const auto result=StageB0TicketPartialDebit100(
        blob.data(),blob.size(),authority);
    assert(result.status==B0PartialDebitStatus::PreparedClone);
    assert(result.beforeUnits==999 && result.afterUnits==899);
    assert(!result.wroteLiveGameData);
    assert(result.proposedGameData.size()==blob.size());
    assert(internal::GetU64(result.proposedGameData.data()+16)==899);
    assert(std::memcmp(result.proposedGameData.data()+30,
                       original.data()+30,30)==0);
    assert(std::memcmp(result.proposedGameData.data(),
                       original.data(),16)==0);
    assert(std::memcmp(result.proposedGameData.data()+24,
                       original.data()+24,6)==0);
    assert(blob==original);  // staging never changes actual GameData bytes

    auto mismatched=authority;
    mismatched.expectedItemSerial=1;
    assert(StageB0TicketPartialDebit100(blob.data(),blob.size(),mismatched).status==
           B0PartialDebitStatus::WrongTicketOrQuantity);
    mismatched=authority;
    mismatched.expectedPhysicalSlot=50;
    assert(StageB0TicketPartialDebit100(blob.data(),blob.size(),mismatched).status==
           B0PartialDebitStatus::WrongTicketOrQuantity);
    mismatched=authority;
    mismatched.expectedStackAmount=998;
    assert(StageB0TicketPartialDebit100(blob.data(),blob.size(),mismatched).status==
           B0PartialDebitStatus::WrongTicketOrQuantity);
    mismatched=authority;
    mismatched.persisted.codecProof.provenProfile=B0CountProfile::Unknown;
    assert(StageB0TicketPartialDebit100(blob.data(),blob.size(),mismatched).status==
           B0PartialDebitStatus::WrongTicketOrQuantity);

    auto full=Make(kRealB0TicketItem,12345,100,47);
    mismatched=authority;mismatched.expectedStackAmount=100;
    assert(StageB0TicketPartialDebit100(full.data(),full.size(),mismatched).status==
           B0PartialDebitStatus::CannotDeleteEntireStack);
    assert(StageB0TicketPartialDebit100(blob.data(),59,authority).status==
           B0PartialDebitStatus::InvalidBlob);

    auto invalid=blob;
    U64(invalid.data()+30+8,12345); // duplicate item serial
    assert(StageB0TicketPartialDebit100(invalid.data(),invalid.size(),authority).status==
           B0PartialDebitStatus::DuplicateSlotOrSerial);
    invalid=blob;
    U16(invalid.data()+30+24,47); // duplicate physical slot
    assert(StageB0TicketPartialDebit100(invalid.data(),invalid.size(),authority).status==
           B0PartialDebitStatus::DuplicateSlotOrSerial);
    // No proof of high option bits: reject preservation ambiguity.
    invalid=blob;
    U64(invalid.data()+16,0x1000u|999u);
    assert(StageB0TicketPartialDebit100(invalid.data(),invalid.size(),authority).status==
           B0PartialDebitStatus::WrongTicketOrQuantity);

    authority.persisted.codecProof.provenProfile=B0CountProfile::OptionLow16;
    const auto low16=StageB0TicketPartialDebit100(blob.data(),blob.size(),authority);
    assert(low16.status==B0PartialDebitStatus::PreparedClone);
    assert(internal::GetU64(low16.proposedGameData.data()+16)==899);
    assert(original==blob);

    std::cout<<"B0_REAL_SAVED_OPTION_999_CLONE_TO_899_PROPOSAL=PASS\n"
             <<"B0_ALL_UNRELATED_INVENTORY_BYTES_PRESERVED=PASS\n"
             <<"B0_ZERO_LIVE_SQL_OR_WORLD_MUTATIONS=PASS\n"
             <<"B0_PROOF_SLOT_IDENTITY_COUNT_AND_FLAGS_REQUIRED=PASS\n";
}
