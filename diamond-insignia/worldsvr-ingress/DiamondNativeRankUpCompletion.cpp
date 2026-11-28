#include "DiamondNativeRankUpCompletion.h"
#include <utility>
#include <cstring>

namespace diamond_v291::completion {
namespace {
bool SameSession(const Identity& a,const Identity& b) noexcept {
    return a.userNum==b.userNum && a.characterIdx==b.characterIdx &&
           a.sessionGeneration==b.sessionGeneration;
}
template<class T> T NativeField(const unsigned char* packet,std::size_t offset) noexcept {
    T value{};
    std::memcpy(&value,packet+offset,sizeof(value));
    return value;
}
Identity RecordOwner(const real_gamedata::RankUpCommitRecord& r) noexcept {
    return {r.operation.userNum,r.operation.characterIdx,
            r.sessionGeneration,r.operation.durableIntent};
}
}
bool RankUpCompletion::ReadyForCommit() noexcept {
    return CloneEnabled() && state_==State::Prepared && !committed_ &&
           identity_.userNum && identity_.characterIdx &&
           identity_.sessionGeneration && identity_.intent &&
           port_.HeldSessionMatches(identity_) && port_.ReplyAbiVerified();
}
Result RankUpCompletion::Recover() noexcept {
    state_=State::RecoveryRequired;
    return Result::RecoveryRequired; // deliberately no fence release
}
void RankUpCompletion::MarkInDoubt() noexcept {
    if(state_!=State::Completed)state_=State::RecoveryRequired;
}
void RankUpCompletion::MarkInDoubt(
        std::unique_ptr<real_gamedata::RankUpCommitRecord> uncertain,
        std::string connectionString) noexcept {
    if(state_==State::Completed)return;
    if(uncertain && !committed_)committed_=std::move(uncertain);
    if(!connectionString.empty())connectionString_=std::move(connectionString);
    // Retained before/after images are recovery evidence, not commit proof.
    MarkInDoubt();
}
Result RankUpCompletion::AcceptCommitted(
        std::unique_ptr<real_gamedata::RankUpCommitRecord> record,
        std::string connectionString) noexcept {
    // A lifecycle callback may interrupt the request while SQL is executing.
    // Keep its returned commit image, and never apply it to reset native data.
    if(state_==State::RecoveryRequired && !committed_) {
        MarkInDoubt(std::move(record),std::move(connectionString));
        return Result::RecoveryRequired;
    }
    if(state_!=State::Prepared)return Result::WrongPhase;
    // Retain the already committed evidence even on identity/ABI failure.
    committed_=std::move(record);
    connectionString_=std::move(connectionString);
    if(!CloneEnabled() || !committed_ || connectionString_.empty() ||
       !SameSession(identity_,RecordOwner(*committed_)) ||
       identity_.intent!=committed_->operation.durableIntent ||
       !port_.HeldSessionMatches(identity_) ||
       barrier_.Begin(committed_->operation,true,true)!=Verdict::Ok)
        return Recover();
    if(!port_.ApplyCommitted(*committed_) ||
       !port_.HeldSessionMatches(identity_) ||
       barrier_.MarkNativeMutationApplied(true)!=Verdict::Ok)
        return Recover();
    SaveReservation save{};
    if(!port_.ReserveSave(save) ||
       barrier_.MarkSaveSent(save.flags,save.epoch,save.outstandingBefore)!=Verdict::Ok)
        return Recover();
    reservation_=save;
    state_=State::WaitingForAck; // established BEFORE publish can deliver ACK
    if(!port_.PublishSave(save))return Recover();
    return Result::WaitingForAck;
}
Result RankUpCompletion::OnNativeSaveRouted(const Identity& owner,
        const void* packet,std::size_t bytes,std::uint64_t epoch,
        std::uint32_t outstandingBeforeRoute) noexcept {
    if(state_!=State::WaitingForAck)return Result::WrongPhase;
    if(owner.characterIdx!=identity_.characterIdx)return Result::IgnoredEvent;
    // 7DEB5E..7DEBB8 constructs a 14-byte IPC header and a fixed body
    // followed by variable records. The native stack buffer is 0x4D000.
    constexpr std::size_t header=14,minimum=0x5433,maximum=0x4d000;
    if(!committed_ || !packet || bytes<minimum || bytes>maximum)return Recover();
    const auto* raw=static_cast<const unsigned char*>(packet);
    if(NativeField<std::uint16_t>(raw,0)!=0xc8f3 ||
       NativeField<std::uint32_t>(raw,4)!=bytes ||
       NativeField<std::uint16_t>(raw,12)!=46 ||
       NativeField<std::uint32_t>(raw,header)!=identity_.characterIdx)
        return Recover();
    // 8BE6D8..8BE702 stores all three original WExp counters into the body.
    // A flags-only route notification cannot establish what will be saved.
    const auto& after=committed_->operation.afterWexp;
    if(NativeField<std::int64_t>(raw,header+0x99)!=after.current ||
       NativeField<std::int64_t>(raw,header+0xa1)!=after.earned ||
       NativeField<std::int64_t>(raw,header+0xa9)!=after.used)
        return Recover();
    const auto flags=NativeField<std::uint32_t>(raw,header+0x15ec);
    return OnSaveRouted(owner,flags,epoch,outstandingBeforeRoute);
}
Result RankUpCompletion::OnSaveRouted(const Identity& owner,std::uint32_t flags,
        std::uint64_t epoch,std::uint32_t outstandingBeforeRoute) noexcept {
    if(state_!=State::WaitingForAck)return Result::WrongPhase;
    if(owner.characterIdx!=identity_.characterIdx)return Result::IgnoredEvent;
    if(epoch<reservation_.epoch)return Result::IgnoredEvent;
    if(!SameSession(identity_,owner) || owner.intent!=identity_.intent ||
       !port_.HeldSessionMatches(identity_) || routeObserved_ ||
       epoch!=reservation_.epoch || flags!=reservation_.flags ||
       outstandingBeforeRoute!=0)
        return Recover();
    routeObserved_=true;
    return Result::SaveObserved;
}
Result RankUpCompletion::OnItcSaveAck(const Identity& owner,const void* packet,
        std::size_t bytes,std::uint64_t epoch,
        std::uint32_t outstandingAtAck) noexcept {
    if(state_!=State::WaitingForAck)return Result::WrongPhase;
    if(!packet || bytes!=kIpcResultSize)return Result::IgnoredAck;
    const auto* raw=static_cast<const unsigned char*>(packet);
    if(raw[8]!=0xf0 || raw[9]!=0x07)return Result::IgnoredAck;
    // The original WorldSvr copies all 18 bytes and rewrites only the opcode.
    // Leave the owner's queued frame untouched for its original handler.
    std::array<unsigned char,kIpcResultSize> ipc{};
    std::memcpy(ipc.data(),raw,ipc.size());
    ipc[8]=kIpcResultUpdateChDat;
    ipc[9]=0;
    return OnSaveAck(owner,ipc.data(),ipc.size(),epoch,outstandingAtAck);
}
Result RankUpCompletion::OnSaveAck(const Identity& owner,const void* packet,
        std::size_t bytes,std::uint64_t epoch,
        std::uint32_t outstandingAtAck) noexcept {
    if(state_!=State::WaitingForAck)return Result::WrongPhase;
    if(!SameSession(identity_,owner))return Result::IgnoredAck;
    if(!port_.HeldSessionMatches(identity_))return Recover();
    const auto ack=barrier_.ObserveIpcResult47(packet,bytes,epoch,outstandingAtAck);
    if(ack==Verdict::Invalid || ack==Verdict::ForeignAck ||
       ack==Verdict::StaleAck || ack==Verdict::DuplicateAck)
        return Result::IgnoredAck;
    if(ack!=Verdict::Ok || owner.intent!=identity_.intent || !routeObserved_)
        return Recover();
    // Actual ODBC readback, not a host-provided arbitrary snapshot/boolean.
    // Keep the native fence held while a fresh connection checks game rows.
    if(!real_gamedata::VerifySavedRankUpServer01(connectionString_,*committed_) ||
       !port_.HeldSessionMatches(identity_))return Recover();
    const auto& op=committed_->operation;
    DurableSnapshot saved{};
    saved.verifiedGameInventory=saved.verifiedGameWexp=saved.receiptCommitted=true;
    saved.durableIntent=op.durableIntent;saved.userNum=op.userNum;
    saved.characterIdx=op.characterIdx;saved.revision=op.appliedRevision;
    saved.badgeGrade=op.newBadgeGrade;saved.wexp=op.afterWexp;
    saved.tickets=op.newTickets;saved.masteryId=op.masteryId;
    saved.masteryLevel=op.newMasteryLevel;
    if(barrier_.Reconcile(saved)!=Verdict::Ok)return Recover();
    const auto reply=gradeup0bda::StageCandidateSuccess(
        barrier_,true,port_.ReplyAbiVerified());
    if(reply.result!=gradeup0bda::ReplyGateResult::CloneCandidateEncoded ||
       !reply.canSendToClient){
        state_=State::ReconciledReplyBlocked;
        return Result::ReplyBlocked; // host must recover/relogin; no release
    }
    // The seven-byte reader uses pending client state and has no intent ID.
    // Consume the send attempt BEFORE calling transport; a lost send must not
    // be retried and cause the client to debit its local selection twice.
    if(replyAttempted_)return Recover();
    replyAttempted_=true;
    if(!port_.SendRankUpSuccess(identity_,reply.bytes))return Recover();
    state_=State::Completed;
    port_.ReleaseAfterReconciliation(identity_);
    return Result::Completed;
}
} // namespace diamond_v291::completion
