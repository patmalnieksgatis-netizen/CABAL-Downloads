#include "DiamondGrade2Ingress.h"
#include <cstdint>

namespace diamond_v291::grade2 {
namespace {
std::uint16_t U16(const std::uint8_t* p) noexcept {
    return static_cast<std::uint16_t>(p[0]) |
           static_cast<std::uint16_t>(p[1])<<8;
}
std::uint32_t U32(const std::uint8_t* p) noexcept {
    return static_cast<std::uint32_t>(U16(p)) |
           static_cast<std::uint32_t>(U16(p+2))<<16;
}
bool Attested(const Proof& proof,const CandidatePacket& request) noexcept {
    return proof.authenticatedSession &&
           proof.catalogGrade2Verified &&
           proof.selectorSemanticVerified &&
           proof.actualInventoryWexpBackendReady &&
           proof.boundWorldSession!=nullptr &&
           proof.authenticatedUserNum!=0 &&
           proof.trustedSessionNonce!=0 &&
           proof.trustedRevision!=0 &&
           request.rawClientSelector==proof.serverVerifiedSelector;
}
} // namespace

CandidatePacket ParseC2s(const void* data,std::size_t size) noexcept {
    CandidatePacket out{};
    if(!data || size<10)return out;
    const auto* p=static_cast<const std::uint8_t*>(data);
    if(U16(p)!=0xB7E2u) {
        out.kind=PacketKind::Other;
        return out;
    }
    if(U16(p+8)!=kCandidateOpcode) {
        out.kind=PacketKind::Other;  // preserve Platinum 0x0B10 and all others
        return out;
    }
    if(size!=kC2sBytes || U16(p+2)!=size)return out;
    const auto selector=U32(p+10);
    if(selector==kInvalidClientSelector)return out;
    out.kind=PacketKind::Candidate;
    out.rawClientSelector=selector; // NEVER identity/grade/revision from client
    return out;
}

Result ExecuteCandidate(const void* data,std::size_t size,
                        const Proof& proof,
                        diamond::DiamondCommandService& rules) noexcept {
    Result result{};
    const auto packet=ParseC2s(data,size);
    if(packet.kind==PacketKind::Other) {
        result.route=Route::Original;
        return result;
    }
    if(packet.kind!=PacketKind::Candidate) {
        result.route=Route::Invalid;
        return result;
    }
    if(!Attested(proof,packet)) {
        result.route=Route::Disabled;
        return result;
    }
#ifndef DIAMOND_ENABLE_GRADE2_CLONE_TRIAL
    (void)rules;
    result.route=Route::Disabled;
    return result;
#else
    try {
        // The packet does not carry user/revision/grade. All of those are
        // taken ONLY from the session-bound server proof and trusted backend.
        const diamond::Session session{
            proof.authenticatedUserNum,proof.trustedSessionNonce};
        const diamond::Command command{
            diamond::CommandType::RankUp,proof.trustedRevision,0};
        result.transaction=rules.handle(session,command);
        result.route=(result.transaction.status==diamond::OperationStatus::Applied)
            ? Route::BackendAppliedPendingSaveProof : Route::Rejected;
    }catch(...) {
        result.route=Route::Rejected;
    }
    // Even if a synthetic backend reports Applied, this layer NEVER
    // manufactures/authorizes a client success response. The live system
    // needs separate durable WorldSaveBarrier and S2C ABI verification.
    result.maySendS2cSuccess=false;
    return result;
#endif
}
} // namespace diamond_v291::grade2
