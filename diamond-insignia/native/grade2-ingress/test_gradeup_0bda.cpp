#include "DiamondGradeUp0BDA.h"
#include <cassert>
#include <cstdint>
#include <iostream>
#include <map>
using namespace diamond_v291::gradeup0bda;
namespace {
struct SyntheticLockedBackend final: diamond::IAtomicWorldState {
    diamond::TrustedState state{};
    bool failCommit=false;
    int calls=0;
    SyntheticLockedBackend() {
        state.authoritative=true;
        state.platinum_badge=true;
        state.platinum_maxed=true;
        state.badge_grade=1;
        state.revision=8;
        state.tickets=120;
        state.wexp=40000;
    }
    diamond::OperationResult apply(
       const diamond::Session& session,const diamond::Command& cmd,
       const Decision& decide) override {
        ++calls;
        if(session.user_num!=900001 || session.session_nonce!=0xA5B6 ||
           cmd.type!=diamond::CommandType::RankUp)
            return {diamond::OperationStatus::Unauthenticated,
                    diamond::Error::Untrusted,state.revision};
        const auto proposal=decide(state); // Synthetic owner-locked state
        if(proposal.result!=diamond::Error::Ok)
            return {diamond::OperationStatus::Rejected,proposal.result,
                    state.revision};
        if(failCommit)
            return {diamond::OperationStatus::StorageFailure,
                    diamond::Error::Untrusted,state.revision};
        state=proposal.after;
        return {diamond::OperationStatus::Applied,diamond::Error::Ok,
                state.revision};
    }
};
WorldProof Good(int* session) {
    WorldProof p{};
    p.authenticatedSession=true;
    p.grade2ServerCatalogVerified=true;
    p.gradeUpSemanticsVerified=true; // SYNTHETIC proof only, NOT live-attested
    p.entriesAuthoritativelyMatched=true;
    p.actualGameDataWexpBackendVerified=true; // SYNTHETIC fake backend
    p.boundWorldSession=session;
    p.userNum=900001;p.sessionNonce=0xA5B6;p.revision=8;
    p.expectedCount=2;
    p.serverEntries[0]=7;p.serverEntries[1]=8;
    return p;
}
} // namespace
int main() {
    std::uint8_t frame[16]={
        0xE2,0xB7,0x10,0,0,0,0,0,0xDA,0x0B,2,0,7,0,8,0
    };
    const auto candidate=ParseC2s(frame,sizeof frame);
    assert(candidate.state==PacketState::Candidate);
    assert(candidate.count==2);
    assert(candidate.rawEntries[0]==7 && candidate.rawEntries[1]==8);
    SyntheticLockedBackend backend;
    const std::map<int,diamond::Mastery> specs;
    diamond::DiamondCommandService service(backend,specs);
    int session=1;
    auto proof=Good(&session);
    // Existing 0B10 and unrelated 0BDD handlers must never be hijacked.
    frame[8]=0x10;frame[9]=0x0B;
    assert(ParseC2s(frame,sizeof frame).state==PacketState::Other);
    assert(ExecuteCandidate(frame,sizeof frame,proof,service).route==Route::Original);
    frame[8]=0xDD;
    assert(ParseC2s(frame,sizeof frame).state==PacketState::Other);
    frame[8]=0xDA;
    frame[2]=15;
    assert(ParseC2s(frame,sizeof frame).state==PacketState::Invalid);
    frame[2]=16;
    frame[10]=0;
    assert(ParseC2s(frame,sizeof frame).state==PacketState::Invalid);
    frame[10]=2;
    assert(ParseC2s(frame,14).state==PacketState::Invalid);
    assert(ParseC2s(nullptr,0).state==PacketState::Invalid);
    auto bad=proof;bad.serverEntries[1]=9;
    assert(ExecuteCandidate(frame,sizeof frame,bad,service).route==Route::Disabled);
    bad=proof;bad.authenticatedSession=false;
    assert(ExecuteCandidate(frame,sizeof frame,bad,service).route==Route::Disabled);
    bad=proof;bad.grade2ServerCatalogVerified=false;
    assert(ExecuteCandidate(frame,sizeof frame,bad,service).route==Route::Disabled);
    bad=proof;bad.gradeUpSemanticsVerified=false;
    assert(ExecuteCandidate(frame,sizeof frame,bad,service).route==Route::Disabled);
    bad=proof;bad.entriesAuthoritativelyMatched=false;
    assert(ExecuteCandidate(frame,sizeof frame,bad,service).route==Route::Disabled);
    bad=proof;bad.actualGameDataWexpBackendVerified=false;
    assert(ExecuteCandidate(frame,sizeof frame,bad,service).route==Route::Disabled);
    bad=proof;bad.boundWorldSession=nullptr;
    assert(ExecuteCandidate(frame,sizeof frame,bad,service).route==Route::Disabled);
    assert(backend.calls==0);
#ifndef DIAMOND_ENABLE_0BDA_CLONE_TRIAL
    auto result=ExecuteCandidate(frame,sizeof frame,proof,service);
    assert(result.route==Route::Disabled);
    assert(!result.maySendS2cSuccess);
    assert(backend.calls==0);
    std::cout<<"GRADE2_0BDA_PRODUCTION_ROUTE_DISABLED=PASS\n";
#else
    backend.failCommit=true;
    auto failed=ExecuteCandidate(frame,sizeof frame,proof,service);
    assert(failed.route==Route::Rejected && !failed.maySendS2cSuccess);
    assert(backend.state.tickets==120 && backend.state.wexp==40000 &&
           backend.state.badge_grade==1 && backend.state.revision==8);
    backend.failCommit=false;
    auto applied=ExecuteCandidate(frame,sizeof frame,proof,service);
    assert(applied.route==Route::CloneBackendAppliedPendingSaveProof);
    assert(!applied.maySendS2cSuccess);
    assert(backend.state.tickets==20 && backend.state.wexp==10000 &&
           backend.state.badge_grade==2 && backend.state.revision==9);
    // Re-use of trusted revision=8 is rejected; the original balance remains.
    auto replay=ExecuteCandidate(frame,sizeof frame,proof,service);
    assert(replay.route==Route::Rejected && !replay.maySendS2cSuccess);
    assert(backend.state.tickets==20 && backend.state.revision==9);
    std::cout<<"GRADE2_0BDA_SYNTHETIC_CLONE_TRIAL=PASS\n"
             <<"REAL_WORLDSVR_GAMEDATA_MSSQL_AND_S2C=NOT_INTEGRATED\n";
#endif
    std::cout<<"GRADE2_0BDA_CLIENT_LIST_NOT_AUTHORITY=PASS\n"
             <<"NO_UNVERIFIED_SUCCESS_REPLY=PASS\n"
             <<"LIVE_WORLD_AND_SQL_UNCHANGED=YES\n";
}
