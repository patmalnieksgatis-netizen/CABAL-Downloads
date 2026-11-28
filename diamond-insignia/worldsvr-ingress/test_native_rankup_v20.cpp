// V20 integration test: fake registry and bridge, no live SQL or server.
#include "DiamondNativeRankUpV20.h"
#include <cassert>
#include <array>
#include <cstdlib>
#include <vector>
using namespace diamond_v19;
namespace gu=diamond_v291::gradeup0bda;
namespace rg=diamond_v291::real_gamedata;
namespace completion=diamond_v291::completion;
struct Port final:completion::NativePort {
    bool HeldSessionMatches(const completion::Identity&) noexcept override{return true;}
    bool ApplyCommitted(const rg::RankUpCommitRecord&) noexcept override{return true;}
    bool ReserveSave(completion::SaveReservation& r) noexcept override{r={0x800,0,100};return true;}
    bool PublishSave(const completion::SaveReservation&) noexcept override{return true;}
    bool ReplyAbiVerified() const noexcept override{return true;}
    bool SendRankUpSuccess(const completion::Identity&,const std::array<std::uint8_t,7>&) noexcept override{return true;}
    void ReleaseAfterReconciliation(const completion::Identity&) noexcept override{}
};
static Port port;
static std::vector<std::unique_ptr<completion::RankUpCompletion>> retained;
static int bridgeCalls=0,finishCalls=0,begins=0,freed=0;
static bool mismatchedOwner=false;
static gu::GameActionState nextState=gu::GameActionState::CommittedPendingSaveProof;
static gu::GameActionState observed=gu::GameActionState::InvalidPacket;
// Replace the actual transaction symbol only for this offline wiring test.
namespace diamond_v291::real_gamedata {
gu::GameActionResult Execute0BDARealServer01(const void*,const void*,std::size_t n,const Real0BDAHost& h) noexcept {
    assert(n==14 && h.transaction);
    ++bridgeCalls;
    if(nextState==gu::GameActionState::CommittedPendingSaveProof ||
       nextState==gu::GameActionState::InDoubtRecoveryRequired){
        auto record=std::make_unique<RankUpCommitRecord>();
        record->sessionGeneration=77;
        auto& o=record->operation;
        o.userNum=5005;o.characterIdx=24055;o.durableIntent=998877;
        o.expectedRevision=5;o.appliedRevision=6;o.command=1;o.newBadgeGrade=2;
        o.beforeWexp={35000,90000,7};o.afterWexp={5000,90000,30007};o.newTickets=899;
        record->inventoryBefore.resize(30);record->inventoryAfter.resize(30);
        if(nextState==gu::GameActionState::CommittedPendingSaveProof)
            h.transaction->committedRankUp=std::move(record);
        else h.transaction->recoveryRankUp=std::move(record);
    }
    gu::GameActionResult r{};r.state=nextState;return r;
}
bool VerifySavedRankUpServer01(const std::string&,const RankUpCommitRecord&) noexcept{return true;}
}
namespace diamond_v291::gradeup0bda {
Candidate ParseC2s(const void* data,std::size_t n) noexcept {
    Candidate r{};
    if(!data || n!=14)return r;
    auto* p=static_cast<const unsigned char*>(data);
    r.state=p[8]==0xda && p[9]==0x0b ? PacketState::Candidate:PacketState::Other;
    return r;
}
}
static void* Create() noexcept {
    auto* p=std::calloc(1,kMapBytes);
    if(p)Write<std::uint8_t>(p,0x20,1);
    return p;
}
static void Destroy(void* p) noexcept {
    std::free(Read<Handler*>(p,0));std::free(p);++freed;
}
static bool Append(void* p,Handler h) noexcept {
    auto* v=static_cast<Handler*>(std::malloc(sizeof(Handler)));
    if(!v)return false;
    *v=h;Write(p,0,v);Write(p,8,v+1);Write(p,16,v+1);return true;
}
static bool Begin(void*,void*,const ContextPrefix& native,diamond_v20::Request& r) noexcept {
    ++begins;r.fenceToken=&begins;r.bridge.transaction=&r.transaction;
    r.transaction.odbcConnectionString="fixture-no-connection";
    r.transaction.attestedUserNum=5005;r.transaction.attestedCharacterIdx=24055;
    if(mismatchedOwner)r.transaction.attestedCharacterIdx++;
    r.transaction.attestedSessionGeneration=77;
    r.transaction.attestedWorldUserCtx=native.user;
    r.completion=std::make_unique<completion::RankUpCompletion>(
        port,completion::Identity{5005,24055,77,998877});
    return true;
}
static void Finish(void*,diamond_v20::Request& r,const gu::GameActionResult& result) noexcept {
    assert(r.fenceToken);
    ++finishCalls;observed=result.state;
    retained.push_back(std::move(r.completion));
}
int main(){
    std::array<void*,kSlots> user{},other{};
    int a=1,b=2;
    user[kPlatinum]=&a;user[kPlatinumCancel]=&b;
    Host h{};h.exactElfVerified=h.startupBeforeAnyDispatch=h.nativeObjectLifetimeVerified=h.realGameBackendReady=true;
    h.userTable=user.data();h.otherTable=other.data();h.readableSlots=kSlots;
    h.createMap=Create;h.destroyMap=Destroy;h.append=Append;
    diamond_v20::Binding bind{};bind.begin=Begin;bind.finish=Finish;
    assert(diamond_v20::Register(h,bind)==Status::Blocked);
    bind.verifiedRestorableClone=bind.originalDispatcherAndFrameIntegrityVerified=
      bind.independentOwnerFenceAndSaveCompletionVerified=bind.actualReplyAbiVerified=true;
#ifndef DIAMOND_ENABLE_0BDA_CLONE_TRIAL
    assert(diamond_v20::Register(h,bind)==Status::Blocked);
    return 0;
#endif
    other[kDiamond]=&a;
    assert(diamond_v20::Register(h,bind)==Status::Collision);
    assert(!diamond_v20::binding && !user[kDiamond]);
    other[kDiamond]=nullptr;
    assert(diamond_v20::Register(h,bind)==Status::Installed);
    assert(user[kPlatinum]==&a && user[kPlatinumCancel]==&b);
    auto entry=*Read<Handler*>(user[kDiamond],0);
    unsigned char frame[14]={0xe2,0xb7,14,0,0,0,0,0,0xda,0x0b,1,0,3,0};
    ContextPrefix c{&a,frame,14};
    assert(entry(nullptr,&c)==0);
    assert(bridgeCalls==1 && begins==1 && finishCalls==1);
    assert(observed==nextState && diamond_v20::pending.load()==1);
    assert(retained.size()==1 && retained[0]->GetState()==completion::State::WaitingForAck);
    nextState=gu::GameActionState::InDoubtRecoveryRequired;
    assert(entry(nullptr,&c)==0);
    assert(bridgeCalls==2 && finishCalls==2 && observed==nextState && diamond_v20::inDoubt.load()==1);
    assert(retained.size()==2 && retained[1]->GetState()==completion::State::RecoveryRequired);
    assert(retained[1]->HasRetainedEvidence());
    mismatchedOwner=true;
    assert(entry(nullptr,&c)==0);
    assert(bridgeCalls==2 && finishCalls==3 &&
           observed==gu::GameActionState::MissingWorldAuthority);
    mismatchedOwner=false;
    frame[8]=0x10;
    assert(entry(nullptr,&c)==0 && bridgeCalls==2);
    c.length=13;
    assert(entry(nullptr,&c)==0 && bridgeCalls==2);
    assert(diamond_v20::Register(h,bind)==Status::Blocked);
    Destroy(user[kDiamond]);
    // Test process is single-threaded; reset only fixture state on exit.
    user[kDiamond]=nullptr;diamond_v20::binding=nullptr;
    assert(freed==1);
}
