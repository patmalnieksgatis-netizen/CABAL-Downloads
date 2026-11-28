#pragma once
// V20: registered native 0BDA handler -> actual Server01 transaction bridge.
// Registration is opt-in, only at verified clone startup. No absolute-address
// calls or automatically enabled feature. The fence survives pending/uncertain
// commits; asynchronous save/reply completion is owned by the real host.
#include "DiamondNativeProcedureRegistrationV19.h"
#include "../native/real-gamedata-transaction/Diamond0BDARealServer01Bridge.h"
#include "../native/grade2-ingress/DiamondGradeUp0BDA.h"
#include "DiamondNativeRankUpCompletion.h"
#include <atomic>
#include <utility>

namespace diamond_v20 {
// Request now carries owned asynchronous completion. Do not mix an older
// compiled begin/finish provider with this header, even on the same WorldSvr.
inline constexpr unsigned kCompletionHostAbi=0x20261128u;
namespace rg=diamond_v291::real_gamedata;
namespace gu=diamond_v291::gradeup0bda;
struct Request {
    rg::RealServer01OdbcContext transaction{};
    rg::Real0BDAHost bridge{};
    void* fenceToken=nullptr;
    std::unique_ptr<diamond_v291::completion::RankUpCompletion> completion{};
};
struct Binding {
    void* context=nullptr;
    bool verifiedRestorableClone=false;
    bool originalDispatcherAndFrameIntegrityVerified=false;
    bool independentOwnerFenceAndSaveCompletionVerified=false;
    bool actualReplyAbiVerified=false;
    // Begin must establish an outer owner fence BEFORE the bridge's inner
    // lease; the two must not deadlock. It must provision request-local
    // transaction state, and prevent stale ordinary saves/disconnect
    // throughout pending completion. On false it must leave no held fence.
    bool (*begin)(void*,void* layer,const diamond_v19::ContextPrefix&,
                  Request&) noexcept=nullptr;
    // Finish receives ALL bridge outcomes. For pending/in-doubt it MUST
    // retain the fence in host-owned recovery state before returning;
    // never retry, release stale state, or send success on uncertainty.
    // It must not synchronously wait for an ACK on the dispatch thread.
    // Request storage is ephemeral. Move completion into host-owned pending
    // or recovery storage BEFORE returning; it owns the SQL commit record.
    // Its native port/fence must outlive that asynchronous completion.
    void (*finish)(void*,Request&,const gu::GameActionResult&) noexcept=nullptr;
};
inline const Binding* binding=nullptr; // immutable after pre-dispatch startup
inline std::atomic<std::uint64_t> entered{0},completed{0},pending{0},inDoubt{0};

inline bool Ready(const Binding& b) noexcept {
    return diamond_v291::completion::RankUpCompletion::CloneEnabled() &&
           b.verifiedRestorableClone &&
           b.originalDispatcherAndFrameIntegrityVerified &&
           b.independentOwnerFenceAndSaveCompletionVerified &&
           b.actualReplyAbiVerified && b.begin && b.finish;
}
inline int Handle(void* layer,diamond_v19::ContextPrefix* ctx) noexcept {
    const auto* b=binding;
    if(!b || !Ready(*b) || !ctx || !ctx->user || !ctx->frame)
        return 0; // no gameplay success implied; no original handler replay
    const auto candidate=gu::ParseC2s(ctx->frame,ctx->length);
    if(candidate.state!=gu::PacketState::Candidate)return 0;
    entered.fetch_add(1,std::memory_order_relaxed);
    Request request{};
    if(!b->begin(b->context,layer,*ctx,request))return 0;
    gu::GameActionResult result{};
    result.state=gu::GameActionState::MissingWorldAuthority;
    // The host must supply a request-local ODBC context; do not share
    // a mutable transaction context between WorldSvr sessions.
    const auto sameOwner=[&]() noexcept {
        if(!request.completion)return false;
        const auto& owner=request.completion->Owner();
        return owner.userNum==request.transaction.attestedUserNum &&
               owner.characterIdx==request.transaction.attestedCharacterIdx &&
               owner.sessionGeneration==request.transaction.attestedSessionGeneration &&
               request.transaction.attestedWorldUserCtx==ctx->user;
    };
    if(request.fenceToken && request.bridge.transaction==&request.transaction &&
       sameOwner() && request.completion->ReadyForCommit()){
        result=rg::Execute0BDARealServer01(
            ctx->user,ctx->frame,ctx->length,request.bridge,request.completion->Owner().intent);
    }
    if(result.state==gu::GameActionState::CommittedPendingSaveProof){
        const auto next=request.completion->AcceptCommitted(
            std::move(request.transaction.committedRankUp),
            std::move(request.transaction.odbcConnectionString));
        if(next!=diamond_v291::completion::Result::WaitingForAck)
            result.state=gu::GameActionState::InDoubtRecoveryRequired;
    }
    if(result.state==gu::GameActionState::InDoubtRecoveryRequired && request.completion)
        request.completion->MarkInDoubt(
            std::move(request.transaction.recoveryRankUp),
            std::move(request.transaction.odbcConnectionString));
    if(result.state==gu::GameActionState::CommittedPendingSaveProof)
        pending.fetch_add(1,std::memory_order_relaxed);
    if(result.state==gu::GameActionState::InDoubtRecoveryRequired)
        inDoubt.fetch_add(1,std::memory_order_relaxed);
    b->finish(b->context,request,result);
    completed.fetch_add(1,std::memory_order_relaxed);
    // CallProc receives normal processing completion, NOT a client S2C
    // status. A registered Diamond handler must be the sole map entry.
    return 0;
}
// Binding lifetime must cover all WorldSvr dispatch threads; no hot swap.
// The caller's startup barrier must remain held through the entire call.
inline diamond_v19::Status Register(const diamond_v19::Host& h,
                                    const Binding& b) noexcept {
    if(binding || !Ready(b) || !h.startupBeforeAnyDispatch)
        return diamond_v19::Status::Blocked;
    binding=&b;
    const auto result=diamond_v19::Register(h,&Handle);
    if(result!=diamond_v19::Status::Installed)binding=nullptr;
    return result;
}
} // namespace diamond_v20
