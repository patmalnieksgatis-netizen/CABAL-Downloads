#include "../DiamondInventoryReconcile.h"
#include "../../world-save-barrier/DiamondWorldSaveBarrier.h"
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <vector>
using namespace diamond_v291;
using namespace diamond_v291::inventory;
namespace {
void Put16(unsigned char* p,std::uint16_t x) {
    p[0]=static_cast<unsigned char>(x);
    p[1]=static_cast<unsigned char>(x>>8);
}
void Put32(unsigned char* p,std::uint32_t x) {
    for(int i=0;i<4;++i)p[i]=static_cast<unsigned char>(x>>(8*i));
}
void Put64(unsigned char* p,std::uint64_t x) {
    for(int i=0;i<8;++i)p[i]=static_cast<unsigned char>(x>>(8*i));
}
std::array<unsigned char,30> Row(std::uint64_t id,std::uint64_t serial,
    std::uint64_t options,std::uint16_t slot,std::uint32_t duration=0) {
    std::array<unsigned char,30> a{};
    Put64(a.data(),id);Put64(a.data()+8,serial);Put64(a.data()+16,options);
    Put16(a.data()+24,slot);Put32(a.data()+26,duration);
    return a;
}
std::vector<unsigned char> Pack(
       const std::vector<std::array<unsigned char,30>>& rows) {
    std::vector<unsigned char> result;
    for(const auto& row:rows)
        result.insert(result.end(),row.begin(),row.end());
    return result;
}
PersistedBlob Blob(const std::vector<unsigned char>& bytes,bool attested=true) {
    return {bytes.data(),bytes.size(),attested};
}
// TEST ONLY: the real game itemOption/stack-count codec is not established!
// It must never be used in a production WorldSvr or GameData bridge.
bool SyntheticStackCodec(void*,const Record30& row,
                        std::uint32_t* quantity) noexcept {
    if(!quantity || (row.itemOption>>16)!=0) return false;
    *quantity=static_cast<std::uint32_t>(row.itemOption);
    return *quantity>0;
}
void TestPersistenceBarrier(bool inventoryVerified,bool expectSuccess) {
    DiamondWorldSaveBarrier barrier;
    Operation op{};
    op.durableIntent=0x123400;
    op.userNum=900001;op.characterIdx=7002;
    op.expectedRevision=10;op.appliedRevision=11;
    op.command=1;op.newBadgeGrade=2;
    op.newWexp=10000;op.newTickets=20;
    assert(barrier.Begin(op,true,true)==Verdict::Ok);
    assert(barrier.MarkNativeMutationApplied(true)==Verdict::Ok);
    assert(barrier.MarkSaveSent(1,100,0)==Verdict::Ok);
    std::array<unsigned char,18> ack{};
    Put16(ack.data(),0xB7E2);Put16(ack.data()+2,18);
    Put16(ack.data()+8,47);
    Put32(ack.data()+10,7002);Put32(ack.data()+14,1);
    assert(barrier.ObserveIpcResult47(ack.data(),ack.size(),101,1)==Verdict::Ok);
    assert(!barrier.MaySendSuccess()); // IPC ACK itself is NOT durability
    DurableSnapshot s{};
    s.verifiedGameInventory=inventoryVerified;
    s.verifiedGameWexp=true;
    s.receiptCommitted=true;
    s.durableIntent=op.durableIntent;s.userNum=op.userNum;
    s.characterIdx=op.characterIdx;s.revision=op.appliedRevision;
    s.badgeGrade=op.newBadgeGrade;s.wexp=op.newWexp;
    s.tickets=op.newTickets;s.masteryId=0;s.masteryLevel=0;
    const auto verdict=barrier.Reconcile(s);
    assert((verdict==Verdict::Ok)==expectSuccess);
    assert(barrier.MaySendSuccess()==expectSuccess);
}
}
int main() {
    constexpr std::uint64_t ticket=kExchangeTicketItemId;
    const auto original=Pack({
        Row(ticket,101,120,48),
        Row(555,300,0xABC,49,333),
    });
    const auto saved=Pack({
        Row(ticket,101,20,48),
        Row(555,300,0xABC,49,333),
    });
    const auto audit=VerifyPersistedTicketDebit(
        Blob(original),Blob(saved),120,20,SyntheticStackCodec,nullptr);
    assert(audit.Verified() && audit.beforeUnits==120 && audit.afterUnits==20);
    assert(audit.beforeTargetRows==1 && audit.afterTargetRows==1);
    // Mastery purchase costs points, NOT a ticket. Persisted inventory must
    // remain byte-identical, and an authoritative stack decoder is still
    // mandatory even though the ticket balance is unchanged.
    const auto same=VerifyPersistedTicketsUnchanged(
        Blob(original),Blob(original),120,SyntheticStackCodec,nullptr);
    assert(same.Verified() && same.beforeUnits==120 && same.afterUnits==120);
    assert(VerifyPersistedTicketsUnchanged(Blob(original),Blob(original),120,
        nullptr,nullptr).status==AuditStatus::MissingQuantityCodec);
    assert(VerifyPersistedTicketsUnchanged(Blob(original),Blob(saved),120,
        SyntheticStackCodec,nullptr).status==AuditStatus::TicketIdentityChanged);

    assert(VerifyPersistedTicketDebit(Blob(original),Blob(saved),120,20,
        nullptr,nullptr).status==AuditStatus::MissingQuantityCodec);
    assert(VerifyPersistedTicketDebit(Blob(original,false),Blob(saved),120,20,
        SyntheticStackCodec,nullptr).status==AuditStatus::UnattestedSnapshot);
    assert(VerifyPersistedTicketDebit(Blob(original),Blob(saved),120,19,
        SyntheticStackCodec,nullptr).status==AuditStatus::TicketTotalsMismatch);
    assert(VerifyPersistedTicketDebit(Blob(original),Blob(original),120,20,
        SyntheticStackCodec,nullptr).status==AuditStatus::TicketTotalsMismatch);
    // A net debit must not mask a credit to a different ticket stack.
    // 120 + 80 -> 130 + 20 reduces the total by 50, but stack 101 grows.
    const auto mixedBefore=Pack({
        Row(ticket,101,120,48),Row(ticket,102,80,50),
        Row(555,300,0xABC,49,333),
    });
    const auto mixedAfter=Pack({
        Row(ticket,101,130,48),Row(ticket,102,20,50),
        Row(555,300,0xABC,49,333),
    });
    assert(VerifyPersistedTicketDebit(
        Blob(mixedBefore),Blob(mixedAfter),200,150,
        SyntheticStackCodec,nullptr).status==AuditStatus::TicketStackIncreased);
    // Legitimate debit may reduce two separate existing stacks.
    const auto splitAfter=Pack({
        Row(ticket,101,70,48),Row(ticket,102,30,50),
        Row(555,300,0xABC,49,333),
    });
    assert(VerifyPersistedTicketDebit(
        Blob(mixedBefore),Blob(splitAfter),200,100,
        SyntheticStackCodec,nullptr).Verified());
    auto foreign=Pack({Row(ticket,101,20,48),Row(555,300,0xABC,50,333)});
    assert(VerifyPersistedTicketDebit(Blob(original),Blob(foreign),120,20,
        SyntheticStackCodec,nullptr).status==AuditStatus::UnrelatedInventoryChanged);
    auto swapped=Pack({Row(ticket,101,20,50),Row(555,300,0xABC,49,333)});
    assert(VerifyPersistedTicketDebit(Blob(original),Blob(swapped),120,20,
        SyntheticStackCodec,nullptr).status==AuditStatus::TicketIdentityChanged);
    auto replaced=Pack({Row(ticket,999,20,48),Row(555,300,0xABC,49,333)});
    assert(VerifyPersistedTicketDebit(Blob(original),Blob(replaced),120,20,
        SyntheticStackCodec,nullptr).status==AuditStatus::TicketIdentityChanged);
    auto duplicated=Pack({Row(ticket,101,120,48),Row(555,101,0xABC,49,333)});
    assert(VerifyPersistedTicketDebit(Blob(duplicated),Blob(saved),120,20,
        SyntheticStackCodec,nullptr).status==AuditStatus::DuplicateSerialOrSlot);
    auto sameSlot=Pack({Row(ticket,101,120,48),Row(555,300,0xABC,48,333)});
    assert(VerifyPersistedTicketDebit(Blob(sameSlot),Blob(saved),120,20,
        SyntheticStackCodec,nullptr).status==AuditStatus::DuplicateSerialOrSlot);
    auto truncated=original;truncated.pop_back();
    assert(VerifyPersistedTicketDebit(Blob(truncated),Blob(saved),120,20,
        SyntheticStackCodec,nullptr).status==AuditStatus::MalformedSnapshot);
    auto unknown=Pack({Row(ticket,101,0x10078,48),Row(555,300,0xABC,49,333)});
    assert(VerifyPersistedTicketDebit(Blob(unknown),Blob(saved),120,20,
        SyntheticStackCodec,nullptr).status==AuditStatus::QuantityCodecFailed);
    auto invalid=Pack({Row(ticket,0,120,48),Row(555,300,0xABC,49,333)});
    assert(VerifyPersistedTicketDebit(Blob(invalid),Blob(saved),120,20,
        SyntheticStackCodec,nullptr).status==AuditStatus::InvalidRecord);
    TestPersistenceBarrier(false,false); // no trusted stack decoding => NO S2C success
    TestPersistenceBarrier(audit.Verified(),true); // synthetic verified evidence
    std::cout<<"DIAMOND_RECORD30_PERSISTED_INVENTORY_AUDIT=PASS\n"
             <<"MASTERY_MUST_NOT_DEBIT_TICKETS=PASS\n"
          <<"INVENTORY_STACK_CODEC_MANDATORY=PASS\n"
             <<"UNTRUSTED_OR_CHANGED_OTHER_ITEMS_REJECTED=PASS\n"
             <<"IPC47_ACK_ALONE_NEVER_GAME_SUCCESS=PASS\n"
             <<"LIVE_GAME_QUANTITY_CODEC_OR_MSSQL=NOT_VERIFIED\n";
}
