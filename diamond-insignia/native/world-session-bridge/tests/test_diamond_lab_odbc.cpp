// Runs the real clone-only ODBC transaction adapter with a fake ODBC driver.
// CI uses a synthetic Merit SCP; no DB credentials, game or MSSQL contacted.
#include "DiamondLabOdbcBackend.h"
#include <atomic>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <memory>
#include <thread>
#include <vector>
namespace fakeodbc { extern int commits,rollbacks;extern bool failReceiptOnce;void reset(); }
using namespace diamond_v291;
namespace {
struct TrustedSession {int user=900001,character=13579;std::int64_t nonce=123456789;};
TrustedSession session;
bool attest(const void* p, VerifiedSession& out,void*) noexcept {
 if(p!=&session)return false;
 out.userNum=session.user;out.characterIdx=session.character;out.shadowNonce=session.nonce;return true;
}
void check(bool pass,const char* message){if(!pass){std::cerr<<"FAIL "<<message<<'\n';std::exit(1);}}
Result perform(const cabal_diamond_engine* eng, Request req,const char* conn="Database=Server01_DiamondLab"){
 DiamondLabOdbcBackend backend(conn,attest,nullptr);
 return Execute(eng,backend,&session,req);
}
}
int main(int argc,char** argv){
 check(argc==2,"need synthetic scp path");
 std::ifstream file(argv[1],std::ios::binary);
 check(static_cast<bool>(file),"synthetic scp missing");
 std::string scp((std::istreambuf_iterator<char>(file)),std::istreambuf_iterator<char>());
 check(!scp.empty(),"synthetic config empty");
 cabal_diamond_engine* raw=nullptr;
 check(cabal_diamond_engine_create(scp.data(),scp.size(),&raw)==0 && raw,"engine create");
 std::unique_ptr<cabal_diamond_engine,decltype(&cabal_diamond_engine_destroy)> eng(raw,&cabal_diamond_engine_destroy);
 fakeodbc::reset();
 const Request rank{10,CABAL_DIAMOND_RANK_UP,0};
 check(perform(eng.get(),rank,"Database=Server01").status==Status::AuthFailure,"LIVE DATABASE GUARD");
 check(fakeodbc::commits==0,"wrong DB no commit");
 session.nonce=777;
 check(perform(eng.get(),rank).status==Status::AuthFailure,"wrong nonce no account access");
 session.nonce=123456789;
 TrustedSession fake{};
 { DiamondLabOdbcBackend db("Database=Server01_DiamondLab",attest,nullptr);
   check(Execute(eng.get(),db,&fake,rank).status==Status::AuthFailure,"forged session refused"); }
 check(perform(eng.get(),rank).status==Status::Applied,"rank-up commits");
 check(fakeodbc::commits==1,"rank one SQL commit");
 auto replay=perform(eng.get(),rank);
 check(replay.status==Status::Replayed && replay.evaluation.new_wexp==10000,"rank replay receipt");
 check(fakeodbc::commits==1,"replay no second SQL commit");
 check(perform(eng.get(),Request{10,CABAL_DIAMOND_MASTERY_LEVEL_UP,159}).status==Status::RevisionConflict,"different same-rev rejected");
 fakeodbc::failReceiptOnce=true;
 check(perform(eng.get(),Request{11,CABAL_DIAMOND_MASTERY_LEVEL_UP,159}).status==Status::BackendFailure,"receipt insert injection failed");
 check(fakeodbc::commits==1,"failed receipt did not commit resource debit");
 check(fakeodbc::rollbacks>0,"failed receipt triggered rollback");
 check(perform(eng.get(),Request{11,CABAL_DIAMOND_MASTERY_LEVEL_UP,159}).status==Status::Applied,"mastery after failed transaction");
 check(fakeodbc::commits==2,"mastery committed once");
 check(perform(eng.get(),Request{11,CABAL_DIAMOND_MASTERY_LEVEL_UP,159}).status==Status::Replayed,"mastery receipt replay");
 std::atomic<int> applied{0},replayed{0},failed{0};
 std::vector<std::thread> threads;
 const Request next{12,CABAL_DIAMOND_MASTERY_LEVEL_UP,159};
 for(int i=0;i<8;++i)threads.emplace_back([&]{
   auto r=perform(eng.get(),next);
   if(r.status==Status::Applied)applied++;
   else if(r.status==Status::Replayed)replayed++;
   else failed++;
 });
 for(auto& t:threads)t.join();
 check(applied==1 && replayed==7 && failed==0,"8 parallel requests one debit seven replays");
 check(fakeodbc::commits==3,"total three SQL commits");
 check(perform(eng.get(),Request{12,CABAL_DIAMOND_MASTERY_LEVEL_UP,160}).status==Status::RevisionConflict,"mastery conflict");
 check(perform(eng.get(),Request{13,CABAL_DIAMOND_MASTERY_LEVEL_UP,158}).status==Status::BadArgument,"not Diamond id");
 std::cout<<"DIAMOND_V291_ODBC_GATE_TEST=PASS\n"
          <<"SYNTHETIC_MSSQL_TRANSACTION=EXERCISED_VIA_FAKE_ODBC\n"
          <<"SAME_TRANSACTION_WALLET_MASTERY_RECEIPT=PASS\n"
          <<"COMMIT_FAILURE_ROLLS_BACK=PASS\n"
          <<"DB_NAME_SERVER01_GUARD=PASS\n"
          <<"CONCURRENT_8=ONE_APPLIED_SEVEN_REPLAYED\n"
          <<"REAL_ODBC_DRIVER_COMPILATION=SEPARATE\n"
          <<"ACTUAL_MSSQL_CONNECTION=NOT_TESTED\n"
          <<"LIVE_WORLDSVR=UNCHANGED\n";
}
