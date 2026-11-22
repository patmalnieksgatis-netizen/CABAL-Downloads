#include "DiamondWorldSaveBarrier.h"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
using namespace diamond_v291;

static Operation operation(){
    Operation x{};
    x.durableIntent=0xACED;
    x.userNum=900001; x.characterIdx=1230001;
    x.expectedRevision=10; x.appliedRevision=11;
    x.command=1; x.newBadgeGrade=2; x.newWexp=10000;
    x.newTickets=20;
    return x;
}
static DurableSnapshot snap(const Operation& x){
    DurableSnapshot s{};
    s.verifiedGameInventory=true;s.verifiedGameWexp=true;
    s.receiptCommitted=true;s.durableIntent=x.durableIntent;
    s.userNum=x.userNum;s.characterIdx=x.characterIdx;
    s.revision=x.appliedRevision;s.badgeGrade=x.newBadgeGrade;
    s.wexp=x.newWexp;s.tickets=x.newTickets;
    s.masteryId=x.masteryId;s.masteryLevel=x.newMasteryLevel;
    return s;
}
static void wr16(unsigned char* p,std::uint16_t v){p[0]=v&0xff;p[1]=v>>8;}
static void wr32(unsigned char* p,std::uint32_t v){wr16(p,v&0xffff);wr16(p+2,v>>16);}
static void ack(unsigned char* p,const Operation& o,std::uint32_t flags){
    std::memset(p,0,kIpcResultSize);
    wr16(p,kIpcMagic);wr16(p+2,kIpcResultSize);wr16(p+8,kIpcResultUpdateChDat);
    wr32(p+10,o.characterIdx);wr32(p+14,flags);
}
int main(){
    const auto o=operation();
    unsigned char packet[kIpcResultSize];
    ack(packet,o,0x800);
    { // must reconcile full durable state after ACK, never before
        DiamondWorldSaveBarrier g;
        assert(!g.MaySendSuccess());
        assert(g.Begin(o,true,true)==Verdict::Ok);
        assert(!g.MaySendSuccess());
        assert(g.MarkNativeMutationApplied(true)==Verdict::Ok);
        assert(g.MarkSaveSent(0x800,100,0)==Verdict::Ok);
        assert(g.ObserveIpcResult47(packet,sizeof(packet),101,1)==Verdict::Ok);
        assert(!g.MaySendSuccess());
        assert(g.Reconcile(snap(o))==Verdict::Ok);
        assert(g.MaySendSuccess());
        assert(g.ObserveIpcResult47(packet,sizeof(packet),102,1)==Verdict::DuplicateAck);
        assert(g.Begin(o,true,true)==Verdict::IllegalPhase);
    }
    { // concurrent character save cannot claim successful persistence
        DiamondWorldSaveBarrier g;
        assert(g.Begin(o,true,true)==Verdict::Ok);
        assert(g.MarkNativeMutationApplied(true)==Verdict::Ok);
        assert(g.MarkSaveSent(0x800,100,2)==Verdict::AmbiguousSave);
        assert(g.GetPhase()==Phase::RecoveryRequired);
        assert(!g.MaySendSuccess());
    }
    { // foreign/invalid/stale ACK cannot complete
        DiamondWorldSaveBarrier g;
        assert(g.Begin(o,true,true)==Verdict::Ok);
        assert(g.MarkNativeMutationApplied(true)==Verdict::Ok);
        assert(g.MarkSaveSent(0x800,100,0)==Verdict::Ok);
        assert(g.ObserveIpcResult47(packet,sizeof(packet),99,1)==Verdict::StaleAck);
        wr32(packet+10,o.characterIdx+1);
        assert(g.ObserveIpcResult47(packet,sizeof(packet),101,1)==Verdict::ForeignAck);
        ack(packet,o,0x801);
        assert(g.ObserveIpcResult47(packet,sizeof(packet),101,1)==Verdict::ForeignAck);
        ack(packet,o,0x800);packet[8]=99;
        assert(g.ObserveIpcResult47(packet,sizeof(packet),101,1)==Verdict::Invalid);
        ack(packet,o,0x800);
        assert(g.ObserveIpcResult47(packet,sizeof(packet),101,2)==Verdict::AmbiguousSave);
        assert(!g.MaySendSuccess());
    }
    { // require trusted session and durable intent
        DiamondWorldSaveBarrier g;
        assert(g.Begin(o,false,true)==Verdict::Invalid);
        assert(g.Begin(o,true,false)==Verdict::Invalid);
        assert(!g.MaySendSuccess());
    }
    { // never success on a mismatching actual inventory count
        DiamondWorldSaveBarrier g;
        assert(g.Begin(o,true,true)==Verdict::Ok);
        assert(g.MarkNativeMutationApplied(true)==Verdict::Ok);
        assert(g.MarkSaveSent(0x800,100,0)==Verdict::Ok);
        assert(g.ObserveIpcResult47(packet,sizeof(packet),101,1)==Verdict::Ok);
        auto s=snap(o);s.tickets+=1;
        assert(g.Reconcile(s)==Verdict::SnapshotMismatch);
        assert(g.GetPhase()==Phase::RecoveryRequired);
        assert(!g.MaySendSuccess());
    }
    { // ACK lost => durable recovery needed
        DiamondWorldSaveBarrier g;
        assert(g.Begin(o,true,true)==Verdict::Ok);
        assert(g.MarkNativeMutationApplied(true)==Verdict::Ok);
        assert(g.MarkSaveSent(0x800,100,0)==Verdict::Ok);
        assert(g.MarkTimeout()==Verdict::NeedRecovery);
        assert(!g.MaySendSuccess());
    }
    { // mastery persistence requires mastery-level parity
        Operation mastery=o;mastery.command=2;mastery.masteryId=159;
        mastery.newMasteryLevel=2;mastery.durableIntent++;
        DiamondWorldSaveBarrier g;
        assert(g.Begin(mastery,true,true)==Verdict::Ok);
        assert(g.MarkNativeMutationApplied(true)==Verdict::Ok);
        assert(g.MarkSaveSent(0x800,200,0)==Verdict::Ok);
        ack(packet,mastery,0x800);
        assert(g.ObserveIpcResult47(packet,sizeof(packet),201,1)==Verdict::Ok);
        auto s=snap(mastery);s.masteryLevel=1;
        assert(g.Reconcile(s)==Verdict::SnapshotMismatch);
        assert(!g.MaySendSuccess());
    }
    { // explicit bad revision / invalid Diamond mastery ID
        Operation bad=o;bad.expectedRevision=std::numeric_limits<std::uint32_t>::max();
        bad.appliedRevision=0;
        DiamondWorldSaveBarrier g;
        assert(g.Begin(bad,true,true)==Verdict::Invalid);
        bad=o;bad.command=2;bad.masteryId=158;bad.newMasteryLevel=1;
        assert(g.Begin(bad,true,true)==Verdict::Invalid);
    }
    std::cout<<"DIAMOND_WORLD_SAVE_BARRIER_TEST=PASS\n"
             <<"IPC_46_47_18B=VALIDATED_AGAINST_SOURCE\n"
             <<"ACK_WITHOUT_DURABLE_RECONCILIATION=CANNOT_ACK_SUCCESS\n"
             <<"AMBIGUOUS_CONCURRENT_SAVE=RECOVERY_REQUIRED\n"
             <<"LIVE_VM_UNCHANGED=YES\n";
}
