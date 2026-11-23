#include "DiamondWorldSessionBridge.h"
#include "EventPassOwnerV282.h"  // unchanged real v14 owner source
#include <cstring>
#include <limits>
#include <utility>

namespace diamond_v291 {
namespace {
constexpr std::size_t kV14UserDataPtrOffset = 0xE8;
static_assert(sizeof(void*)==8,"v14 Linux WorldSvr requires ELF64 pointers");
class AuthorityGuard {
public:
    AuthorityGuard(WorldSessionAuthority& auth,const void* ctx) noexcept
        :auth_(auth),ctx_(ctx){}
    bool Acquire(LockedWorldSession& lease) noexcept {
        if(!ctx_ || !auth_.AcquireExclusive(ctx_,lease)) return false;
        held_=true;
        return true;
    }
    ~AuthorityGuard(){if(held_) auth_.ReleaseExclusive(ctx_);}
    AuthorityGuard(const AuthorityGuard&)=delete;
    AuthorityGuard& operator=(const AuthorityGuard&)=delete;
private:
    WorldSessionAuthority& auth_;
    const void* ctx_;
    bool held_=false;
};
struct AttestBinding {
    const void* worldUserCtx=nullptr;
    SessionProof proof{};
};
bool AttestOnlyLockedWorldSession(const void* ptr,VerifiedSession& out,
                                  void* opaque) noexcept {
    out={};
    const auto* binding=static_cast<const AttestBinding*>(opaque);
    if(!binding || ptr!=binding->worldUserCtx || !binding->proof.Verified())
        return false;
    out=binding->proof.account;
    return true;
}
}
SessionProof ProveWorldSessionV14(const void* worldUserCtx,
                                 const LockedWorldSession& lease) noexcept {
    SessionProof proof{};
    proof.error=SessionProofError::InvalidLease;
    if(!worldUserCtx || !lease.userData || lease.registeredUserNum==0 ||
       lease.registeredCharacterIdx==0 || lease.sessionGeneration==0 ||
       lease.labNonce<=0 || lease.registeredUserNum>static_cast<std::uint32_t>(INT32_MAX) ||
       lease.registeredCharacterIdx>static_cast<std::uint32_t>(INT32_MAX)) return proof;
    // Session authority guaranteed pointer liveness and lock lifetime.
    const auto* ctxBytes=static_cast<const unsigned char*>(worldUserCtx);
    const void* dataFromContext=nullptr;
    std::memcpy(&dataFromContext,ctxBytes+kV14UserDataPtrOffset,sizeof(dataFromContext));
    if(dataFromContext != lease.userData){
        proof.error=SessionProofError::UserDataPointerMismatch;
        return proof;
    }
    EventPassOwnerV282::OwnerIdentity owner{};
    if(!EventPassOwnerV282::Resolve(lease.userData,&owner) ||
       owner.ownerScope!=EventPassOwnerV282::kOwnerScopeAccount){
        proof.error=SessionProofError::OwnerReadFailure;
        return proof;
    }
    if(owner.userNum!=lease.registeredUserNum ||
       owner.characterIdx!=lease.registeredCharacterIdx){
        proof.error=SessionProofError::RegistryIdentityMismatch;
        return proof;
    }
    proof.account.userNum=owner.userNum;
    proof.account.characterIdx=owner.characterIdx;
    proof.account.shadowNonce=lease.labNonce;
    proof.generation=lease.sessionGeneration;
    proof.error=SessionProofError::Valid;
    return proof;
}
Result ExecuteAttestedDiamondLab(const cabal_diamond_engine* engine,
                                 WorldSessionAuthority& authority,
                                 const void* worldUserCtx,
                                 const Request& request,
                                 const std::string& odbcConnectionString){
    Result failed{};
    failed.status=Status::AuthFailure;
    if(!engine || !worldUserCtx) return failed;
    AuthorityGuard guard(authority,worldUserCtx);
    LockedWorldSession lease{};
    if(!guard.Acquire(lease)) return failed;
    const SessionProof proof=ProveWorldSessionV14(worldUserCtx,lease);
    if(!proof.Verified()) return failed;
    const AttestBinding binding{worldUserCtx,proof};
    DiamondLabOdbcBackend backend(odbcConnectionString,
                                 &AttestOnlyLockedWorldSession,
                                 const_cast<AttestBinding*>(&binding));
    // Lease is held until after the backend commits/rolls back and dies.
    return Execute(engine,backend,worldUserCtx,request);
}
const char* SessionProofErrorName(SessionProofError x) noexcept {
    switch(x){
      case SessionProofError::Valid:return "Valid";
      case SessionProofError::MissingAuthority:return "MissingAuthority";
      case SessionProofError::NoLiveSession:return "NoLiveSession";
      case SessionProofError::InvalidLease:return "InvalidLease";
      case SessionProofError::UserDataPointerMismatch:return "UserDataPointerMismatch";
      case SessionProofError::RegistryIdentityMismatch:return "RegistryIdentityMismatch";
      case SessionProofError::OwnerReadFailure:return "OwnerReadFailure";
    }
    return "Unknown";
}
} // namespace diamond_v291
