// Completion ordering/identity/recovery fixtures. SQL and native actions are
// explicitly substituted; this test is not a live WorldSvr integration test.
#include "DiamondNativeRankUpCompletion.h"
#include <cassert>
#include <iostream>
#include <utility>
#include <vector>
namespace c=diamond_v291::completion;
namespace rg=diamond_v291::real_gamedata;
static bool readback=true,changeSessionOnRead=false;
static int reads=0;
static std::vector<int> events;
struct Port final:c::NativePort {
    bool held=true,apply=true,reserve=true,publish=true,abi=true,send=true;
    unsigned outstanding=0,sends=0,releases=0;
    bool HeldSessionMatches(const c::Identity& id) noexcept override {
        return held && id.userNum==5005 && id.characterIdx==24055 &&
               id.sessionGeneration==77 && id.intent==998877;
    }
    bool ApplyCommitted(const rg::RankUpCommitRecord& r) noexcept override {
        assert(held && r.operation.afterWexp.used==30007);
        events.push_back(1);return apply;
    }
    bool ReserveSave(c::SaveReservation& r) noexcept override {
        assert(held);events.push_back(2);r={0x800,outstanding,100};return reserve;
    }
    bool PublishSave(const c::SaveReservation& r) noexcept override {
        assert(held && r.epoch==100);events.push_back(3);return publish;
    }
    bool ReplyAbiVerified() const noexcept override{return abi;}
    bool SendRankUpSuccess(const c::Identity&,const std::array<std::uint8_t,7>& b) noexcept override {
        assert(held && reads>0);
        assert((b==std::array<std::uint8_t,7>{0xe2,0xb7,7,0,0xda,0x0b,1}));
        events.push_back(5);++sends;return send;
    }
    void ReleaseAfterReconciliation(const c::Identity&) noexcept override {
        assert(held && sends==1);events.push_back(6);++releases;held=false;
    }
};
static Port* currentPort=nullptr;
namespace diamond_v291::real_gamedata {
bool VerifySavedRankUpServer01(const std::string& connection,
                              const RankUpCommitRecord& r) noexcept {
    assert(connection=="fixture-no-connection" && currentPort && currentPort->held);
    assert(r.operation.characterIdx==24055 && r.inventoryAfter.size()==30);
    ++reads;events.push_back(4);
    if(changeSessionOnRead)currentPort->held=false;
    return readback;
}
}
static c::Identity identity(){return {5005,24055,77,998877};}
static std::unique_ptr<rg::RankUpCommitRecord> record(){
    auto r=std::make_unique<rg::RankUpCommitRecord>();
    r->sessionGeneration=77;
    auto& o=r->operation;
    o.durableIntent=998877;o.userNum=5005;o.characterIdx=24055;
    o.expectedRevision=5;o.appliedRevision=6;o.command=1;o.newBadgeGrade=2;
    o.beforeWexp={35000,90000,7};o.afterWexp={5000,90000,30007};
    o.newTickets=899;r->inventoryBefore.resize(30);r->inventoryAfter.resize(30);
    return r;
}
static std::array<unsigned char,18> ack(){
    std::array<unsigned char,18> a{0xe2,0xb7,18,0,0,0,0,0,47,0};
    const std::uint32_t ch=24055,flags=0x800;
    for(int i=0;i<4;++i){a[10+i]=ch>>(8*i);a[14+i]=flags>>(8*i);}
    return a;
}
int main(){
    const auto packet=ack();
    {
        Port p;currentPort=&p;c::RankUpCompletion x(p,identity());
#ifndef DIAMOND_ENABLE_0BDA_CLONE_TRIAL
        assert(!x.ReadyForCommit());
        assert(x.AcceptCommitted(record(),"fixture-no-connection")==c::Result::RecoveryRequired);
        assert(events.empty() && p.held && p.releases==0 && p.sends==0);
        std::cout<<"NATIVE_COMPLETION_PRODUCTION_DISABLED=PASS\n";
        return 0;
#else
        assert(x.ReadyForCommit());
        assert(x.AcceptCommitted(record(),"fixture-no-connection")==c::Result::WaitingForAck);
        assert((events==std::vector<int>{1,2,3}) && reads==0 && p.sends==0);
        auto foreign=identity();foreign.sessionGeneration++;
        assert(x.OnSaveAck(foreign,packet.data(),18,101,1)==c::Result::IgnoredAck);
        assert(x.OnSaveAck(identity(),packet.data(),18,100,1)==c::Result::IgnoredAck);
        auto bad=packet;bad[10]++;
        assert(x.OnSaveAck(identity(),bad.data(),18,101,1)==c::Result::IgnoredAck);
        assert(reads==0 && p.sends==0);
        assert(x.OnSaveAck(identity(),packet.data(),18,101,1)==c::Result::Completed);
        assert((events==std::vector<int>{1,2,3,4,5,6}));
        assert(p.sends==1 && p.releases==1 && !p.held);
        assert(x.OnSaveAck(identity(),packet.data(),18,102,1)==c::Result::WrongPhase);
        assert(p.sends==1 && p.releases==1);
#endif
    }
    for(int failure=0;failure<10;++failure){
        events.clear();reads=0;readback=true;changeSessionOnRead=false;
        Port p;currentPort=&p;c::RankUpCompletion x(p,identity());
        auto r=record();
        if(failure==0)r->sessionGeneration++;
        if(failure==1)p.apply=false;
        if(failure==2)p.reserve=false;
        if(failure==3)p.outstanding=1;
        if(failure==4)p.publish=false;
        if(failure==5)readback=false;
        if(failure==6)changeSessionOnRead=true;
        if(failure==7)p.send=false;
        auto started=x.AcceptCommitted(std::move(r),"fixture-no-connection");
        c::Result result=started;
        if(started==c::Result::WaitingForAck){
            if(failure==8)p.abi=false;
            result=x.OnSaveAck(identity(),packet.data(),18,101,failure==9?2:1);
        }
        assert(result==(failure==8?c::Result::ReplyBlocked:c::Result::RecoveryRequired));
        assert(p.releases==0 && p.sends==(failure==7?1u:0u));
        // Failed/ambiguous send, timeout, bad readback or new session may not
        // be retried by delivering the same ACK again.
        assert(x.OnSaveAck(identity(),packet.data(),18,102,1)==c::Result::WrongPhase);
        assert(p.releases==0 && p.sends==(failure==7?1u:0u));
    }
    {
        Port p;currentPort=&p;c::RankUpCompletion x(p,identity());
        p.abi=false;assert(!x.ReadyForCommit());
        p.abi=true;p.held=false;assert(!x.ReadyForCommit());
        p.held=true;x.MarkInDoubt();assert(!x.ReadyForCommit());
        assert(x.AcceptCommitted(record(),"fixture-no-connection")==c::Result::WrongPhase);
        assert(p.sends==0 && p.releases==0);
    }
    std::cout<<"SQL_NATIVE_SAVE_RECONCILE_SINGLE_REPLY_ORDER=PASS\n"
             <<"SESSION_GENERATION_AND_AMBIGUOUS_SAVE_GATES=PASS\n"
             <<"UNCERTAIN_COMPLETION_RETAINS_FENCE=PASS\n"
             <<"REAL_NATIVE_PORT_AND_SQL_SUBSTITUTED=YES\n";
}
