#include "DiamondGrade2Ingress.h"
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <map>
using namespace diamond_v291::grade2;
namespace {
struct FakeLockedStore final: diamond::IAtomicWorldState {
    diamond::TrustedState state{};
    bool injectCommitFailure=false;
    int calls=0;
    FakeLockedStore() {
        state.authoritative=true; state.platinum_maxed=true;
        state.platinum_badge=true; state.badge_grade=1; state.revision=8;
        state.wexp=40000; state.tickets=120;
    }
    diamond::OperationResult apply(
       const diamond::Session& session,
       const diamond::Command& request,
       const Decision& decide) override {
        ++calls;
        if(session.user_num!=900001 || session.session_nonce!=0xA5B6 ||
           request.type!=diamond::CommandType::RankUp)
            return {diamond::OperationStatus::Unauthenticated,
                    diamond::Error::Untrusted,state.revision};
        const auto proposal=decide(state); // only authoritative locked state
        if(proposal.result!=diamond::Error::Ok)
            return {diamond::OperationStatus::Rejected,
                    proposal.result,state.revision};
        if(injectCommitFailure)
            return {diamond::OperationStatus::StorageFailure,
                    diamond::Error::Untrusted,state.revision};
        state=proposal.after; // in-memory synthetic atomic commit; NOT GameData
        return {diamond::OperationStatus::Applied,
                diamond::Error::Ok,state.revision};
    }
};
void Put32(unsigned char* p,std::uint32_t v) {
    for(unsigned i=0;i<4;++i)p[i]=static_cast<unsigned char>(v>>(8*i));
}
void MakePacket(unsigned char* p,std::uint32_t selector) {
    const unsigned char hdr[10]={0xE2,0xB7,0x0E,0,0,0,0,0,0xDD,0x0B};
    for(unsigned i=0;i<10;++i)p[i]=hdr[i];
    Put32(p+10,selector);
}
Proof GoodProof(const void* session) {
    Proof p{};
    p.authenticatedSession=true;
    p.catalogGrade2Verified=true;
    p.selectorSemanticVerified=true;
    p.actualInventoryWexpBackendReady=true;
    p.boundWorldSession=session;
    p.authenticatedUserNum=900001;
    p.trustedSessionNonce=0xA5B6;
    p.trustedRevision=8;
    p.serverVerifiedSelector=7;
    return p;
}
} // namespace
int main() {
    FakeLockedStore store;
    const std::map<int,diamond::Mastery> specs{};
    diamond::DiamondCommandService rules(store,specs);
    unsigned char packet[14]{};
    MakePacket(packet,7);
    assert(ParseC2s(packet,sizeof packet).kind==PacketKind::Candidate);
    int stub=1;
    const Proof proof=GoodProof(&stub);

    // Protect legacy Platinum and any unrelated packet.
    packet[8]=0x10;packet[9]=0x0B;
    assert(ParseC2s(packet,sizeof packet).kind==PacketKind::Other);
    assert(ExecuteCandidate(packet,sizeof packet,proof,rules).route==Route::Original);
    assert(store.calls==0);
    MakePacket(packet,7);
    assert(ParseC2s(packet,10).kind==PacketKind::Invalid);
    packet[2]=0x0F;
    assert(ParseC2s(packet,sizeof packet).kind==PacketKind::Invalid);
    MakePacket(packet,0xFFFFFFFF);
    assert(ParseC2s(packet,sizeof packet).kind==PacketKind::Invalid);
    MakePacket(packet,7);

    // The client-chosen raw selector is NOT an authorization source.
    auto weak=proof;weak.serverVerifiedSelector=8;
    assert(ExecuteCandidate(packet,sizeof packet,weak,rules).route==Route::Disabled);
    weak=proof;weak.authenticatedSession=false;
    assert(ExecuteCandidate(packet,sizeof packet,weak,rules).route==Route::Disabled);
    weak=proof;weak.catalogGrade2Verified=false;
    assert(ExecuteCandidate(packet,sizeof packet,weak,rules).route==Route::Disabled);
    weak=proof;weak.selectorSemanticVerified=false;
    assert(ExecuteCandidate(packet,sizeof packet,weak,rules).route==Route::Disabled);
    weak=proof;weak.actualInventoryWexpBackendReady=false;
    assert(ExecuteCandidate(packet,sizeof packet,weak,rules).route==Route::Disabled);
    weak=proof;weak.boundWorldSession=nullptr;
    assert(ExecuteCandidate(packet,sizeof packet,weak,rules).route==Route::Disabled);
    assert(store.calls==0);

#ifndef DIAMOND_ENABLE_GRADE2_CLONE_TRIAL
    const auto passive=ExecuteCandidate(packet,sizeof packet,proof,rules);
    assert(passive.route==Route::Disabled);
    assert(!passive.maySendS2cSuccess && store.calls==0);
    std::cout<<"GRADE2_V291_DEFAULT_DISABLED=PASS\n";
#else
    // Synthetic, explicit clone test: real-game persistence is not implied.
    store.injectCommitFailure=true;
    const auto failure=ExecuteCandidate(packet,sizeof packet,proof,rules);
    assert(failure.route==Route::Rejected);
    assert(!failure.maySendS2cSuccess);
    assert(store.state.badge_grade==1 && store.state.tickets==120 &&
           store.state.wexp==40000 && store.state.revision==8);
    store.injectCommitFailure=false;
    const auto applied=ExecuteCandidate(packet,sizeof packet,proof,rules);
    assert(applied.route==Route::BackendAppliedPendingSaveProof);
    assert(applied.transaction.status==diamond::OperationStatus::Applied);
    assert(!applied.maySendS2cSuccess);
    assert(store.state.badge_grade==2 && store.state.tickets==20 &&
           store.state.wexp==10000 && store.state.revision==9);
    const auto replay=ExecuteCandidate(packet,sizeof packet,proof,rules);
    assert(replay.route==Route::Rejected);
    assert(!replay.maySendS2cSuccess);
    assert(store.state.revision==9 && store.state.tickets==20);
    std::cout<<"GRADE2_V291_CLONE_SYNTHETIC_ATOMIC_RULES=PASS\n"
             <<"GRADE2_V291_SAVE_RECONCILIATION_AND_S2C=NOT_IMPLEMENTED\n";
#endif
    std::cout<<"GRADE2_V291_CLIENT_SELECTOR_UNTRUSTED=PASS\n"
             <<"GRADE2_V291_NO_S2C_SUCCESS_EMITTED=PASS\n"
             <<"LIVE_WORLD_AND_SQL_UNCHANGED=YES\n";
}
