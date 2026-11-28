#include "DiamondWorldSaveBarrier.h"
#include <limits>

namespace diamond_v291 {
namespace {
std::uint16_t ReadU16(const unsigned char* p) noexcept {
    return static_cast<std::uint16_t>(p[0]) |
           static_cast<std::uint16_t>(p[1]) << 8;
}
std::uint32_t ReadU32(const unsigned char* p) noexcept {
    return static_cast<std::uint32_t>(ReadU16(p)) |
           static_cast<std::uint32_t>(ReadU16(p+2)) << 16;
}
bool SameLedger(const real_gamedata::WarExpLedger& a,
                const real_gamedata::WarExpLedger& b) noexcept {
    return a.current==b.current && a.earned==b.earned && a.used==b.used;
}
bool ValidAccounting(const Operation& op) noexcept {
    const auto& before=op.beforeWexp;
    if(before.current<0 || before.earned<0 || before.used<0) return false;
    if(op.command==1){
        const auto debit=real_gamedata::PlanWarExpDebit(before,30000);
        return debit.valid && SameLedger(debit.after,op.afterWexp);
    }
    // Command 2 buys a level with mastery points. It must not spend WExp;
    // Special Mastery activation is a separate, currently unbound operation.
    return op.command==2 && SameLedger(before,op.afterWexp);
}
}
Verdict DiamondWorldSaveBarrier::Begin(const Operation& op,
                                      bool sessionAttested,
                                      bool durableIntentVerified) noexcept {
    if(phase_ != Phase::Empty) return Verdict::IllegalPhase;
    if(!sessionAttested || !durableIntentVerified || !op.durableIntent ||
       !op.userNum || !op.characterIdx ||
       op.expectedRevision==std::numeric_limits<std::uint32_t>::max() ||
       op.appliedRevision != op.expectedRevision+1 ||
       op.newBadgeGrade!=2 || !ValidAccounting(op) ||
       (op.command!=1 && op.command!=2) ||
       (op.command==1 && (op.masteryId!=0 || op.newMasteryLevel!=0)) ||
       (op.command==2 && (op.masteryId<159 || op.masteryId>474 ||
                          op.newMasteryLevel<1 || op.newMasteryLevel>100)))
        return Verdict::Invalid;
    operation_=op;
    phase_=Phase::IntentDurable;
    return Verdict::Ok;
}
Verdict DiamondWorldSaveBarrier::MarkNativeMutationApplied(
                                         bool appliedUnderOwnerLock) noexcept {
    if(phase_!=Phase::IntentDurable) return Verdict::IllegalPhase;
    if(!appliedUnderOwnerLock){phase_=Phase::RecoveryRequired;return Verdict::NeedRecovery;}
    phase_=Phase::NativeMutationApplied;
    return Verdict::Ok;
}
Verdict DiamondWorldSaveBarrier::MarkSaveSent(std::uint32_t flags,
        std::uint64_t epoch,std::uint32_t outstandingBeforeSend) noexcept {
    if(phase_!=Phase::NativeMutationApplied) return Verdict::IllegalPhase;
    const bool missingInventory = operation_.command == 1 && (flags & kSaveInventory) == 0;
    if(!flags || !epoch || missingInventory){
        // A mutation has already been applied. Failure to establish a valid
        // save cannot be treated as a clean rejection or retried blindly.
        phase_=Phase::RecoveryRequired;
        return Verdict::NeedRecovery;
    }
    if(outstandingBeforeSend!=0){
        phase_=Phase::RecoveryRequired;
        return Verdict::AmbiguousSave;
    }
    packFlags_=flags;
    sendEpoch_=epoch;
    phase_=Phase::SaveSent;
    return Verdict::Ok;
}
Verdict DiamondWorldSaveBarrier::ObserveIpcResult47(const void* raw,
     std::size_t size,std::uint64_t receiveEpoch,
     std::uint32_t outstandingAtAck) noexcept {
    if(phase_==Phase::AckObserved || phase_==Phase::Reconciled) return Verdict::DuplicateAck;
    if(phase_!=Phase::SaveSent) return Verdict::IllegalPhase;
    if(!raw || size!=kIpcResultSize)return Verdict::Invalid;
    const auto* p=static_cast<const unsigned char*>(raw);
    if(ReadU16(p)!=kIpcMagic || ReadU16(p+2)!=kIpcResultSize ||
       ReadU16(p+8)!=kIpcResultUpdateChDat) return Verdict::Invalid;
    const auto ch=ReadU32(p+10);
    const auto flags=ReadU32(p+14);
    if(ch!=operation_.characterIdx)return Verdict::ForeignAck;
    if(receiveEpoch<=sendEpoch_)return Verdict::StaleAck;
    // A fresh ACK for a different save of this character contradicts the
    // exclusive reservation. Even a save omitting inventory can write WExp.
    if(flags!=packFlags_ || outstandingAtAck!=1){
        phase_=Phase::RecoveryRequired;
        return Verdict::AmbiguousSave;
    }
    phase_=Phase::AckObserved;
    return Verdict::Ok;
}
Verdict DiamondWorldSaveBarrier::Reconcile(const DurableSnapshot& s) noexcept {
    if(phase_!=Phase::AckObserved) return Verdict::IllegalPhase;
    if(!s.verifiedGameInventory || !s.verifiedGameWexp || !s.receiptCommitted ||
       s.durableIntent!=operation_.durableIntent ||
       s.userNum!=operation_.userNum || s.characterIdx!=operation_.characterIdx ||
       s.revision!=operation_.appliedRevision ||
       s.badgeGrade!=operation_.newBadgeGrade ||
       !SameLedger(s.wexp,operation_.afterWexp) ||
       s.tickets!=operation_.newTickets ||
       s.masteryId!=operation_.masteryId ||
       s.masteryLevel!=operation_.newMasteryLevel){
        phase_=Phase::RecoveryRequired;
        return Verdict::SnapshotMismatch;
    }
    phase_=Phase::Reconciled;
    return Verdict::Ok;
}
Verdict DiamondWorldSaveBarrier::MarkTimeout() noexcept {
    if(phase_!=Phase::IntentDurable && phase_!=Phase::NativeMutationApplied &&
       phase_!=Phase::SaveSent && phase_!=Phase::AckObserved)
        return Verdict::IllegalPhase;
    phase_=Phase::RecoveryRequired;
    return Verdict::NeedRecovery;
}
bool DiamondWorldSaveBarrier::MaySendSuccess() const noexcept {
    return phase_==Phase::Reconciled;
}
const char* WorldSavePhaseName(Phase p) noexcept {
    switch(p){
        case Phase::Empty:return "Empty";
        case Phase::IntentDurable:return "IntentDurable";
        case Phase::NativeMutationApplied:return "NativeMutationApplied";
        case Phase::SaveSent:return "SaveSent";
        case Phase::AckObserved:return "AckObserved";
        case Phase::Reconciled:return "Reconciled";
        case Phase::RecoveryRequired:return "RecoveryRequired";
    }
    return "Unknown";
}
const char* WorldSaveVerdictName(Verdict p) noexcept {
    switch(p){
        case Verdict::Ok:return "Ok";
        case Verdict::Invalid:return "Invalid";
        case Verdict::IllegalPhase:return "IllegalPhase";
        case Verdict::ForeignAck:return "ForeignAck";
        case Verdict::StaleAck:return "StaleAck";
        case Verdict::AmbiguousSave:return "AmbiguousSave";
        case Verdict::DuplicateAck:return "DuplicateAck";
        case Verdict::NeedRecovery:return "NeedRecovery";
        case Verdict::SnapshotMismatch:return "SnapshotMismatch";
    }
    return "Unknown";
}
} // namespace diamond_v291
