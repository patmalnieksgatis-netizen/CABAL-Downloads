// Pure rules tests, using invented fixture mastery definitions.
#include "../native/diamond_rules.hpp"
#include <cassert>
#include <cstdio>
using namespace diamond;
int main() {
  TrustedState s{};
  s.authoritative=true; s.platinum_badge=true; s.platinum_maxed=true;
  s.revision=7; s.wexp=35000; s.tickets=123;
  auto rank=rank_up(s,7);
  assert(rank.result==Error::Ok && rank.requires_atomic_commit);
  assert(rank.after.badge_grade==2 && rank.after.wexp==5000 &&
         rank.after.tickets==23 && rank.after.revision==8);
  assert(s.badge_grade==1 && s.tickets==123 && s.wexp==35000);
  assert(rank_up(rank.after,7).result==Error::Stale);
  assert(rank_up(rank.after,8).result==Error::AlreadyDiamond);
  s=rank.after;
  s.active_categories.insert(11); s.server_open_slots={159,160};
  s.free_points=5;
  Mastery a{159,11,2,0,0,0,{2,3}};
  Mastery b{160,11,1,159,1,0,{1}};
  std::map<int,Mastery> specs{{159,a},{160,b}};
  assert(mastery_level_up(s,specs,160,8).result==Error::MissingPrerequisite);
  auto up=mastery_level_up(s,specs,159,8);
  assert(up.result==Error::Ok && up.requires_atomic_commit &&
         up.after.levels.at(159)==1 && up.after.free_points==3 &&
         up.after.revision==9 && up.after.wexp==s.wexp &&
         up.after.tickets==s.tickets);
  assert(s.levels.empty() && s.free_points==5);
  assert(mastery_level_up(up.after,specs,160,8).result==Error::Stale);
  auto next=mastery_level_up(up.after,specs,160,9);
  assert(next.result==Error::Ok && next.after.free_points==2);
  assert(mastery_level_up(next.after,specs,159,10).result==Error::InsufficientPoints);
  assert(mastery_level_up(next.after,specs,160,10).result==Error::MaxLevel);
  auto invalid=specs; invalid[159].prerequisite_level=1;
  assert(mastery_level_up(s,invalid,159,8).result==Error::InvalidConfig);
  invalid=specs; invalid[160].prerequisite_level=0;
  assert(mastery_level_up(s,invalid,160,8).result==Error::InvalidConfig);
  invalid=specs; invalid[160].prerequisite_level=3;
  assert(mastery_level_up(s,invalid,160,8).result==Error::InvalidConfig);
  invalid=specs; invalid[159].prerequisite_id=160; invalid[159].prerequisite_level=1;
  assert(mastery_level_up(s,invalid,159,8).result==Error::InvalidConfig);
  invalid=specs; invalid[159].level_cost[1]=-1;
  assert(mastery_level_up(s,invalid,159,8).result==Error::InvalidConfig);
  invalid=specs; invalid[159].linked_id=160;
  assert(mastery_level_up(s,invalid,159,8).result==Error::LinkedSemanticsUnverified);
  assert(s.free_points==5 && s.levels.empty());
  std::puts("DIAMOND_V32_RULES=PASS");
}
