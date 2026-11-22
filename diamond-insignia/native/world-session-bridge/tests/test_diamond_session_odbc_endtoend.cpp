// Full synthetic authenticated v14 session -> actual Diamond CommitGate ->
// actual clone-only ODBC adapter -> fake SQL transaction driver.
// No active game, production DB, or private staged SCP is ever accessed.
#include "DiamondWorldSessionBridge.h"
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <mutex>
#include <string>
#include <thread>
#include <vector>
namespace fakeodbc { extern int commits,rollbacks; void reset(); }
using namespace diamond_v291;
namespace {
struct World {
    alignas(8) std::array<unsigned char,0xF0> context{};
    alignas(8) std::array<unsigned char,0xA28> data{};
    std::mutex sessionMutex;
    bool connected=true;
    bool useWrongData=false;
    bool wrongCharacter=false;
    bool wrongAccount=false;
    std::uint64_t generation=19;
    std::uint32_t acquired=0,released=0;
    World(){
        void* ptr=data.data();
        std::memcpy(context.data()+0xE8,&ptr,sizeof(ptr));
        std::uint32_t user=900001,ch=13579;
        std::memcpy(data.data()+0x890,&user,sizeof(user));
        std::memcpy(data.data()+0xA24,&ch,sizeof(ch));
    }
};
struct Authority final:WorldSessionAuthority {
    World& w;
    explicit Authority(World& x):w(x){}
    bool AcquireExclusive(const void* p,LockedWorldSession& out) noexcept override {
        if(p!=w.context.data())return false;
        w.sessionMutex.lock();
        if(!w.connected){w.sessionMutex.unlock();return false;}
        ++w.acquired;
        out.userData=w.useWrongData?nullptr:w.data.data();
        out.registeredUserNum=w.wrongAccount?900002:900001;
        out.registeredCharacterIdx=w.wrongCharacter?11111:13579;
        out.sessionGeneration=w.generation;
        out.labNonce=123456789;
        return true;
    }
    void ReleaseExclusive(const void* p) noexcept override {
        assert(p==w.context.data());++w.released;
        w.sessionMutex.unlock();
    }
};
void check(bool ok,const char* msg) {
    if(!ok){std::cerr<<"DIAMOND_V14_ODBC_ENDTOEND_FAILED: "<<msg<<"\n";std::exit(2);}
}
}
int main(int argc,char** argv) {
    check(argc==2,"synthetic scp argument required");
    std::ifstream input(argv[1],std::ios::binary);
    check(static_cast<bool>(input),"synthetic scp absent");
    const std::string config((std::istreambuf_iterator<char>(input)),
                              std::istreambuf_iterator<char>());
    cabal_diamond_engine* engine=nullptr;
    check(cabal_diamond_engine_create(config.data(),config.size(),&engine)==0 &&
          engine!=nullptr,"unable to construct rules");
    World world;Authority auth(world);
    auto run=[&](Request request,const char* db="Database=Server01_DiamondLab") {
        return ExecuteAttestedDiamondLab(engine,auth,world.context.data(),request,db);
    };
    fakeodbc::reset();
    const Request rank{10,CABAL_DIAMOND_RANK_UP,0};
    world.connected=false;
    check(run(rank).status==Status::AuthFailure,"disconnected session");
    world.connected=true;
    world.generation=0;
    check(run(rank).status==Status::AuthFailure,"stale generation");
    world.generation=19;
    world.useWrongData=true;
    check(run(rank).status==Status::AuthFailure,"incorrect pData");
    world.useWrongData=false;
    world.wrongCharacter=true;
    check(run(rank).status==Status::AuthFailure,"forged character");
    world.wrongCharacter=false;
    world.wrongAccount=true;
    check(run(rank).status==Status::AuthFailure,"forged UserNum");
    world.wrongAccount=false;
    check(run(rank,"Database=Server01").status==Status::AuthFailure,
          "production DB guard");
    check(fakeodbc::commits==0 && world.acquired==world.released,
          "preflight unexpectedly committed or leaked lock");
    check(run(rank).status==Status::Applied,"rank up not durable");
    check(fakeodbc::commits==1 && world.acquired==world.released,
          "rank commit count or session unlock mismatch");
    check(run(rank).status==Status::Replayed,"rank receipt replay");
    check(fakeodbc::commits==1,"rank receipt charged twice");
    const Request firstMastery{11,CABAL_DIAMOND_MASTERY_LEVEL_UP,159};
    check(run(firstMastery).status==Status::Applied,"first Mastery purchase");
    check(run(firstMastery).status==Status::Replayed,"Mastery receipt replay");
    check(fakeodbc::commits==2,"Mastery double debit");
    const Request secondMastery{12,CABAL_DIAMOND_MASTERY_LEVEL_UP,159};
    std::atomic<int> applied{0},replayed{0},errors{0};
    std::vector<std::thread> threads;
    for(int i=0;i<8;++i)threads.emplace_back([&]{
        const auto result=run(secondMastery);
        if(result.status==Status::Applied)applied++;
        else if(result.status==Status::Replayed)replayed++;
        else errors++;
    });
    for(auto& thread:threads)thread.join();
    check(applied==1 && replayed==7 && errors==0,
          "concurrent requests not exactly once");
    check(fakeodbc::commits==3 && world.acquired==world.released,
          "final transaction or lock mismatch");
    cabal_diamond_engine_destroy(engine);
    std::cout<<"DIAMOND_V14_SESSION_TO_COMMIT_GATE_TO_ODBC=PASS\n"
             <<"REAL_V14_IDENTITY_READER=COMPILED_AND_EXERCISED\n"
             <<"CLONE_SHADOW_DB_GUARD=PASS\n"
             <<"EIGHT_CONCURRENT_RETRIES=ONE_APPLIED_SEVEN_REPLAYED\n"
             <<"DBAGENT_GAME_INVENTORY_MSSQL=NOT_TESTED\n";
}
