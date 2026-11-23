#include "Diamond0BDAGameplayAction.h"

namespace diamond_v291::gradeup0bda {
GameActionResult PrepareAndCommitRealGradeUp(
    const void* clientFrame,std::size_t verifiedFrameBytes,
    const LockedGameOwner& owner,const GameHost& host) noexcept {
    GameActionResult result{};
    const Candidate packet=ParseC2s(clientFrame,verifiedFrameBytes);
    if(packet.state==PacketState::Other) {
        result.state=GameActionState::NotDiamondCommand;
        return result; // caller must forward unmodified to original WorldSvr
    }
    if(packet.state!=PacketState::Candidate) return result;

    // An ELF SHA or session pointer by itself does not authenticate a
    // character. This entire proof must be prepared by a trusted WorldSvr
    // owner-lease provider while holding its *real* exclusive character lock.
    if(!owner.worldUserCtx || !owner.registeredUserNum ||
       !owner.registeredCharacterIdx || !owner.sessionGeneration ||
       !owner.durableIntentId || !owner.ownerExclusiveLockHeld ||
       !owner.exactGradeUpCommandSemanticsVerified ||
       !owner.actualGameDataAtomicBackendVerified ||
       !owner.authoritativePlatinumStateVerified ||
       !owner.authoritativeWexpVerified ||
       !owner.authoritativeTotalTicketCountVerified ||
       owner.before.revision==0 ||
       owner.selectedInventory.authenticatedWorldSession!=owner.worldUserCtx ||
       owner.selectedInventory.boundWorldSession!=owner.worldUserCtx ||
       owner.selectedInventory.registeredUserNum!=owner.registeredUserNum ||
       owner.selectedInventory.registeredCharacterIdx!=owner.registeredCharacterIdx ||
       owner.selectedInventory.trustedRevision!=owner.before.revision ||
       !owner.selectedInventory.acquiredUnderExclusiveOwnerLock) {
        result.state=GameActionState::MissingWorldAuthority;
        return result;
    }
    const TicketDebitPlan selected=PlanTicketDebit(packet,owner.selectedInventory);
    result.inventory=selected.status;
    if(selected.status!=SelectionVerdict::ExactDebitPlan ||
       selected.exactPlannedDebit!=diamond::kDiamondRankTickets ||
       selected.selectedUnits>owner.before.tickets) {
        result.state=GameActionState::InventoryNotVerified;
        return result;
    }
    result.plannedTickets=selected.exactPlannedDebit;
    const auto proposal=diamond::rank_up(owner.before,owner.before.revision);
    result.rule=proposal.result;
    if(proposal.result!=diamond::Error::Ok ||
       !proposal.requires_atomic_commit ||
       proposal.after.revision!=owner.before.revision+1u ||
       proposal.after.badge_grade!=2 ||
       proposal.after.wexp>owner.before.wexp ||
       owner.before.wexp-proposal.after.wexp!=diamond::kDiamondRankWExp ||
       proposal.after.tickets>owner.before.tickets ||
       owner.before.tickets-proposal.after.tickets!=diamond::kDiamondRankTickets) {
        result.state=GameActionState::RuleRejected;
        return result;
    }
    result.plannedWexp=diamond::kDiamondRankWExp;
    result.proposedRevision=proposal.after.revision;
    if(host.abiVersion!=1 || !host.commit) {
        result.state=GameActionState::MissingRealCommitBackend;
        return result;
    }
    AtomicGradeUpRequest operation{};
    operation.durableIntentId=owner.durableIntentId;
    operation.userNum=owner.registeredUserNum;
    operation.characterIdx=owner.registeredCharacterIdx;
    operation.sessionGeneration=owner.sessionGeneration;
    operation.expectedBefore=owner.before;
    operation.intendedAfter=proposal.after;
    operation.selectedTicketDebit=selected;
    // One call only. No implicit retry, no second original dispatch after
    // committing; failure with unknown persistence requires recovery instead.
    const auto commit=host.commit(host.context,owner.worldUserCtx,operation);
    if(commit.state==AtomicCommitState::InDoubtRecoveryRequired) {
        result.state=GameActionState::InDoubtRecoveryRequired;
        return result;
    }
    if(commit.state==AtomicCommitState::RolledBackOrRejected) {
        result.state=GameActionState::RolledBack;
        return result;
    }
    if(commit.recordedIntentId!=operation.durableIntentId ||
       commit.appliedRevision!=proposal.after.revision) {
        // Never trust a success callback whose receipt does not match this
        // locked user and durable transaction. Require reconciliation.
        result.state=GameActionState::InDoubtRecoveryRequired;
        return result;
    }
    // Even a committed GameData transaction must await genuine WorldSvr
    // cmd46/47 save confirmation, independently reloaded inventory + WExp,
    // a committed receipt and verified real 0BDA S2C response layout.
    result.state=GameActionState::CommittedPendingSaveProof;
    return result;
}
} // namespace diamond_v291::gradeup0bda
