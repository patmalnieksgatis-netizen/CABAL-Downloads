#include "Diamond0BDAAuthenticatedIngress.h"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <mutex>
#include <vector>

using namespace diamond_v291;
using namespace diamond_v291::gradeup0bda;
namespace {
void U32(std::uint8_t* p,std::uint32_t v) {
    for(unsigned i=0;i<4;++i)p[i]=static_cast<std::uint8_t>(v>>(8*i));
}
struct World {
    alignas(8) std::array<unsigned char,0xF0> userCtx{};
    alignas(8) std::array<unsigned char,0xA28> userData{};
    std::vector<std::uint8_t> slots=
        std::vector<std::uint8_t>(kWorldInventorySlots*kWorldInventoryEntryBytes,0);
    bool leaseHeld=false;
    int acquired=0,released=0,commits=0;
    std::uint32_t registeredUser=5005,registeredCharacter=24055;
    std::uint64_t sessionGeneration=77;
    bool connected=true,foreignData=false,failState=false;
    bool independentB0Proof=true;
    World() {
        void* p=userData.data();
        std::memcpy(userCtx.data()+0xE8,&p,sizeof(p));
        U32(userData.data()+0x890,5005);
        U32(userData.data()+0xA24,24055);
        auto* slot=slots.data()+5*kWorldInventoryEntryBytes;
        U32(slot+4,1);U32(slot+8,kTicket33554961);U32(slot+0x18,999);
    }
};
struct Authority final:WorldSessionAuthority {
    World& world;
    explicit Authority(World& w):world(w){}
    bool AcquireExclusive(const void* p,LockedWorldSession& out) noexcept override {
        if(p!=world.userCtx.data() || !world.connected || world.leaseHeld)
            return false;
        world.leaseHeld=true; ++world.acquired;
        out.userData=world.foreignData?world.userCtx.data():world.userData.data();
        out.registeredUserNum=world.registeredUser;
        out.registeredCharacterIdx=world.registeredCharacter;
        out.sessionGeneration=world.sessionGeneration;
        // labNonce=0 is legal in LIVE ingress: not a shadow DB account!
        out.labNonce=0;
        return true;
    }
    void ReleaseExclusive(const void* p) noexcept override {
        assert(p==world.userCtx.data() && world.leaseHeld);
        world.leaseHeld=false;++world.released;
    }
};
bool FillOwner(void* opaque,const AttestedLiveWorldUser& user,
               LockedGameOwner& out) noexcept {
    auto& world=*static_cast<World*>(opaque);
    if(!world.leaseHeld || world.failState)return false;
    out.worldUserCtx=user.worldUserCtx;
    out.registeredUserNum=user.userNum;
    out.registeredCharacterIdx=user.characterIdx;
    out.sessionGeneration=user.sessionGeneration;
    out.durableIntentId=998877;
    out.ownerExclusiveLockHeld=true;
    out.exactGradeUpCommandSemanticsVerified=true; // SYNTHETIC only
    out.actualGameDataAtomicBackendVerified=true; // SYNTHETIC only
    out.authoritativePlatinumStateVerified=true; // SYNTHETIC only
    out.authoritativeWexpVerified=true; // SYNTHETIC only
    out.authoritativeTotalTicketCountVerified=true; // SYNTHETIC only
    out.before.authoritative=true;
    out.before.platinum_badge=true;out.before.platinum_maxed=true;
    out.before.badge_grade=1;out.before.revision=5;
    out.before.wexp=35000;out.before.tickets=999;
    auto& inv=out.selectedInventory;
    inv.authenticatedWorldSession=user.worldUserCtx;
    inv.boundWorldSession=user.worldUserCtx;
    inv.trustedRecords=world.slots.data();
    inv.trustedRecordsBytes=world.slots.size();
    inv.acquiredUnderExclusiveOwnerLock=true;
    inv.recordsVerifiedFromWorldSession=true;
    inv.opcode0bdaSelectionMeansTicketSlotsVerified=true; // SYNTHETIC
    inv.selectionSemanticsBoundToGradeUpVerified=true; // SYNTHETIC
    inv.registeredUserNum=user.userNum;
    inv.registeredCharacterIdx=user.characterIdx;
    inv.trustedRevision=out.before.revision;
    inv.itemCatalog.fromTrustedWorldCatalog=true;
    inv.itemCatalog.catalogItemIndex=0x211u;
    inv.itemCatalog.catalogVariant=1;
    inv.itemCatalog.kindField38=0xB0;
    inv.itemCatalog.stackField3C=999;
    auto& proof=inv.itemCatalog.b0QuantityProof;
    proof.provenProfile=diamond_v291::inventory::B0CountProfile::
        PlainPositiveOptionNoFlags;
    proof.independentlyMatchedKnownQuantity=world.independentB0Proof; // SYNTHETIC
    proof.sameGameBuildAndMaterialKindVerified=true; // SYNTHETIC
    proof.optionLayoutVerified=true; // SYNTHETIC
    proof.extraOptionFlagsProvenAbsent=true; // SYNTHETIC
    return true;
}
AtomicCommitOutcome Commit(void* opaque,const void* ctx,
                            const AtomicGradeUpRequest& request) noexcept {
    auto& world=*static_cast<World*>(opaque);
    assert(ctx==world.userCtx.data());
    assert(world.leaseHeld); // lock MUST persist through the commit callback
    assert(request.userNum==5005 && request.characterIdx==24055);
    assert(request.sessionGeneration==77);
    assert(request.selectedTicketDebit.exactPlannedDebit==100);
    assert(request.intendedAfter.wexp==5000);
    assert(request.selectedTicketDebit.slots[0].expectedRemaining==899);
    ++world.commits;
    return {AtomicCommitState::CommittedNeedsIndependentSaveVerification,
            request.durableIntentId,request.intendedAfter.revision};
}
AuthenticatedIngressHost Host(World& w,WorldSessionAuthority& authority) {
    AuthenticatedIngressHost host{};
    host.authority=&authority;
    host.data.exactWorldSvrLayoutAndHashVerified=true; // SYNTHETIC
    host.data.readLockedState=&FillOwner;
    host.data.hostContext=&w;
    host.game.abiVersion=1;
    host.game.context=&w;
    host.game.commit=&Commit;
    auto& db=host.game.sql;
    db.userNum=5005;db.characterIdx=24055;
    db.exactServer01PrimaryKeysVerified=true; // SYNTHETIC
    db.verifiedCharacterBelongsToUser=true; // SYNTHETIC
    db.singleSerializableTransactionAcrossAllFourTables=true; // SYNTHETIC
    db.revisionAndIntentReplayProtectionEnforced=true; // SYNTHETIC
    db.lockedBeforeRowsComparedInsideThatTransaction=true; // SYNTHETIC
    db.transactionReceiptDurablyCommitted=true; // SYNTHETIC
    db.notChainingIndependentToolSetProcedures=true; // SYNTHETIC
    return host;
}
}
int main() {
    World world{};
    Authority authority(world);
    auto host=Host(world,authority);
    const std::array<std::uint8_t,14> packet={
        0xe2,0xb7,14,0,0,0,0,0,0xda,0x0b,1,0,5,0};
    auto platinum=packet;platinum[8]=0x10;
    auto result=ExecuteAuthenticated0BDA(world.userCtx.data(),platinum.data(),
                                         platinum.size(),host);
    assert(result.state==GameActionState::NotDiamondCommand);
    assert(world.acquired==0 && world.commits==0);

    world.connected=false;
    result=ExecuteAuthenticated0BDA(world.userCtx.data(),packet.data(),
                                    packet.size(),host);
    assert(result.state==GameActionState::MissingWorldAuthority);
    world.connected=true;
    world.foreignData=true;
    result=ExecuteAuthenticated0BDA(world.userCtx.data(),packet.data(),
                                    packet.size(),host);
    assert(result.state==GameActionState::MissingWorldAuthority);
    world.foreignData=false;
    world.registeredUser=9999;
    result=ExecuteAuthenticated0BDA(world.userCtx.data(),packet.data(),
                                    packet.size(),host);
    assert(result.state==GameActionState::MissingWorldAuthority);
    world.registeredUser=5005;
    world.registeredCharacter=30000;
    result=ExecuteAuthenticated0BDA(world.userCtx.data(),packet.data(),
                                    packet.size(),host);
    assert(result.state==GameActionState::MissingWorldAuthority);
    world.registeredCharacter=24055;
    world.sessionGeneration=0;
    result=ExecuteAuthenticated0BDA(world.userCtx.data(),packet.data(),
                                    packet.size(),host);
    assert(result.state==GameActionState::MissingWorldAuthority);
    world.sessionGeneration=77;
    world.failState=true;
    result=ExecuteAuthenticated0BDA(world.userCtx.data(),packet.data(),
                                    packet.size(),host);
    assert(result.state==GameActionState::MissingWorldAuthority);
    world.failState=false;
    auto wrongHost=host;
    wrongHost.data.exactWorldSvrLayoutAndHashVerified=false;
    result=ExecuteAuthenticated0BDA(world.userCtx.data(),packet.data(),
                                    packet.size(),wrongHost);
    assert(result.state==GameActionState::MissingWorldAuthority);
    wrongHost=host;
    wrongHost.game.sql.userNum=9000;
    result=ExecuteAuthenticated0BDA(world.userCtx.data(),packet.data(),
                                    packet.size(),wrongHost);
    assert(result.state==GameActionState::MissingRealCommitBackend);
    world.independentB0Proof=false;
    result=ExecuteAuthenticated0BDA(world.userCtx.data(),packet.data(),
                                    packet.size(),host);
    assert(result.state==GameActionState::InventoryNotVerified);
    assert(world.commits==0);
    world.independentB0Proof=true;
    result=ExecuteAuthenticated0BDA(world.userCtx.data(),packet.data(),
                                    packet.size(),host);
    assert(result.state==GameActionState::CommittedPendingSaveProof);
    assert(result.plannedTickets==100 && result.plannedWexp==30000);
    assert(!result.maySendClientSuccess);
    assert(world.commits==1);
    assert(!world.leaseHeld && world.acquired==world.released);
    std::cout<<"0BDA_V14_OWNER_ACCOUNT_CHARACTER_AND_GENERATION_ATTESTED=PASS\n"
             <<"0BDA_OWNER_LOCK_HELD_THROUGH_ATOMIC_CALLBACK=PASS\n"
             <<"0BDA_NO_LAB_NONCE_NEEDED_FOR_REAL_OWNER=PASS\n"
             <<"0BDA_REAL_B0_999_WITH_SYNTHETIC_PROOF=PASS\n"
             <<"0BDA_NO_REAL_SQL_OR_GAME_MUTATIONS=PASS\n";
}
