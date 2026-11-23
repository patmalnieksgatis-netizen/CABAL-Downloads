#include "Diamond0BDAWorldContext.h"
namespace diamond_v291::gradeup0bda {
DispatchResult Dispatch(const ProcessDataContext* ctx,
                        std::size_t verifiedFrameSize,
                        bool originalTransportIntegrityVerified,
                        std::uint32_t verifiedProcessLayer,
                        const HostAdapter& trustedHost,
                        diamond::DiamondCommandService& service) noexcept {
    DispatchResult result{};
    // Real WorldSvr supplies an authenticated context and already validates
    // network framing; this shim refuses to equate iLen with transport truth.
    if(!ctx || !ctx->pUserCtx || !ctx->cpPacket ||
       verifiedFrameSize!=ctx->iLen ||
       verifiedFrameSize<10 || verifiedFrameSize>65535 ||
       !originalTransportIntegrityVerified) {
        result.state=DispatchState::InvalidFrame;
        return result;
    }
    const Candidate packet=ParseC2s(ctx->cpPacket,verifiedFrameSize);
    if(packet.state==PacketState::Other) {
        result.state=DispatchState::Original;
        return result;
    }
    if(packet.state!=PacketState::Candidate) {
        result.state=DispatchState::InvalidFrame;
        return result;
    }
    if(trustedHost.version!=kHostProofAdapterVersion || !trustedHost.attest) {
        result.state=DispatchState::Disabled;
        return result;
    }
    WorldProof authority{};
    if(!trustedHost.attest(trustedHost.context,ctx->pUserCtx,
                           verifiedProcessLayer,packet,authority) ||
       authority.boundWorldSession!=ctx->pUserCtx) {
        result.state=DispatchState::Disabled;
        return result;
    }
    const auto routed=ExecuteCandidate(ctx->cpPacket,verifiedFrameSize,
                                       authority,service);
    switch(routed.route) {
        case Route::Original:result.state=DispatchState::Original;break;
        case Route::Invalid:result.state=DispatchState::InvalidFrame;break;
        case Route::Disabled:result.state=DispatchState::Disabled;break;
        case Route::Rejected:result.state=DispatchState::CloneBackendRejected;break;
        case Route::CloneBackendAppliedPendingSaveProof:
            result.state=DispatchState::CloneBackendAppliedPendingSaveProof;
            result.hostStateWasChanged=true; // synthetic mock only
            break;
    }
    // Success can ONLY be determined by independent durable-save receipt,
    // replay protection and actual game payload serialization, not this shim.
    result.maySendS2cSuccess=false;
    return result;
}
} // namespace diamond_v291::gradeup0bda
