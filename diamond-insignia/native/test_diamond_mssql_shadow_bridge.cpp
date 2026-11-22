#include "diamond_mssql_shadow_bridge.h"
#include "test_diamond_fixture.hpp"
#include <cassert>
#include <iostream>
int main() {
 const auto input=fixture();
 cabal_diamond_engine* engine=nullptr;
 assert(cabal_diamond_engine_create(input.data(),input.size(),&engine)==0);
 assert(engine!=nullptr);
 auto calls=cabal_diamond_mssql_shadow_callbacks();
 assert(calls.version==CABAL_DIAMOND_WORLD_BRIDGE_VERSION &&
        calls.begin_authenticated_locked && calls.load_trusted_state &&
        calls.commit_durable && calls.abort_transaction);
 cabal_diamond_shadow_session session{};
 session.tag=CABAL_DIAMOND_MSSQL_SHADOW_SESSION_TAG;
 session.user_num=900001;
 session.nonce=123456;
 cabal_diamond_mssql_shadow_config host{};
 host.abi_version=CABAL_DIAMOND_MSSQL_SHADOW_ABI;
 host.odbc_connection_string="DSN=NO_SUCH_DSN_DO_NOT_CONNECT";
 host.active_authenticated_session=&session;
 cabal_diamond_request request{CABAL_DIAMOND_ABI_VERSION,CABAL_DIAMOND_RANK_UP,1,0};
 cabal_diamond_world_result result{};
 // Critical: session/UID mismatch must fail BEFORE any ODBC connect attempt.
 int result_code=cabal_diamond_world_execute(engine,&session,900002,&request,
                                            &calls,&host,&result);
 assert(result_code==0 && result.status==CABAL_DIAMOND_WORLD_AUTH_FAILED &&
        result.evaluated.permitted==0);
 cabal_diamond_shadow_session injected{CABAL_DIAMOND_MSSQL_SHADOW_SESSION_TAG,900001,123456};
 result_code=cabal_diamond_world_execute(engine,&injected,900001,&request,
                                        &calls,&host,&result);
 assert(result_code==0 && result.status==CABAL_DIAMOND_WORLD_AUTH_FAILED &&
        result.evaluated.permitted==0);
 host.abi_version=77;
 result_code=cabal_diamond_world_execute(engine,&session,900001,&request,
                                        &calls,&host,&result);
 assert(result_code==0 && result.status==CABAL_DIAMOND_WORLD_AUTH_FAILED);
 cabal_diamond_engine_destroy(engine);
 std::cout<<"DIAMOND_MSSQL_ODBC_SHADOW_AUTH_GATES=PASS\n"
          <<"ODBC_DRIVER_CONNECT_ATTEMPTED=NO\n"
          <<"PRODUCTION_DB_ACCESS=NO\n";
}