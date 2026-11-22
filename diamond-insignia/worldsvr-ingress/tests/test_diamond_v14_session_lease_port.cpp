#include "../DiamondV14SessionLeasePort.h"
#include "../../native/test_diamond_fixture.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <iostream>
#include <mutex>
#include <thread>
#include <chrono>
#include <condition_variable>

using namespace diamond_v291;
using namespace DiamondBoundIngress;
struct Store {
    alignas(8) std::array<unsigned char,0xF0> userContext{};
    alignas(8) std::array<unsigned char,0xA28> userData{};
    std::mutex mutex;
    std::mutex gateMutex;
    std::condition_variable gateCV;
    bool pauseInCommit=false,commitEntered=false,releaseCommit=false;
    bool connected=true,permit=true,gradeTwo=true,selector=true,commitFails=false;
    bool swapData=false,wrongOwner=false;
    std::uint64_t generation=19;
    unsigned acquired=0,released=0,commits=0,aborts=0;
    std::uint32_t revision=11;
    int points=50,level=0;
    std::uint32_t openSlot=159;
    cabal_diamond_level_entry existing{159,0};
    Store() {
        void* data=userData.data();
        std::memcpy(userContext.data()+0xE8,&data,sizeof(data));
        const std::uint32_t uid=900001,ch=7002;
        std::memcpy(userData.data()+0x0890,&uid,sizeof(uid));
        std::memcpy(userData.data()+0x0A24,&ch,sizeof(ch));
    }
};
struct Registry:WorldSessionAuthority {
    Store& state;
    explicit Registry(Store& s):state(s){}
    bool AcquireExclusive(const void* user,LockedWorldSession& lease) noexcept override {
        if(user!=state.userContext.data()||!state.connected)return false;
        state.mutex.lock();++state.acquired;
        lease.userData=state.swapData?nullptr:state.userData.data();
        lease.registeredUserNum=state.wrongOwner?900002:900001;
        lease.registeredCharacterIdx=7002;
        lease.sessionGeneration=state.generation;
        lease.labNonce=123456789;
        return true;
    }
    void ReleaseExclusive(const void* user) noexcept override {
        assert(user==state.userContext.data());
        ++state.released;state.mutex.unlock();
    }
};
struct Catalog:MeritCatalogAuthority {
    Store& state;
    explicit Catalog(Store& s):state(s){}
    bool ReadUnderExclusiveLease(const LockedWorldSession& lease,
                                  const SessionProof& proof,
                                  CatalogSelection& selected) noexcept override {
        if(!state.permit || !proof.Verified() || lease.sessionGeneration==0)
            return false;
        selected.trustedRevision=state.revision;
        selected.serverMasteryId=159;
        selected.serverSecondDword=999;
        selected.isDiamondGrade=state.gradeTwo;
        selected.serverMeritSelectorIsDiamond=state.selector;
        return true;
    }
};
struct Tx {Store* host;};
int begin(void* opaque,const void* session,std::uint32_t user,void** tx) {
    auto& s=*static_cast<Store*>(opaque);
    if(!tx||session!=s.userContext.data()||user!=900001 ||
       s.acquired!=s.released+1)return -1;
    *tx=new Tx{&s};return 0;
}
int load(void*,void* p,cabal_diamond_state* out) {
    auto& s=*static_cast<Tx*>(p)->host;
    *out={};out->abi_version=1;out->server_authoritative=1;
    out->badge_grade=2;out->platinum_badge=1;out->platinum_maxed=1;
    out->revision=s.revision;out->free_points=s.points;
    out->active_category_mask=1;
    out->server_open_mastery_ids=&s.openSlot;out->server_open_count=1;
    if(s.level){s.existing.level=s.level;out->server_levels=&s.existing;out->server_level_count=1;}
    return 0;
}
int commit(void*,void* p,const cabal_diamond_request* cmd,
           const cabal_diamond_evaluation* e) {
    auto* tx=static_cast<Tx*>(p);auto& s=*tx->host;
    if(s.pauseInCommit) {
        std::unique_lock<std::mutex> gate(s.gateMutex);
        s.commitEntered=true;
        s.gateCV.notify_all();
        s.gateCV.wait(gate,[&]{return s.releaseCommit;});
    }
    if(s.commitFails||s.acquired!=s.released+1||!e->permitted||
       e->new_revision!=s.revision+1||cmd->expected_revision!=s.revision||
       e->changed_mastery_id!=159||e->changed_mastery_level!=s.level+1)
       return -1;
    s.revision=e->new_revision;s.points=e->new_free_points;
    s.level=e->changed_mastery_level;++s.commits;
    delete tx;return 0;
}
void abortTx(void*,void* p) {auto* tx=static_cast<Tx*>(p);++tx->host->aborts;delete tx;}
std::array<unsigned char,18> request(std::uint32_t id=159,std::uint32_t second=999) {
    std::array<unsigned char,18> p{};
    p[0]=0xE2;p[1]=0xB7;p[2]=18;p[8]=0xF3;p[9]=9;
    for(int i=0;i<4;i++){
      p[10+i]=static_cast<unsigned char>(id>>(8*i));
      p[14+i]=static_cast<unsigned char>(second>>(8*i));
    }
    return p;
}
int main() {
    Store state; Registry registry(state); Catalog catalog(state);
    DiamondV14SessionLeasePort port(registry,catalog);
    const std::string scp=fixture();
    cabal_diamond_engine* engine=nullptr;
    assert(cabal_diamond_engine_create(scp.data(),scp.size(),&engine)==0);
    const auto candidate=request();
    assert(Process(state.userContext.data(),candidate.data(),candidate.size())==DiamondBoundIngress::Result::Disabled);
    setenv("CABAL_DIAMOND_SHADOW_TRIAL","ISOLATED_SYNTHETIC_USER_900001_ONLY",1);
    Binding b{};b.engine=engine;
    b.acquire_exclusive=&DiamondV14SessionLeasePort::Acquire;
    b.release_exclusive=&DiamondV14SessionLeasePort::Release;
    b.authority_context=&port;b.backend_context=&state;
    b.callbacks.version=CABAL_DIAMOND_WORLD_BRIDGE_VERSION;
    b.callbacks.begin_authenticated_locked=begin;
    b.callbacks.load_trusted_state=load;b.callbacks.commit_durable=commit;
    b.callbacks.abort_transaction=abortTx;
    assert(InstallOnce(&b));
    const auto rejected=[&] {
        const unsigned before=state.commits;
        assert(Process(state.userContext.data(),candidate.data(),candidate.size())==
               DiamondBoundIngress::Result::AuthRefused);
        assert(state.acquired==state.released && state.commits==before);
    };
    state.connected=false;rejected();state.connected=true;
    state.generation=0;rejected();state.generation=19;
    state.swapData=true;rejected();state.swapData=false;
    // Trust must match the real +0xE8 user data pointer, not just plausible
    // UserNum bytes in an otherwise valid USERDATACONTEXT buffer.
    const void* wrongData=state.userContext.data();
    std::memcpy(state.userContext.data()+0xE8,&wrongData,sizeof(wrongData));
    rejected();
    void* actualData=state.userData.data();
    std::memcpy(state.userContext.data()+0xE8,&actualData,sizeof(actualData));
    state.wrongOwner=true;rejected();state.wrongOwner=false;
    // Tampering a character identity behind a valid account must be refused.
    const std::uint32_t otherCharacter=7003;
    std::memcpy(state.userData.data()+0x0A24,&otherCharacter,sizeof(otherCharacter));
    rejected();
    const std::uint32_t expectedCharacter=7002;
    std::memcpy(state.userData.data()+0x0A24,&expectedCharacter,sizeof(expectedCharacter));
    state.permit=false;rejected();state.permit=true;
    state.gradeTwo=false;rejected();state.gradeTwo=true;
    state.selector=false;rejected();state.selector=true;
    auto altered=request(159,1000);
    assert(Process(state.userContext.data(),altered.data(),altered.size())==DiamondBoundIngress::Result::AuthRefused);
    assert(state.acquired==state.released);
    altered=request(160,999);
    assert(Process(state.userContext.data(),altered.data(),altered.size())==DiamondBoundIngress::Result::AuthRefused);
    assert(state.acquired==state.released);
    // Real concurrent blocker test: a session disconnect/character switch
    // cannot acquire the registry mutex while a Diamond debit is in commit.
    state.pauseInCommit=true;
    DiamondBoundIngress::Result purchaseOutcome=DiamondBoundIngress::Result::BadEngine;
    std::thread buyer([&]{
        purchaseOutcome=Process(state.userContext.data(),
                                candidate.data(),candidate.size());
    });
    bool entered=false;
    {
        std::unique_lock<std::mutex> gate(state.gateMutex);
        entered=state.gateCV.wait_for(gate,std::chrono::seconds(4),
                                     [&]{return state.commitEntered;});
    }
    bool couldDisconnect=false;
    if(entered) {
        couldDisconnect=state.mutex.try_lock();
        if(couldDisconnect)state.mutex.unlock();
    }
    {
        std::lock_guard<std::mutex> gate(state.gateMutex);
        state.releaseCommit=true;
    }
    state.gateCV.notify_all();
    buyer.join();
    assert(entered && !couldDisconnect &&
           purchaseOutcome==DiamondBoundIngress::Result::ShadowApplied);
    state.pauseInCommit=false;
    assert(state.points==45 && state.level==1 && state.revision==12 &&
           state.commits==1 && state.acquired==state.released);
    state.commitFails=true;
    assert(Process(state.userContext.data(),candidate.data(),candidate.size())==DiamondBoundIngress::Result::ShadowRejected);
    assert(state.level==1 && state.commits==1 &&
           state.acquired==state.released && state.aborts>=1);
    state.commitFails=false;
    assert(Process(state.userContext.data(),candidate.data(),candidate.size())==DiamondBoundIngress::Result::ShadowApplied);
    assert(state.points==35 && state.level==2 && state.revision==13 &&
           state.commits==2 && state.acquired==state.released);
    unsetenv("CABAL_DIAMOND_SHADOW_TRIAL");
    assert(Process(state.userContext.data(),candidate.data(),candidate.size())==DiamondBoundIngress::Result::Disabled);
    cabal_diamond_engine_destroy(engine);
    std::cout<<"DIAMOND_V14_SESSION_POINTER_OWNER_AND_GENERATION=PASS\n"
             <<"AUTHORITY_LOCK_HELD_ACROSS_COMMIT=PASS\n"
             <<"CONCURRENT_DISCONNECT_BLOCKED_UNTIL_COMMIT=PASS\n"
             <<"MALFORMED_OR_UNATTESTED_C2S_NO_DEBIT=PASS\n"
             <<"REAL_WORLDSVR_REGISTRY=NOT_CONNECTED\n";
}
