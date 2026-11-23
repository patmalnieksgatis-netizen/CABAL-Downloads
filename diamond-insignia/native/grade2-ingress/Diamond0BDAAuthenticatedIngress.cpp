#include "Diamond0BDAAuthenticatedIngress.h"
#include "../world-session-bridge/deps/EventPassOwnerV282.h"
#include <cstring>
#include <limits>

namespace diamond_v291::gradeup0bda {
namespace {
class Lease final {
    diamond_v291::WorldSessionAuthority* authority_;
    const void* ctx_;
    bool acquired_=false;
public:
    Lease(diamond_v291::WorldSessionAuthority* authority,
          const void* ctx) noexcept : authority_(authority),ctx_(ctx){}
    bool Acquire(diamond_v291::LockedWorldSession& out) noexcept {
        if(!authority_ || !ctx_)return false;
        if(!authority_->AcquireExclusive(ctx_,out))return false;
        acquired_=true;
        return true;
    }
    ~Lease(){if(acquired_)authority_->ReleaseExclusive(ctx_);}
    Lease(const Lease&)=delete;
    Lease& operator=(const Lease&)=delete;
};
GameActionResult Denied() noexcept {
    GameActionResult r{};
    r.state=GameActionState::MissingWorldAuthority;
    return r;
}
} // namespace
GameActionResult ExecuteAuthenticated0BDA(
    const void* worldUserCtx,const void* clientFrame,
    std::size_t verifiedFrameBytes,
    const AuthenticatedIngressHost& host) noexcept {
    // No game lock, pointer dereference or callback for Platinum or any
    // unrelated command. The caller MUST forward those unchanged.
    const auto parsed=ParseC2s(clientFrame,verifiedFrameBytes);
    if(parsed.state==PacketState::Other) {
        GameActionResult result{};
        result.state=GameActionState::NotDiamondCommand;
        return result;
    }
    if(parsed.state!=PacketState::Candidate) {
        GameActionResult result{};
        result.state=GameActionState::InvalidPacket;
        return result;
    }
    if(!host.authority || !host.data.readLockedState ||
       !host.data.exactWorldSvrLayoutAndHashVerified ||
       !worldUserCtx)return Denied();

    Lease lease(host.authority,worldUserCtx);
    diamond_v291::LockedWorldSession locked{};
    if(!lease.Acquire(locked))return Denied();
    // Holding the EXCLUSIVE real WorldSvr owner lease is mandatory for
    // reading these v14 source-confirmed offsets.
    if(!locked.userData || !locked.registeredUserNum ||
       !locked.registeredCharacterIdx || !locked.sessionGeneration ||
       locked.registeredUserNum>static_cast<std::uint32_t>(INT32_MAX) ||
       locked.registeredCharacterIdx>static_cast<std::uint32_t>(INT32_MAX))
        return Denied();
    const auto* ctx=static_cast<const unsigned char*>(worldUserCtx);
    const void* referencedData=nullptr;
    std::memcpy(&referencedData,ctx+0xE8,sizeof(referencedData));
    if(referencedData!=locked.userData)return Denied();

    EventPassOwnerV282::OwnerIdentity read{};
    if(!EventPassOwnerV282::Resolve(locked.userData,&read) ||
       read.ownerScope!=EventPassOwnerV282::kOwnerScopeAccount ||
       read.userNum!=locked.registeredUserNum ||
       read.characterIdx!=locked.registeredCharacterIdx)
        return Denied();
    const AttestedLiveWorldUser identity{
        worldUserCtx,locked.userData,read.userNum,read.characterIdx,
        locked.sessionGeneration};
    LockedGameOwner owner{};
    if(!host.data.readLockedState(host.data.hostContext,identity,owner))
        return Denied();
    // A callback cannot replace the resolved account/character identity,
    // session generation or active owner-locked context with its own.
    if(owner.worldUserCtx!=worldUserCtx ||
       owner.registeredUserNum!=identity.userNum ||
       owner.registeredCharacterIdx!=identity.characterIdx ||
       owner.sessionGeneration!=identity.sessionGeneration ||
       !owner.ownerExclusiveLockHeld)
        return Denied();
    // The lock stays held during grade-up validation and through the
    // atomic commit callback. No S2C is sent from this adapter.
    return PrepareAndCommitRealGradeUp(
        clientFrame,verifiedFrameBytes,owner,host.game);
}
} // namespace diamond_v291::gradeup0bda
