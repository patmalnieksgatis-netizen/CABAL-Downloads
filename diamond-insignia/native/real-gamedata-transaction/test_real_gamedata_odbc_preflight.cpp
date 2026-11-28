#include "DiamondRealGameDataOdbc.h"
#include <cassert>
#include <cstdint>
#include <iostream>
#include <vector>

using namespace diamond_v291::real_gamedata;
using namespace diamond_v291::gradeup0bda;
int main(){
    AtomicGradeUpRequest cmd{};
    cmd.userNum=5005;cmd.characterIdx=24055;
    cmd.sessionGeneration=77;cmd.durableIntentId=998877;
    cmd.expectedBefore.authoritative=true;
    cmd.expectedBefore.wexp=35000;cmd.expectedBefore.tickets=999;
    cmd.expectedBefore.revision=5;
    cmd.intendedAfter.wexp=5000;cmd.intendedAfter.tickets=899;
    cmd.intendedAfter.revision=6;
    cmd.selectedTicketDebit.status=SelectionVerdict::ExactDebitPlan;
    cmd.selectedTicketDebit.selectedCount=1;
    cmd.selectedTicketDebit.exactPlannedDebit=100;
    cmd.selectedTicketDebit.selectedUnits=999;
    cmd.selectedTicketDebit.slots[0]={5,999,100,899,false};
    int fakeUser=1;
    assert(CommitRealGameDataServer01(nullptr,&fakeUser,cmd).state==
           AtomicCommitState::RolledBackOrRejected);
    RealServer01OdbcContext ctx{};
    ctx.attestedUserNum=5005;ctx.attestedCharacterIdx=24055;
    ctx.attestedSessionGeneration=77;
    ctx.attestedWorldUserCtx=&fakeUser;
    ctx.verifiedRestorableTestClone=false;
    ctx.driverConfiguredForExactServer01=false;
    ctx.ownerLockStillHeld=false;
    ctx.independentWarExpAccountingVerified=false;
    ctx.actualDbOwnerRankRowProvisioned=false;
    // This deliberately never opens ODBC or attempts SQL.
    assert(CommitRealGameDataServer01(&ctx,&fakeUser,cmd).state==
           AtomicCommitState::RolledBackOrRejected);
    ctx.verifiedRestorableTestClone=true;
    assert(CommitRealGameDataServer01(&ctx,&fakeUser,cmd).state==
           AtomicCommitState::RolledBackOrRejected);
    ctx.driverConfiguredForExactServer01=true;
    assert(CommitRealGameDataServer01(&ctx,&fakeUser,cmd).state==
           AtomicCommitState::RolledBackOrRejected);
    ctx.ownerLockStillHeld=true;
    ctx.independentWarExpAccountingVerified=true;
    ctx.actualDbOwnerRankRowProvisioned=true;
    assert(CommitRealGameDataServer01(&ctx,&fakeUser,cmd).state==
           AtomicCommitState::RolledBackOrRejected); // no inventory proof
    ctx.proof.userNum=5005;ctx.proof.characterIdx=24055;
    ctx.proof.authenticatedWorldOwnerLockHeld=true;
    ctx.proof.sameUserAndCharacterProvenFromServer=true;
    ctx.proof.worldSlotsMappedToPersistedRowsUnderOwnerLock=true;
    cmd.userNum=5006;
    assert(CommitRealGameDataServer01(&ctx,&fakeUser,cmd).state==
           AtomicCommitState::RolledBackOrRejected);
    cmd.userNum=5005;
    cmd.durableIntentId=0;
    assert(CommitRealGameDataServer01(&ctx,&fakeUser,cmd).state==
           AtomicCommitState::RolledBackOrRejected);
    cmd.durableIntentId=998877;
    ctx.attestedSessionGeneration=0;
    assert(CommitRealGameDataServer01(&ctx,&fakeUser,cmd).state==
           AtomicCommitState::RolledBackOrRejected);
    RankUpCommitRecord saved{};
    assert(!VerifySavedRankUpServer01("",saved));
    saved.sessionGeneration=77;
    auto& op=saved.operation;
    op.userNum=5005;op.characterIdx=24055;op.durableIntent=998877;
    op.expectedRevision=5;op.appliedRevision=6;op.command=1;op.newBadgeGrade=2;
    op.beforeWexp={35000,90000,7};op.afterWexp={5000,90000,30007};
    op.newTickets=899;saved.inventoryAfter.resize(30);
    // A valid-shaped record still cannot open a connection without host
    // configuration. No temporary/fixture row is treated as a saved receipt.
    assert(!VerifySavedRankUpServer01("",saved));
    // No direct SQL in this test: actual DB transactions require a real
    // restorable VM clone, correct SQL approval and live WorldSvr owner.
    std::cout<<"REAL_SERVER01_ODBC_HOST_PREFLIGHT_FAILS_CLOSED=PASS\n"
             <<"REAL_SQL_TRANSACTION_NOT_EXECUTED_IN_CI=YES\n";
}
