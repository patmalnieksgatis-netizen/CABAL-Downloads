#include "DiamondV14SessionLeasePort.h"
#include <memory>
#include <new>

namespace diamond_v291 {
namespace {
// One lease token per operation. The trusted WorldSessionAuthority must keep
// both USERCONTEXT and USERDATACONTEXT readable and stable until Release.
struct LeaseToken {
    WorldSessionAuthority* sessions=nullptr;
    const void* worldUserCtx=nullptr;
    bool held=false;
    ~LeaseToken() noexcept {
        if(held && sessions) sessions->ReleaseExclusive(worldUserCtx);
    }
};
}
int DiamondV14SessionLeasePort::Acquire(
        void* opaque,const void* worldUserCtx,
        const DiamondIngress::Observation* candidate,void** outLease,
        DiamondBoundIngress::VerifiedIdentity* out) noexcept {
    if(!outLease || !out) return -1;
    *outLease=nullptr;
    *out={};
    if(!opaque || !worldUserCtx || !candidate || !candidate->candidate)
        return -2;
    auto* port=static_cast<DiamondV14SessionLeasePort*>(opaque);
    // std::nothrow: the ABI callback is noexcept and must fail closed on OOM.
    std::unique_ptr<LeaseToken> token(new(std::nothrow) LeaseToken{});
    if(!token)return -3;
    token->sessions=&port->sessions_;
    token->worldUserCtx=worldUserCtx;

    LockedWorldSession lease{};
    if(!port->sessions_.AcquireExclusive(worldUserCtx,lease))return -4;
    token->held=true; // every later failure releases the acquired lock

    // This routine uses the exact v14 owner offsets, checking pointer equality
    // and comparing account/character against the independent registry lease.
    // It is safe ONLY while the host-supplied registry lease owns both regions.
    const SessionProof proof=ProveWorldSessionV14(worldUserCtx,lease);
    if(!proof.Verified() || proof.account.userNum!=
       DiamondBoundIngress::kSyntheticUserNum)return -5;

    CatalogSelection selection{};
    if(!port->catalog_.ReadUnderExclusiveLease(lease,proof,selection) ||
       !selection.trustedRevision ||
       !selection.isDiamondGrade ||
       !selection.serverMeritSelectorIsDiamond ||
       selection.serverMasteryId!=candidate->mastery_id ||
       selection.serverSecondDword!=candidate->second_field)
       return -6;

    out->authenticated_session=worldUserCtx;
    out->user_num=proof.account.userNum;
    out->expected_revision=selection.trustedRevision;
    out->server_catalog_grade_two_confirmed=1;
    out->server_selector_confirms_diamond=1;
    out->first_payload_dword_authoritatively_matched=1;
    out->second_payload_dword_authoritatively_matched=1;
    out->matched_first_payload_dword=selection.serverMasteryId;
    out->matched_second_payload_dword=selection.serverSecondDword;

    // Transfer ownership to ABI-v3 ScopedLease, which spans the bridge
    // transaction and ensures release after commit, abort or exception.
    *outLease=token.release();
    return 0;
}
void DiamondV14SessionLeasePort::Release(void* opaque,
                                         void* leaseToken) noexcept {
    if(!opaque || !leaseToken)return;
    delete static_cast<LeaseToken*>(leaseToken);
}
} // namespace diamond_v291
