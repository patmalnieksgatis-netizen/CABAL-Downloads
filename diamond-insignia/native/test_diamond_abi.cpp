#include "diamond_abi.h"
#include "test_diamond_fixture.hpp"
#include <cassert>
#include <cstdint>
#include <iostream>
int main() {
  assert(cabal_diamond_abi_version()==CABAL_DIAMOND_ABI_VERSION);
  const auto cfg=fixture();
  cabal_diamond_engine* engine=nullptr;
  assert(cabal_diamond_engine_create(cfg.data(),cfg.size(),&engine)==0);
  assert(engine!=nullptr);
  cabal_diamond_state s{};
  s.abi_version=CABAL_DIAMOND_ABI_VERSION;
  s.server_authoritative=1;s.badge_grade=1;
  s.platinum_badge=1;s.platinum_maxed=1;
  s.revision=5;s.wexp=45000;s.verified_exchange_ticket_count=110;
  cabal_diamond_request rank{CABAL_DIAMOND_ABI_VERSION,CABAL_DIAMOND_RANK_UP,5,0};
  cabal_diamond_evaluation result{};
  assert(cabal_diamond_evaluate(engine,&s,&rank,&result)==0);
  assert(result.permitted==1 && result.requires_atomic_commit==1 &&
         result.new_revision==6 && result.new_badge_grade==2 &&
         result.new_wexp==15000 && result.new_ticket_count==10);
  assert(s.badge_grade==1 && s.wexp==45000); // Evaluation never persists.
  s.server_authoritative=0;
  assert(cabal_diamond_evaluate(engine,&s,&rank,&result)==0);
  assert(result.permitted==0 && result.requires_atomic_commit==0);
  s.server_authoritative=1;
  s.badge_grade=2;s.revision=6;s.wexp=15000;
  s.verified_exchange_ticket_count=10;s.free_points=50;
  s.active_category_mask=1u; // Category 11 is open from trusted server.
  const uint32_t open_id=159;s.server_open_mastery_ids=&open_id;s.server_open_count=1;
  cabal_diamond_request purchase{CABAL_DIAMOND_ABI_VERSION,CABAL_DIAMOND_MASTERY_LEVEL_UP,6,159};
  assert(cabal_diamond_evaluate(engine,&s,&purchase,&result)==0);
  assert(result.permitted==1 && result.requires_atomic_commit==1 &&
         result.new_free_points==45 && result.changed_mastery_id==159 &&
         result.changed_mastery_level==1 && result.new_revision==7);
  purchase.expected_revision=5;
  assert(cabal_diamond_evaluate(engine,&s,&purchase,&result)==0);
  assert(result.permitted==0 && result.requires_atomic_commit==0);
  purchase.expected_revision=6;
  s.server_open_count=2;
  assert(cabal_diamond_evaluate(engine,&s,&purchase,&result)!=0);
  s.server_open_count=1;
  s.abi_version=77;
  assert(cabal_diamond_evaluate(engine,&s,&purchase,&result)!=0);
  cabal_diamond_engine_destroy(engine);
  engine=nullptr;
  const auto invalid=fixture(true,false);
  assert(cabal_diamond_engine_create(invalid.data(),invalid.size(),&engine)!=0);
  assert(engine==nullptr);
  std::cout<<"DIAMOND_SHARED_LIBRARY_ABI_TESTS=PASS\n";
}
