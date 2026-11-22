#include "diamond_rules.hpp"
#include <cassert>
#include <iostream>
using namespace diamond;
static TrustedState gold_to_diamond_candidate() {
  TrustedState s;
  s.authoritative=true;s.platinum_maxed=true;s.platinum_badge=true;
  s.badge_grade=1;s.revision=12;s.wexp=30000;s.tickets=100;
  return s;
}
int main() {
  auto s=gold_to_diamond_candidate();
  {auto u=s;u.authoritative=false;assert(rank_up(u,12).result==Error::Untrusted);}
  {auto u=s;u.platinum_maxed=false;assert(rank_up(u,12).result==Error::PlatinumNotMaxed);}
  {auto u=s;u.wexp=29999;assert(rank_up(u,12).result==Error::MissingWExp);}
  {auto u=s;u.tickets=99;assert(rank_up(u,12).result==Error::MissingTickets);}
  assert(rank_up(s,11).result==Error::Stale);
  auto r=rank_up(s,12);
  assert(r.result==Error::Ok && r.requires_atomic_commit);
  assert(r.after.badge_grade==2 && r.after.wexp==0 && r.after.tickets==0 && r.after.revision==13);
  assert(s.badge_grade==1 && s.wexp==30000); // Pure proposal, source untouched
  assert(rank_up(r.after,13).result==Error::AlreadyDiamond);
  std::map<int,Mastery> specs;
  Mastery m;m.id=159;m.category=11;m.max_level=2;m.level_cost={15,25};
  specs.emplace(159,m);
  auto d=r.after;d.free_points=100;d.active_categories={11};d.server_open_slots={159};
  {auto u=d;u.authoritative=false;assert(mastery_level_up(u,specs,159,13).result==Error::Untrusted);}
  {auto u=d;u.active_categories={11,12,13};assert(mastery_level_up(u,specs,159,13).result==Error::InvalidProgress);}
  {auto u=d;u.server_open_slots.clear();assert(mastery_level_up(u,specs,159,13).result==Error::SlotNotOpen);}
  {auto u=d;u.active_categories.clear();assert(mastery_level_up(u,specs,159,13).result==Error::LockedCategory);}
  {auto u=d;u.free_points=14;assert(mastery_level_up(u,specs,159,13).result==Error::InsufficientPoints);}
  {auto u=d;u.levels[159]=3;assert(mastery_level_up(u,specs,159,13).result==Error::InvalidProgress);}
  {auto c=specs;c.at(159).linked_id=160;assert(mastery_level_up(d,c,159,13).result==Error::LinkedSemanticsUnverified);}
  {auto c=specs;c.at(159).prerequisite_id=160;c.at(159).prerequisite_level=2;
   assert(mastery_level_up(d,c,159,13).result==Error::MissingPrerequisite);}
  assert(mastery_level_up(d,specs,159,12).result==Error::Stale);
  auto buy=mastery_level_up(d,specs,159,13);
  assert(buy.result==Error::Ok && buy.requires_atomic_commit);
  assert(buy.after.levels.at(159)==1 && buy.after.free_points==85 && buy.after.revision==14);
  assert(d.levels.empty() && d.free_points==100); // source is untouched
  auto buy2=mastery_level_up(buy.after,specs,159,14);
  assert(buy2.result==Error::Ok && buy2.after.levels.at(159)==2);
  assert(buy2.after.free_points==60);
  assert(mastery_level_up(buy2.after,specs,159,15).result==Error::MaxLevel);
  {auto u=d;u.revision=static_cast<uint32_t>(std::numeric_limits<int32_t>::max());
   assert(mastery_level_up(u,specs,159,u.revision).result==Error::Stale);}
  std::cout<<"DIAMOND_NATIVE_CORE_TESTS=PASS\n";
}
