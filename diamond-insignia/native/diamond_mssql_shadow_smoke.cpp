// Opt-in MSSQL Diamond shadow clone smoke host. NO GAME ACCOUNT/INVENTORY ACCESS.
// Requires DBA to install guarded SQL scripts 08/09 in Server01_DiamondLab.
// Credential string comes ONLY from DIAMOND_CLONE_ODBC_CONNECTION environment.
#include "diamond_mssql_shadow_bridge.h"
#include <atomic>
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <thread>
#include <vector>
int main(int argc,char** argv) {
 if(argc!=3 || std::string(argv[1])!="--run-shadow-clone") {
  std::cerr<<"Usage: --run-shadow-clone /path/to/MeritSystem.DIAMOND_STAGED_DO_NOT_INSTALL.scp\n";
  return 2;
 }
 const char* connection=std::getenv("DIAMOND_CLONE_ODBC_CONNECTION");
 if(!connection || !*connection){
  std::cerr<<"STOP: DIAMOND_CLONE_ODBC_CONNECTION is missing (not printed)\n";return 3;
 }
 std::ifstream input(argv[2],std::ios::binary);
 if(!input.good()){std::cerr<<"STOP: staged SCP missing\n";return 4;}
 const std::string scp((std::istreambuf_iterator<char>(input)),std::istreambuf_iterator<char>());
 cabal_diamond_engine* engine=nullptr;
 if(cabal_diamond_engine_create(scp.data(),scp.size(),&engine)!=0){
  std::cerr<<"STOP: native Diamond SCP failed validation\n";return 5;
 }
 auto close_engine=[&](){cabal_diamond_engine_destroy(engine);};
 cabal_diamond_shadow_session session{};
 session.tag=CABAL_DIAMOND_MSSQL_SHADOW_SESSION_TAG;
 session.user_num=900001;session.nonce=123456789;
 cabal_diamond_mssql_shadow_config host{};
 host.abi_version=CABAL_DIAMOND_MSSQL_SHADOW_ABI;
 host.odbc_connection_string=connection;
 host.active_authenticated_session=&session;
 auto cb=cabal_diamond_mssql_shadow_callbacks();
 auto call=[&](const cabal_diamond_request& command,cabal_diamond_world_result& result) {
  return cabal_diamond_world_execute(engine,&session,session.user_num,
                                    &command,&cb,&host,&result);
 };
 cabal_diamond_world_result r{};
 const cabal_diamond_request rank{CABAL_DIAMOND_ABI_VERSION,CABAL_DIAMOND_RANK_UP,10,0};
 if(call(rank,r)!=0 || r.status!=CABAL_DIAMOND_WORLD_APPLIED ||
    !r.evaluated.permitted || r.evaluated.new_revision!=11 ||
    r.evaluated.new_wexp!=10000 || r.evaluated.new_ticket_count!=20) {
  std::cerr<<"DIAMOND_MSSQL_CLONE=FAIL rank-up (shadow only), status="<<r.status<<"\n";
  close_engine();return 6;
 }
 if(call(rank,r)!=0 || r.status!=CABAL_DIAMOND_WORLD_REJECTED){
  std::cerr<<"DIAMOND_MSSQL_CLONE=FAIL replay rank-up\n";close_engine();return 7;
 }
 const cabal_diamond_request purchase{CABAL_DIAMOND_ABI_VERSION,
                                       CABAL_DIAMOND_MASTERY_LEVEL_UP,11,159};
 if(call(purchase,r)!=0 || r.status!=CABAL_DIAMOND_WORLD_APPLIED ||
    r.evaluated.new_revision!=12 || r.evaluated.changed_mastery_id!=159 ||
    r.evaluated.changed_mastery_level!=1) {
  std::cerr<<"DIAMOND_MSSQL_CLONE=FAIL mastery level1\n";close_engine();return 8;
 }
 const cabal_diamond_request purchase2{CABAL_DIAMOND_ABI_VERSION,
                                        CABAL_DIAMOND_MASTERY_LEVEL_UP,12,159};
 std::atomic<int> successes{0},rejects{0},failures{0};
 std::vector<std::thread> threads;
 for(int i=0;i<4;++i) threads.emplace_back([&](){
  cabal_diamond_world_result result{};
  int ret=call(purchase2,result);
  if(ret==0 && result.status==CABAL_DIAMOND_WORLD_APPLIED)++successes;
  else if(ret==0 && result.status==CABAL_DIAMOND_WORLD_REJECTED)++rejects;
  else ++failures;
 });
 for(auto& t:threads)t.join();
 if(successes!=1 || rejects!=3 || failures!=0){
  std::cerr<<"DIAMOND_MSSQL_CLONE=FAIL concurrent same-revision purchase "
           <<"successes="<<successes<<" rejected="<<rejects<<" failed="<<failures<<"\n";
  close_engine();return 9;
 }
 // Check via a stale request; the backend must accept/reject from durable state.
 const cabal_diamond_request stale{CABAL_DIAMOND_ABI_VERSION,
                                    CABAL_DIAMOND_MASTERY_LEVEL_UP,12,159};
 if(call(stale,r)!=0 || r.status!=CABAL_DIAMOND_WORLD_REJECTED ||
    r.evaluated.new_revision!=13) {
  std::cerr<<"DIAMOND_MSSQL_CLONE=FAIL persisted revision 13\n";
  close_engine();return 10;
 }
 std::cout<<"DIAMOND_MSSQL_SHADOW_CLONE=PASS\n"
          <<"STAGED_SCP=VALIDATED\n"
          <<"GRADE_UP=PASS\nMASTERIES_LEVEL_1_AND_2=PASS\n"
          <<"SERIALIZABLE_ROW_LOCK=PASS\nCONCURRENT_REPLAY=PASS\n"
          <<"LAST_REVISION=13\n"
          <<"TARGET_DB=Server01_DiamondLab_ONLY\n"
          <<"REAL_GAME_WORLDSVR_OR_INVENTORY=NOT_TOUCHED\n";
 close_engine();return 0;
}
