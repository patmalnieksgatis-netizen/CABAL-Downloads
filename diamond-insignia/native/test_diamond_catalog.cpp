#include "diamond_catalog.hpp"
#include "test_diamond_fixture.hpp"
#include <cassert>
#include <iostream>
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
