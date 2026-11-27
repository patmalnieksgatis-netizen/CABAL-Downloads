#include "diamond_catalog.hpp"
#include "test_diamond_fixture.hpp"
#include <cassert>
#include <iostream>
#include <fstream>
#include <sstream>
#include <stdexcept>
using namespace diamond;
static void reject(const std::string& s) {
  std::istringstream input(s);
  bool failed=false;
  try { (void)read_native_catalog(input); }
  catch (const std::invalid_argument&) { failed=true; }
  assert(failed);
}
int main(int argc,char** argv) {
  assert(argc==1 || argc==2);
  const auto test=fixture();
  std::istringstream input(test);
  const auto catalog=read_native_catalog(input);
  assert(catalog.diamond.size()==316);
  assert(catalog.imported_value_rows==1096);
  assert(catalog.activation_edges.size()==4);
  assert(catalog.mastery_types.size()==316);
  assert(catalog.levels.size()==1096);
  const auto& force=catalog.levels.at({159,2});
  assert(force.point_cost==10 && force.base.id==180 &&
         force.base.value==6 && force.base.value_type==1);
  assert(force.bonus.id==0 && force.bonus.value==0 && force.bonus.value_type==0);
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
  // Malformed force metadata used to be silently discarded by this reader.
  auto bad_force=test;
  const std::string old_force="\t180\t6\t1\t0\t0\t0\n";
  const auto force_at=bad_force.find(old_force);
  assert(force_at!=std::string::npos);
  bad_force.replace(force_at,old_force.size(),"\t180\t6\t3\t0\t0\t0\n");
  reject(bad_force);
  assert(!has_complete_slot_catalog(catalog));
  auto partial_slots=test+"[SlotOpen_Time]\tCategory\tOpened_Slot\tNeed_Time\n0\t11\t0\t900\n";
  reject(partial_slots);
  auto partial_special=test+"[SpecialMastery_Value]\tSpecialMastery_Index\tGrade\tForce_ID\tForce_Value\tForce_ValueType\n0\t34\t1\t1\t100\t1\n";
  reject(partial_special);
  if(argc==2) {
    std::ifstream real_input(argv[1]);
    assert(real_input.good());
    const auto real=read_native_catalog(real_input);
    assert(has_complete_slot_catalog(real));
    assert(real.slot_openings.at({26,19}).seconds==31536000);
    assert(real.slot_openings.at({26,19}).materials[0].count==50);
    for(const auto& pair:real.levels) {
      const auto& key=pair.first;const auto& d=pair.second;
      std::cout<<"LEVEL\t"<<key.first<<'\t'<<key.second<<'\t'<<d.mastery_type<<'\t'
       <<d.point_cost<<'\t'<<d.base.id<<'\t'<<d.base.value<<'\t'<<d.base.value_type<<'\t'
       <<d.bonus.id<<'\t'<<d.bonus.value<<'\t'<<d.bonus.value_type<<'\n';
    }
    std::cout<<"REAL_DONOR_NATIVE_CATALOG=PASS; MASTERIES=316; LEVELS=1096; SLOTS=308; SPECIAL_EFFECTS=100\n";
  }
  std::cout<<"DIAMOND_SCP_CATALOG_TESTS=PASS\n";
}
