#include "Diamond0BDAGameplayAction.h"
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <vector>
using namespace diamond_v291::gradeup0bda;
namespace {
void Put32(std::uint8_t* p,std::uint32_t v) {
    for(unsigned n=0;n<4;++n)p[n]=static_cast<std::uint8_t>(v>>(8u*n));
}
void Ticket(std::vector<std::uint8_t>& records,std::uint16_t slot,
            std::uint32_t units) {
    auto* p=records.data()+slot*kWorldInventoryEntryBytes;
    Put32(p+4,1);
    Put32(p+8,kTicket33554961);
    Put32(p+0x18,units);
}
std::array<std::uint8_t,16> GradeUpFrame() {
    return {0xe2,0xb7,16,0,0,0,0,0,0xda,0x0b,2,0,5,0,8,0};
}
struct HostFixture {
    int calls=0;
    std::uint64_t lastIntent=0;
    std::uint32_t lastUser=0;
    std::uint32_t lastCharacter=0;
    std::uint32_t lastPlannedTickets=0;
    std::uint64_t lastWexpDelta=0;
    bool simulateFailure=false;
    bool simulateInDoubt=false;
    bool corruptReceipt=false;
};
AtomicCommitOutcome CommitOnlySynthetic(
    void* ptr,const void* userCtx,const AtomicGradeUpRequest& op) noexcept {
    auto& fake=*static_cast<HostFixture*>(ptr);
    assert(userCtx!=nullptr);
    ++fake.calls;
    fake.lastIntent=op.durableIntentId;
    fake.lastUser=op.userNum;
    fake.lastCharacter=op.characterIdx;
    fake.lastPlannedTickets=op.selectedTicketDebit.exactPlannedDebit;
    fake.lastWexpDelta=op.expectedBefore.wexp-op.intendedAfter.wexp;
    if(fake.simulateFailure)return {};
    if(fake.simulateInDoubt)
        return {AtomicCommitState::InDoubtRecoveryRequired,0,0};
    return {AtomicCommitState::CommittedNeedsIndependentSaveVerification,
            fake.corruptReceipt?op.durableIntentId+1:op.durableIntentId,
            op.intendedAfter.revision};
}
LockedGameOwner Owner(std::vector<std::uint8_t>& slots,const void* ctx) {
    LockedGameOwner owner{};
    owner.worldUserCtx=ctx;
    owner.registeredUserNum=5005;
    owner.registeredCharacterIdx=24055;
    owner.sessionGeneration=77;
    owner.durableIntentId=998877;
    owner.ownerExclusiveLockHeld=true;
    owner.exactGradeUpCommandSemanticsVerified=true; // synthetic test only
    owner.actualGameDataAtomicBackendVerified=true; // synthetic test only
    owner.authoritativePlatinumStateVerified=true; // synthetic test only
    owner.authoritativeWexpVerified=true; // synthetic test only
    owner.authoritativeTotalTicketCountVerified=true; // synthetic only
    owner.before.authoritative=true;
    owner.before.platinum_badge=true;
    owner.before.platinum_maxed=true;
    owner.before.badge_grade=1;
    owner.before.revision=5;
    owner.before.wexp=33000;
    owner.before.tickets=140;
    owner.selectedInventory.authenticatedWorldSession=ctx;
    owner.selectedInventory.boundWorldSession=ctx;
    owner.selectedInventory.trustedRecords=slots.data();
    owner.selectedInventory.trustedRecordsBytes=slots.size();
    owner.selectedInventory.acquiredUnderExclusiveOwnerLock=true;
    owner.selectedInventory.recordsVerifiedFromWorldSession=true;
    owner.selectedInventory.opcode0bdaSelectionMeansTicketSlotsVerified=true;
    owner.selectedInventory.selectionSemanticsBoundToGradeUpVerified=true;
    owner.selectedInventory.registeredUserNum=owner.registeredUserNum;
    owner.selectedInventory.registeredCharacterIdx=owner.registeredCharacterIdx;
    owner.selectedInventory.trustedRevision=owner.before.revision;
    owner.selectedInventory.itemCatalog.fromTrustedWorldCatalog=true;
    owner.selectedInventory.itemCatalog.catalogItemIndex=0x211;
    owner.selectedInventory.itemCatalog.catalogVariant=1;
    owner.selectedInventory.itemCatalog.kindField38=0xaf; // SYNTHETIC!
    owner.selectedInventory.itemCatalog.stackField3C=999;
    return owner;
}
}
int main() {
    std::vector<std::uint8_t> rows(
        kWorldInventorySlots*kWorldInventoryEntryBytes,0);
    Ticket(rows,5,60);Ticket(rows,8,80);
    const auto untouched=rows;
    int world=1,foreign=2;
    auto owner=Owner(rows,&world);
    const auto pkt=GradeUpFrame();
    HostFixture state{};
    GameHost host{1,&state,&CommitOnlySynthetic,{}};
    // SYNTHETIC capability flags: only exercise the binding gate. No real
    // transaction or GameData write occurs in this offline unit test!
    host.sql.characterIdx=owner.registeredCharacterIdx;
    host.sql.userNum=owner.registeredUserNum;
    host.sql.exactServer01PrimaryKeysVerified=true;
    host.sql.verifiedCharacterBelongsToUser=true;
    host.sql.singleSerializableTransactionAcrossAllFourTables=true;
    host.sql.revisionAndIntentReplayProtectionEnforced=true;
    host.sql.lockedBeforeRowsComparedInsideThatTransaction=true;
    host.sql.transactionReceiptDurablyCommitted=true;
    host.sql.notChainingIndependentToolSetProcedures=true;
    const auto ok=PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),owner,host);
    assert(ok.state==GameActionState::CommittedPendingSaveProof);
    assert(ok.inventory==SelectionVerdict::ExactDebitPlan);
    assert(ok.rule==diamond::Error::Ok);
    assert(ok.plannedTickets==100 && ok.plannedWexp==30000);
    assert(ok.proposedRevision==6);
    assert(!ok.maySendClientSuccess);
    assert(state.calls==1 && state.lastIntent==998877);
    assert(state.lastUser==5005 && state.lastCharacter==24055);
    assert(state.lastPlannedTickets==100 && state.lastWexpDelta==30000);
    assert(rows==untouched); // mock callback never edits any world state

    // Unsupported B0 metadata must not reach the commit callback.
    auto observedOwner=owner;
    observedOwner.selectedInventory.itemCatalog.kindField38=kObservedTicketKind38;
    observedOwner.selectedInventory.itemCatalog.stackField3C=1000; // Unsupported B0 limit.
    const auto unsafe=PrepareAndCommitRealGradeUp(
        pkt.data(),pkt.size(),observedOwner,host);
    assert(unsafe.state==GameActionState::InventoryNotVerified);
    assert(unsafe.inventory==SelectionVerdict::UnsupportedStackQuantityEncoding);
    assert(state.calls==1);
    // Original B0/999 numeric quantities reach the substituted backend.
    Ticket(rows,5,999);
    auto plainOwner=owner;
    plainOwner.before.tickets=999;
    plainOwner.selectedInventory.itemCatalog.kindField38=kObservedTicketKind38;
    plainOwner.selectedInventory.itemCatalog.stackField3C=kObservedTicketStack3C;
    const std::array<std::uint8_t,14> singleRequest={
        0xe2,0xb7,14,0,0,0,0,0,0xda,0x0b,1,0,5,0
    };
    HostFixture plainFixture{};
    auto plainHost=host;
    plainHost.context=&plainFixture;
    plainOwner.selectedInventory.itemCatalog.fromTrustedWorldCatalog=false;
    const auto blocked=PrepareAndCommitRealGradeUp(
        singleRequest.data(),singleRequest.size(),plainOwner,plainHost);
    assert(blocked.state==GameActionState::InventoryNotVerified);
    assert(plainFixture.calls==0);
    plainOwner.selectedInventory.itemCatalog.fromTrustedWorldCatalog=true;
    const auto plain=PrepareAndCommitRealGradeUp(
        singleRequest.data(),singleRequest.size(),plainOwner,plainHost);
    assert(plain.state==GameActionState::CommittedPendingSaveProof);
    assert(plain.inventory==SelectionVerdict::ExactDebitPlan);
    assert(plain.plannedTickets==100 && plain.plannedWexp==30000);
    assert(plainFixture.calls==1 && plainFixture.lastPlannedTickets==100);
    assert(!plain.maySendClientSuccess);
    Ticket(rows,5,60); // the real owner's WorldSvr is never touched
    assert(rows==untouched);
    // All failure paths must avoid the actual persistence callback.
    auto c=pkt;c[8]=0x10; // original 0B10 Platinum, never intercepted
    assert(PrepareAndCommitRealGradeUp(c.data(),c.size(),owner,host).state==
           GameActionState::NotDiamondCommand);
    assert(state.calls==1);
    c=pkt;c[2]=17;
    assert(PrepareAndCommitRealGradeUp(c.data(),c.size(),owner,host).state==
           GameActionState::InvalidPacket);
    auto unbound=owner;
    unbound.worldUserCtx=&foreign;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),unbound,host).state==
           GameActionState::MissingWorldAuthority);
    unbound=owner;unbound.ownerExclusiveLockHeld=false;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),unbound,host).state==
           GameActionState::MissingWorldAuthority);
    unbound=owner;unbound.exactGradeUpCommandSemanticsVerified=false;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),unbound,host).state==
           GameActionState::MissingWorldAuthority);
    unbound=owner;unbound.actualGameDataAtomicBackendVerified=false;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),unbound,host).state==
           GameActionState::MissingWorldAuthority);
    unbound=owner;unbound.selectedInventory.opcode0bdaSelectionMeansTicketSlotsVerified=false;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),unbound,host).state==
           GameActionState::InventoryNotVerified);
    unbound=owner;unbound.before.wexp=100;
    const auto lacking=PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),unbound,host);
    assert(lacking.state==GameActionState::RuleRejected &&
           lacking.rule==diamond::Error::MissingWExp);
    unbound=owner;unbound.before.tickets=99;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),unbound,host).state==
           GameActionState::InventoryNotVerified);
    c=pkt;c[14]=5; // repeated slot 5 instead of 8
    assert(PrepareAndCommitRealGradeUp(c.data(),c.size(),owner,host).state==
           GameActionState::InventoryNotVerified);
    assert(state.calls==1);
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),owner,{}).state==
           GameActionState::MissingRealCommitBackend);
    // The actual Server01 schema binds Inventory/WarExp on CharacterIdx
    // and Platinum on UserNum. Swapping either identity must fail closed.
    auto wrongDb=host;wrongDb.sql.userNum+=1;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),owner,wrongDb).state==
           GameActionState::MissingRealCommitBackend);
    wrongDb=host;wrongDb.sql.characterIdx+=1;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),owner,wrongDb).state==
           GameActionState::MissingRealCommitBackend);
    wrongDb=host;wrongDb.sql.verifiedCharacterBelongsToUser=false;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),owner,wrongDb).state==
           GameActionState::MissingRealCommitBackend);
    // Independent SQL writer procs cannot be chained and called "atomic".
    wrongDb=host;wrongDb.sql.notChainingIndependentToolSetProcedures=false;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),owner,wrongDb).state==
           GameActionState::MissingRealCommitBackend);
    wrongDb=host;wrongDb.sql.singleSerializableTransactionAcrossAllFourTables=false;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),owner,wrongDb).state==
           GameActionState::MissingRealCommitBackend);
    wrongDb=host;wrongDb.sql.revisionAndIntentReplayProtectionEnforced=false;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),owner,wrongDb).state==
           GameActionState::MissingRealCommitBackend);
    wrongDb=host;wrongDb.sql.lockedBeforeRowsComparedInsideThatTransaction=false;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),owner,wrongDb).state==
           GameActionState::MissingRealCommitBackend);
    wrongDb=host;wrongDb.sql.transactionReceiptDurablyCommitted=false;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),owner,wrongDb).state==
           GameActionState::MissingRealCommitBackend);
    wrongDb=host;wrongDb.sql.exactServer01PrimaryKeysVerified=false;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),owner,wrongDb).state==
           GameActionState::MissingRealCommitBackend);
    assert(state.calls==1);
    state.simulateFailure=true;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),owner,host).state==
           GameActionState::RolledBack);
    state.simulateFailure=false;
    state.simulateInDoubt=true;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),owner,host).state==
           GameActionState::InDoubtRecoveryRequired);
    state.simulateInDoubt=false;
    state.corruptReceipt=true;
    assert(PrepareAndCommitRealGradeUp(pkt.data(),pkt.size(),owner,host).state==
           GameActionState::InDoubtRecoveryRequired);
    assert(rows==untouched);
    std::cout<<"0BDA_B0_PLAIN_999_TO_899_SYNTHETIC_END_TO_END=PASS\n"
             <<"0BDA_SERVER01_REAL_PK_AND_SINGLE_SQL_TX_GATE=PASS\n"
             <<"0BDA_UNSUPPORTED_B0_LIMIT_COMMIT_BLOCKED=PASS\n"
             <<"0BDA_GAMEPLAY_ENTRY_ORIGINAL_PLATINUM_PASSTHROUGH=PASS\n"
             <<"0BDA_GAMEPLAY_RULES_SELECTED_TICKETS_AND_WEXP_IN_ONE_PATH=PASS\n"
             <<"0BDA_GAMEPLAY_FAIL_CLOSED_AND_NO_S2C_WITHOUT_DURABLE_SAVE=PASS\n"
             <<"REAL_GAMEDATA_BACKEND=NOT_CONNECTED\n";
}
