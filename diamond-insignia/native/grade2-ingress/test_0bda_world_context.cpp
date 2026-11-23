#include "Diamond0BDAWorldContext.h"
#include <cassert>
#include <cstdint>
#include <iostream>
#include <map>
#include <vector>
using namespace diamond_v291::gradeup0bda;
namespace {
struct Store final: diamond::IAtomicWorldState {
    diamond::TrustedState state{};
    bool failSave=false;
    int calls=0;
    Store() {
        state.authoritative=true;state.platinum_badge=true;
        state.platinum_maxed=true;state.badge_grade=1;state.revision=21;
        state.wexp=40000;state.tickets=120;
    }
    diamond::OperationResult apply(const diamond::Session& session,
        const diamond::Command& command,const Decision& decide) override {
        ++calls;
        if(session.user_num!=9911 || session.session_nonce!=0xBBAA ||
           command.type!=diamond::CommandType::RankUp)
            return {diamond::OperationStatus::Unauthenticated,
                    diamond::Error::Untrusted,state.revision};
        const auto proposal=decide(state);
        if(proposal.result!=diamond::Error::Ok)
            return {diamond::OperationStatus::Rejected,proposal.result,state.revision};
        if(failSave)
            return {diamond::OperationStatus::StorageFailure,
                    diamond::Error::Untrusted,state.revision};
        state=proposal.after;
        return {diamond::OperationStatus::Applied,diamond::Error::Ok,state.revision};
    }
};
struct Host {
    const void* expectedSession=nullptr;
    unsigned attestCalls=0;
    bool reject=false;
    bool foreignBind=false;
};
bool Attest(void* raw,const void* session,std::uint32_t layer,
            const Candidate& packet,WorldProof& out) noexcept {
    auto& host=*static_cast<Host*>(raw);
    ++host.attestCalls;
    if(host.reject || layer!=123 || session!=host.expectedSession ||
       packet.count!=2 || packet.rawEntries[0]!=7 || packet.rawEntries[1]!=8)
        return false;
    out.authenticatedSession=true;
    out.grade2ServerCatalogVerified=true;
    out.gradeUpSemanticsVerified=true; // synthetic evidence, not real host
    out.entriesAuthoritativelyMatched=true;
    out.actualGameDataWexpBackendVerified=true; // fake in-memory Store only
    out.boundWorldSession=host.foreignBind?&host:session;
    out.userNum=9911;out.sessionNonce=0xBBAA;out.revision=21;
    out.expectedCount=2;out.serverEntries[0]=7;out.serverEntries[1]=8;
    return true;
}
} // namespace
int main() {
    Store store;
    const std::map<int,diamond::Mastery> specs{};
    diamond::DiamondCommandService service(store,specs);
    std::uint8_t wire[16]={0xE2,0xB7,0x10,0,0,0,0,0,0xDA,0x0B,2,0,7,0,8,0};
    int user=42;
    ProcessDataContext ctx{};
    ctx.pUserCtx=&user;ctx.cpPacket=wire;ctx.iLen=sizeof wire;
    Host host{};host.expectedSession=&user;
    HostAdapter adapter{kHostProofAdapterVersion,Attest,&host};
    auto dispatch=[&](std::size_t n,bool integrity,const HostAdapter& proof) {
        return Dispatch(&ctx,n,integrity,123,proof,service);
    };
    assert(dispatch(15,true,adapter).state==DispatchState::InvalidFrame);
    assert(dispatch(sizeof wire,false,adapter).state==DispatchState::InvalidFrame);
    const auto missing=Dispatch(nullptr,sizeof wire,true,123,adapter,service);
    assert(missing.state==DispatchState::InvalidFrame);
    assert(store.calls==0 && host.attestCalls==0);
    HostAdapter incomplete{};
    assert(dispatch(sizeof wire,true,incomplete).state==DispatchState::Disabled);
    assert(host.attestCalls==0);
    wire[8]=0x10;wire[9]=0x0B; // Platinum 0B10 remains ORIGINAL
    assert(dispatch(sizeof wire,true,adapter).state==DispatchState::Original);
    wire[8]=0x13; // Platinum slot-open cancel
    assert(dispatch(sizeof wire,true,adapter).state==DispatchState::Original);
    wire[8]=0xDD; // new slot-cancel candidate
    assert(dispatch(sizeof wire,true,adapter).state==DispatchState::Original);
    wire[8]=0xDA;wire[10]=0;
    assert(dispatch(sizeof wire,true,adapter).state==DispatchState::InvalidFrame);
    wire[10]=2;
    host.reject=true;
    assert(dispatch(sizeof wire,true,adapter).state==DispatchState::Disabled);
    host.reject=false;host.foreignBind=true;
    assert(dispatch(sizeof wire,true,adapter).state==DispatchState::Disabled);
    host.foreignBind=false;
    assert(store.calls==0);
#ifndef DIAMOND_ENABLE_0BDA_CLONE_TRIAL
    const auto candidate=dispatch(sizeof wire,true,adapter);
    assert(candidate.state==DispatchState::Disabled);
    assert(!candidate.maySendS2cSuccess && !candidate.hostStateWasChanged);
    assert(store.calls==0);
    std::cout<<"WORLDSVR_0BDA_PRODUCTION_DISABLED=PASS\n";
#else
    store.failSave=true;
    auto rejected=dispatch(sizeof wire,true,adapter);
    assert(rejected.state==DispatchState::CloneBackendRejected);
    assert(!rejected.maySendS2cSuccess);
    assert(store.state.tickets==120 && store.state.wexp==40000 &&
           store.state.badge_grade==1 && store.state.revision==21);
    store.failSave=false;
    auto applied=dispatch(sizeof wire,true,adapter);
    assert(applied.state==DispatchState::CloneBackendAppliedPendingSaveProof);
    assert(applied.hostStateWasChanged && !applied.maySendS2cSuccess);
    assert(store.state.tickets==20 && store.state.wexp==10000 &&
           store.state.badge_grade==2 && store.state.revision==22);
    auto replay=dispatch(sizeof wire,true,adapter);
    assert(replay.state==DispatchState::CloneBackendRejected);
    assert(!replay.maySendS2cSuccess);
    assert(store.state.tickets==20 && store.state.revision==22);
    std::cout<<"WORLDSVR_0BDA_SYNTHETIC_CLONE_RANKUP=PASS\n";
#endif
    // A large original command is not erroneously decoded as Diamond.
    std::vector<std::uint8_t> original(350,0);
    original[0]=0xE2;original[1]=0xB7;
    original[2]=0x5E;original[3]=0x01;
    original[8]=0x10;original[9]=0x0B;
    ctx.cpPacket=original.data();ctx.iLen=350;
    assert(dispatch(350,true,adapter).state==DispatchState::Original);
    assert(store.calls==
#ifdef DIAMOND_ENABLE_0BDA_CLONE_TRIAL
        3
#else
        0
#endif
    );
    std::cout<<"WORLDSVR_ABI_LAYOUT=PASS\n"
             <<"WORLDSVR_PLATINUM_PASSTHROUGH=PASS\n"
             <<"WORLDSVR_FOREIGN_SESSION_REJECTED=PASS\n"
             <<"NO_S2C_SUCCESS_WITHOUT_DURABLE_SAVE=PASS\n";
}
