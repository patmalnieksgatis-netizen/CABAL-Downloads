#include "diamond_catalog.hpp"
#include <cassert>
#include <iostream>
#include <sstream>
#include <stdexcept>
using namespace diamond;
static std::string fixture(bool drop_value=false,bool bad_upgrade=false) {
  std::ostringstream o;
  o<<"[MeritMastery_Base]\tMastery_Category\tBadge_Grade\tMastery_Type\tMastery_Index\tMax_Level\tPreMastery_Index\tPreMastery_Level\tLinkedMastery_Index\n";
  for(int i=1;i<=64;i++) o<<i-1<<"\t1\t0\t1\t"<<i<<"\t1\t0\t0\t0\n";
  for(int i=65;i<=158;i++) o<<i-1<<"\t2\t1\t1\t"<<i<<"\t1\t0\t0\t0\n";
  for(int i=159;i<=474;i++) {
    const int maxlevel=i<315?6:1;
    const int linked=i>=160&&i<=267?i-1:0;
    o<<i-1<<"\t"<<11+(i-159)%16<<"\t2\t1\t"<<i<<"\t"<<maxlevel
     <<"\t0\t0\t"<<linked<<"\n";
  }
  o<<"\n[MeritMastery_Value]\tMastery_Type\tMastery_Index\tMastery_Level\tReq_MeritPoint\tBase_ForceID\tBase_ForceValue\tBase_ValueType\tBonus_ForceID\tBonus_ForceValue\tBonus_ValueType\n";
  int row=0;
  for(int i=159;i<=474;i++) {
    for(int lvl=1;lvl<=(i<315?6:1);lvl++) {
      if(drop_value && i==159 && lvl==2)continue;
      o<<++row<<"\t1\t"<<i<<"\t"<<lvl<<"\t"<<lvl*5<<"\t180\t6\t1\t0\t0\t0\n";
    }
  }
  o<<"\n[UpGrade_Material]\tBadge_Grade\tWexp\tNeed_Item\tNeed_Count\n";
  o<<"0\t1\t20000\t33554961\t100\n";
  o<<"1\t2\t"<<(bad_upgrade?30001:30000)<<"\t33554961\t100\n";
  o<<"\n[SpecialMastery_Active]\tMastery_Index\tActive_Category\n";
  o<<"0\t83\t5\n1\t102\t6\n";
  o<<"2\t159\t11\n3\t175\t15\n4\t191\t19\n5\t207\t23\n";
  return o.str();
}
static void reject(const std::string& s) {
  std::istringstream input(s);
  bool failed=false;
  try { (void)read_native_catalog(input); }
  catch (const std::invalid_argument&) { failed=true; }
  assert(failed);
}
int main() {
  const auto test=fixture();
  std::istringstream input(test);
  const auto catalog=read_native_catalog(input);
  assert(catalog.diamond.size()==316);
  assert(catalog.imported_value_rows==1096);
  assert(catalog.activation_edges.size()==4);
  assert(catalog.diamond.at(159).max_level==6);
  assert(catalog.diamond.at(159).level_cost.size()==6);
  assert(catalog.diamond.at(159).level_cost.at(1)==10);
  assert(catalog.diamond.at(160).linked_id==159);
  assert(catalog.diamond.at(474).max_level==1);
  TrustedState state;
  state.authoritative=true;state.badge_grade=2;state.revision=1;
  state.free_points=30;state.active_categories.insert(11);
  state.server_open_slots.insert(159);
  auto res=mastery_level_up(state,catalog.diamond,159,1);
  assert(res.result==Error::Ok && res.after.free_points==25 &&
         res.after.levels.at(159)==1);
  // Refuse a malformed/incomplete private source instead of silently defaulting costs.
  reject(fixture(true,false));
  reject(fixture(false,true));
  std::string duplicate=test+"[MeritMastery_Base]\tx\n";
  reject(duplicate);
  std::cout<<"DIAMOND_SCP_CATALOG_TESTS=PASS\n";
}
