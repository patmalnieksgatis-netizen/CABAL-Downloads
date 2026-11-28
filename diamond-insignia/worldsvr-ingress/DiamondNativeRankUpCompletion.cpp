#include "DiamondNativeRankUpCompletion.h"
#include <utility>

namespace diamond_v291::completion {
namespace {
bool Same(const Identity& a,const Identity& b) noexcept {
    return a.userNum==b.userNum && a.characterIdx==b.characterIdx &&
           a.sessionGeneration==b.sessionGeneration && a.intent==b.intent;
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
    if(state_!=State::Prepared)return Result::WrongPhase;
    // Retain the already committed evidence even on identity/ABI failure.
    committed_=std::move(record);
    connectionString_=std::move(connectionString);
    if(!CloneEnabled() || !committed_ || connectionString_.empty() ||
       !Same(identity_,RecordOwner(*committed_)) ||
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
    state_=State::WaitingForAck; // established BEFORE publish can deliver ACK
    if(!port_.PublishSave(save))return Recover();
    return Result::WaitingForAck;
}
Result RankUpCompletion::OnSaveAck(const Identity& owner,const void* packet,
        std::size_t bytes,std::uint64_t epoch,
        std::uint32_t outstandingAtAck) noexcept {
    if(state_!=State::WaitingForAck)return Result::WrongPhase;
    if(!Same(identity_,owner))return Result::IgnoredAck;
    if(!port_.HeldSessionMatches(identity_))return Recover();
    const auto ack=barrier_.ObserveIpcResult47(packet,bytes,epoch,outstandingAtAck);
    if(ack==Verdict::Invalid || ack==Verdict::ForeignAck ||
       ack==Verdict::StaleAck || ack==Verdict::DuplicateAck)
        return Result::IgnoredAck;
    if(ack!=Verdict::Ok)return Recover();
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
