// Offline regression tests. Synthetic data only. No database, sockets, game
// process, live registry, or runtime installation.
#include "../native/world-save-barrier/DiamondWorldSaveBarrier.h"
#include "../native/grade2-ingress/Diamond0BDASaveReplyGate.h"
#include <cassert>
#include <cstdio>
using namespace diamond_v291;
using namespace diamond_v291::gradeup0bda;
static Operation operation() {
    Operation o{};
    o.durableIntent=17; o.userNum=7; o.characterIdx=42;
    o.expectedRevision=3; o.appliedRevision=4; o.command=1;
    o.newBadgeGrade=2;o.beforeWexp={35000,90000,7};
    o.afterWexp={5000,90000,30007};o.newTickets=23;
    return o;
}
static void blocked(const DiamondWorldSaveBarrier& b) {
    assert(!b.MaySendSuccess());
    auto r=StageCandidateSuccess(b,true,true);
    assert(r.result==ReplyGateResult::NoWorldSaveProof);
    assert(!r.canSendToClient);
    for(auto v:r.bytes)assert(v==0);
}
int main() {
    auto o=operation();
    {
        DiamondWorldSaveBarrier b;
        blocked(b);
        assert(b.Begin(o,false,true)==Verdict::Invalid);
        assert(b.Begin(o,true,false)==Verdict::Invalid);
        assert(b.GetPhase()==Phase::Empty);
        assert(b.Begin(o,true,true)==Verdict::Ok);
        blocked(b);
        assert(b.Begin(o,true,true)==Verdict::IllegalPhase);
        assert(b.MarkNativeMutationApplied(false)==Verdict::NeedRecovery);
        assert(b.GetPhase()==Phase::RecoveryRequired);
        assert(b.Begin(o,true,true)==Verdict::IllegalPhase);
        blocked(b);
    }
    {
        DiamondWorldSaveBarrier b;
        assert(b.Begin(o,true,true)==Verdict::Ok);
        assert(b.MarkNativeMutationApplied(true)==Verdict::Ok);
        blocked(b);
        assert(b.MarkSaveSent(kSaveInventory,9,1)==Verdict::AmbiguousSave);
        assert(b.GetPhase()==Phase::RecoveryRequired);
        blocked(b);
    }
    {
        DiamondWorldSaveBarrier b;
        assert(b.Begin(o,true,true)==Verdict::Ok);
        assert(b.MarkNativeMutationApplied(true)==Verdict::Ok);
        assert(b.MarkSaveSent(kSaveInventory,9,0)==Verdict::Ok);
        blocked(b);
        DurableSnapshot s{};
        assert(b.Reconcile(s)==Verdict::IllegalPhase);
        assert(b.ObserveIpcResult47(nullptr,0,10,1)==Verdict::Invalid);
        assert(b.GetPhase()==Phase::SaveSent);
        assert(b.MarkTimeout()==Verdict::NeedRecovery);
        assert(b.GetPhase()==Phase::RecoveryRequired);
        assert(b.Reconcile(s)==Verdict::IllegalPhase);
        blocked(b);
    }
    {
        DiamondWorldSaveBarrier b;
        assert(b.Begin(o,true,true)==Verdict::Ok);
        assert(b.MarkTimeout()==Verdict::NeedRecovery);
        blocked(b);
    }
    {
        DiamondWorldSaveBarrier b;
        assert(b.Begin(o,true,true)==Verdict::Ok);
        assert(b.MarkNativeMutationApplied(true)==Verdict::Ok);
        assert(b.MarkTimeout()==Verdict::NeedRecovery);
        blocked(b);
    }
    for(unsigned i=0;i<2;++i) {
        DiamondWorldSaveBarrier b;
        assert(b.Begin(o,true,true)==Verdict::Ok);
        assert(b.MarkNativeMutationApplied(true)==Verdict::Ok);
        assert(b.MarkSaveSent(i?1:0,i?0:9,0)==Verdict::NeedRecovery);
        assert(b.GetPhase()==Phase::RecoveryRequired);
        assert(b.MarkSaveSent(kSaveInventory,9,0)==Verdict::IllegalPhase);
        blocked(b);
    }
    std::puts("DIAMOND_OFFLINE_PERSISTENCE_DENIAL=PASS");
}
