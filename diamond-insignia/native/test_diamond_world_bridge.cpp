#include "diamond_world_bridge.h"
#include "test_diamond_fixture.hpp"
#include <cassert>
#include <cstdint>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

struct WorldSession {uint32_t user; uint64_t nonce;};
struct Store {
  std::mutex mutex;
  WorldSession session{42,0xaabbccdd};
  uint32_t badge=1,revision=7;
  uint64_t wexp=40000;
  uint32_t tickets=120;
  int32_t points=20,level159=0;
  bool platinum_maxed=true,authoritative=true,fail_commit=false;
  int commits=0,rollbacks=0,auth_denied=0;
  uint32_t open_slot=159;
};
struct LockedTransaction {
  Store* store;
  std::unique_lock<std::mutex> guard;
  explicit LockedTransaction(Store* s):store(s),guard(s->mutex){}
};
static int begin(void* ctx,const void* world_session,uint32_t user_num,void** out) {
  auto& s=*static_cast<Store*>(ctx);
  *out=nullptr;
  if (world_session!=&s.session || user_num!=s.session.user ||
      s.session.nonce==0) {++s.auth_denied;return -1;}
  *out=new LockedTransaction(&s);
  return 0;
}
static int load(void*,void* txp,cabal_diamond_state* state) {
  auto& s=*static_cast<LockedTransaction*>(txp)->store;
  *state={};
  state->abi_version=CABAL_DIAMOND_ABI_VERSION;
  state->server_authoritative=s.authoritative?1u:0u;
  state->badge_grade=s.badge;
  state->platinum_badge=1;
  state->platinum_maxed=s.platinum_maxed?1u:0u;
  state->revision=s.revision;
  state->wexp=s.wexp;
  state->verified_exchange_ticket_count=s.tickets;
  state->free_points=s.points;
  if (s.badge==2) {
    state->active_category_mask=1u;
    state->server_open_mastery_ids=&s.open_slot;
    state->server_open_count=1;
  }
  return 0;
}
static int commit(void*,void* txp,const cabal_diamond_request* request,
                  const cabal_diamond_evaluation* result) {
  auto* tx=static_cast<LockedTransaction*>(txp);
  auto& s=*tx->store;
  if (s.fail_commit || result->permitted!=1 ||
      !result->requires_atomic_commit ||
      request->expected_revision!=s.revision ||
      result->new_revision!=s.revision+1 ||
      result->new_ticket_count>s.tickets || result->new_wexp>s.wexp)
    return -1;
  // The test store mimics ONE atomic durable transaction. Production callback
  // MUST include actual item 33554961, WExp and SQL updates in same transaction.
  s.badge=result->new_badge_grade;
  s.wexp=result->new_wexp;
  s.tickets=result->new_ticket_count;
  s.points=result->new_free_points;
  s.revision=result->new_revision;
  if (result->changed_mastery_id==159)
    s.level159=result->changed_mastery_level;
  ++s.commits;
  delete tx;
  return 0;
}
static void abort_tx(void*,void* txp) {
  auto* tx=static_cast<LockedTransaction*>(txp);
  ++tx->store->rollbacks;
  delete tx;
}
int main() {
  const auto raw=fixture();
  cabal_diamond_engine* engine=nullptr;
  assert(cabal_diamond_engine_create(raw.data(),raw.size(),&engine)==0);
  Store s;
  cabal_diamond_world_callbacks callbacks{};
  callbacks.version=CABAL_DIAMOND_WORLD_BRIDGE_VERSION;
  callbacks.begin_authenticated_locked=begin;
  callbacks.load_trusted_state=load;
  callbacks.commit_durable=commit;
  callbacks.abort_transaction=abort_tx;
  assert(cabal_diamond_world_bridge_version()==1);
  cabal_diamond_request rank{CABAL_DIAMOND_ABI_VERSION,CABAL_DIAMOND_RANK_UP,7,0};
  cabal_diamond_world_result r{};
  assert(cabal_diamond_world_execute(engine,&s.session,999,&rank,&callbacks,&s,&r)==0);
  assert(r.status==CABAL_DIAMOND_WORLD_AUTH_FAILED && s.commits==0);
  s.fail_commit=true;
  assert(cabal_diamond_world_execute(engine,&s.session,42,&rank,&callbacks,&s,&r)==0);
  assert(r.status==CABAL_DIAMOND_WORLD_COMMIT_FAILED);
  assert(s.revision==7 && s.wexp==40000 && s.tickets==120 && s.commits==0);
  s.fail_commit=false;
  s.authoritative=false;
  assert(cabal_diamond_world_execute(engine,&s.session,42,&rank,&callbacks,&s,&r)==0);
  assert(r.status==CABAL_DIAMOND_WORLD_BAD_BACKEND);
  s.authoritative=true;
  assert(cabal_diamond_world_execute(engine,&s.session,42,&rank,&callbacks,&s,&r)==0);
  assert(r.status==CABAL_DIAMOND_WORLD_APPLIED && r.evaluated.permitted==1);
  assert(s.revision==8 && s.badge==2 && s.wexp==10000 && s.tickets==20);
  assert(s.commits==1);
  // Replay is rejected while holding same user lock.
  assert(cabal_diamond_world_execute(engine,&s.session,42,&rank,&callbacks,&s,&r)==0);
  assert(r.status==CABAL_DIAMOND_WORLD_REJECTED && s.commits==1);
  cabal_diamond_request buy{CABAL_DIAMOND_ABI_VERSION,
                            CABAL_DIAMOND_MASTERY_LEVEL_UP,8,159};
  assert(cabal_diamond_world_execute(engine,&s.session,42,&buy,&callbacks,&s,&r)==0);
  assert(r.status==CABAL_DIAMOND_WORLD_APPLIED);
  assert(s.revision==9 && s.level159==1 && s.points==15 && s.commits==2);
  // Two concurrent duplicate same-revision packets must yield at most one commit.
  buy.expected_revision=9;
  const int before=s.commits;
  std::vector<std::thread> threads;
  for (int i=0;i<4;i++) threads.emplace_back([&](){
    cabal_diamond_world_result local{};
    assert(cabal_diamond_world_execute(engine,&s.session,42,&buy,
                                       &callbacks,&s,&local)==0);
    assert(local.status==CABAL_DIAMOND_WORLD_APPLIED ||
           local.status==CABAL_DIAMOND_WORLD_REJECTED);
  });
  for (auto& t:threads)t.join();
  assert(s.commits==before+1 && s.revision==10 &&
         s.level159==2 && s.points==5);
  // The result is produced only after durable backend commit.
  assert(r.bridge_version==1 && s.rollbacks>=4);
  callbacks.version=77;
  assert(cabal_diamond_world_execute(engine,&s.session,42,&buy,&callbacks,&s,&r)!=0);
  cabal_diamond_engine_destroy(engine);
  std::cout<<"DIAMOND_AUTHENTICATED_C_WORLD_BRIDGE_TESTS=PASS\n";
}
