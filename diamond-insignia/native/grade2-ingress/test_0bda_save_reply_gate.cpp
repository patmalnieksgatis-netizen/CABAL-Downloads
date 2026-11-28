#include "Diamond0BDASaveReplyGate.h"
#include <cassert>
#include <cstdint>
#include <iostream>
using namespace diamond_v291;
using namespace diamond_v291::gradeup0bda;
namespace {
void Put16(unsigned char* p,std::uint16_t v) {
    p[0]=static_cast<unsigned char>(v);p[1]=static_cast<unsigned char>(v>>8);
}
void Put32(unsigned char* p,std::uint32_t v) {
    for(int i=0;i<4;++i)p[i]=static_cast<unsigned char>(v>>(8*i));
}
void Ack(unsigned char* p,std::uint32_t ch,std::uint32_t flags) {
    for(int i=0;i<18;++i)p[i]=0;
    Put16(p,0xB7E2);Put16(p+2,18);Put16(p+8,47);
    Put32(p+10,ch);Put32(p+14,flags);
}
Operation Operation21() {
    Operation o{};
    o.durableIntent=0xCAFEu;o.userNum=9911;o.characterIdx=2020;
    o.expectedRevision=21;o.appliedRevision=22;o.command=1;
    o.masteryId=0;o.newMasteryLevel=0;o.newBadgeGrade=2;
    o.beforeWexp={40000,100000,60000};
    o.afterWexp={10000,100000,90000};o.newTickets=20;
    return o;
}
DurableSnapshot Snapshot21() {
    DurableSnapshot s{};
    s.verifiedGameInventory=true;s.verifiedGameWexp=true;
    s.receiptCommitted=true;s.durableIntent=0xCAFEu;
    s.userNum=9911;s.characterIdx=2020;s.revision=22;
    s.badgeGrade=2;s.wexp={10000,100000,90000};s.tickets=20;
    s.masteryId=0;s.masteryLevel=0;
    return s;
}
} // namespace
int main() {
    DiamondWorldSaveBarrier barrier;
    auto none=StageCandidateSuccess(barrier,true,true);
    assert(none.result==ReplyGateResult::NoWorldSaveProof);
    assert(!none.canSendToClient);
    assert(barrier.Begin(Operation21(),true,true)==Verdict::Ok);
    assert(barrier.MarkNativeMutationApplied(true)==Verdict::Ok);
    assert(barrier.MarkSaveSent(0x77,100,0)==Verdict::Ok);
    unsigned char ack[18]{};
    Ack(ack,2021,0x77);
    assert(barrier.ObserveIpcResult47(ack,18,110,1)==Verdict::ForeignAck);
    assert(StageCandidateSuccess(barrier,true,true).result==
           ReplyGateResult::NoWorldSaveProof);
    Ack(ack,2020,0x77);
    assert(barrier.ObserveIpcResult47(ack,18,110,1)==Verdict::Ok);
    assert(!barrier.MaySendSuccess());
    assert(StageCandidateSuccess(barrier,true,true).result==
           ReplyGateResult::NoWorldSaveProof);
    const auto snap=Snapshot21();
    assert(barrier.Reconcile(snap)==Verdict::Ok);
    assert(barrier.MaySendSuccess());
    assert(StageCandidateSuccess(barrier,false,true).result==
           ReplyGateResult::MissingResponseAbiAttestation);
    assert(StageCandidateSuccess(barrier,true,false).result==
           ReplyGateResult::MissingResponseAbiAttestation);
    const auto result=StageCandidateSuccess(barrier,true,true);
#ifndef DIAMOND_ENABLE_0BDA_CLONE_TRIAL
    assert(result.result==ReplyGateResult::Blocked);
    assert(!result.canSendToClient);
    std::cout<<"GRADEUP_0BDA_PRODUCTION_ACK_DISABLED=PASS\n";
#else
    assert(result.result==ReplyGateResult::CloneCandidateEncoded);
    assert(result.bytes[0]==0xE2 && result.bytes[1]==0xB7);
    assert(result.bytes[2]==7 && result.bytes[3]==0);
    assert(result.bytes[4]==0xDA && result.bytes[5]==0x0B);
    assert(result.bytes[6]==1);
    assert(result.canSendToClient);
    std::cout<<"GRADEUP_0BDA_CLONE_ENCODING_WITH_ABI_PROOFS=PASS\n";
#endif
    // In a fresh transaction, bad persisted snapshot must require recovery.
    DiamondWorldSaveBarrier bad;
    assert(bad.Begin(Operation21(),true,true)==Verdict::Ok);
    assert(bad.MarkNativeMutationApplied(true)==Verdict::Ok);
    assert(bad.MarkSaveSent(0x77,100,0)==Verdict::Ok);
    assert(bad.ObserveIpcResult47(ack,18,110,1)==Verdict::Ok);
    auto mismatched=Snapshot21();
    mismatched.tickets=21;
    assert(bad.Reconcile(mismatched)==Verdict::SnapshotMismatch);
    assert(!bad.MaySendSuccess());
    assert(StageCandidateSuccess(bad,true,true).result==
           ReplyGateResult::NoWorldSaveProof);
    std::cout<<"GRADEUP_0BDA_FOREIGN_ACK_REJECTED=PASS\n"
             <<"GRADEUP_0BDA_MISMATCHED_PERSISTED_STATE_REJECTED=PASS\n"
             <<"GRADEUP_0BDA_NO_LIVE_PACKET_EMISSION=PASS\n";
}
