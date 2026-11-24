// V20 integration test: fake registry and bridge, no live SQL or server.
#include "DiamondNativeRankUpV20.h"
#include <cassert>
#include <array>
#include <cstdlib>
using namespace diamond_v19;
namespace gu=diamond_v291::gradeup0bda;
namespace rg=diamond_v291::real_gamedata;
static int bridgeCalls=0,finishCalls=0,begins=0,freed=0;
static gu::GameActionState nextState=gu::GameActionState::CommittedPendingSaveProof;
static gu::GameActionState observed=gu::GameActionState::InvalidPacket;
// Replace the actual transaction symbol only for this offline wiring test.
namespace diamond_v291::real_gamedata {
gu::GameActionResult Execute0BDARealServer01(const void*,const void*,std::size_t n,const Real0BDAHost& h) noexcept {
    assert(n==14 && h.transaction);
    ++bridgeCalls;
    gu::GameActionResult r{};r.state=nextState;return r;
}
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
static bool Begin(void*,void*,const ContextPrefix&,diamond_v20::Request& r) noexcept {
    ++begins;r.fenceToken=&begins;r.bridge.transaction=&r.transaction;return true;
}
static void Finish(void*,diamond_v20::Request& r,const gu::GameActionResult& result) noexcept {
    assert(r.fenceToken);
    ++finishCalls;observed=result.state;
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
    nextState=gu::GameActionState::InDoubtRecoveryRequired;
    assert(entry(nullptr,&c)==0);
    assert(bridgeCalls==2 && finishCalls==2 && observed==nextState && diamond_v20::inDoubt.load()==1);
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
