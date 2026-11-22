#include "diamond_merit_world_entry.h"
#include <cassert>
#include <cstdint>
#include <iostream>

int main() {
  std::uint8_t bytes[18]={0xE2,0xB7,18,0,0,0,0,0,0xF3,0x09,
                           159,0,0,0,1,0,0,0};
  cabal_diamond_merit_server_proof proof{
    CABAL_DIAMOND_MERIT_PROOF_VERSION,1,1,1,1,1
  };
  cabal_diamond_world_result world{};
  cabal_merit_route_result route=CABAL_MERIT_ROUTE_INVALID;
  // Production mode MUST stay classification-only. No engine, backend,
  // or authenticated WorldSvr hook exists in this compilation.
  int session=33;
  const auto rc=cabal_diamond_merit_verified_shadow_route(
      nullptr,bytes,sizeof(bytes),&session,7,3,&proof,
      nullptr,nullptr,1,&world,&route);
  assert(rc==0 && route==CABAL_MERIT_ROUTE_DISABLED);
  assert(world.status==0);
  assert(world.evaluated.permitted==0);
  assert(world.evaluated.requires_atomic_commit==0);
  route=CABAL_MERIT_ROUTE_INVALID;
  assert(cabal_diamond_merit_shadow_route(
      nullptr,bytes,sizeof(bytes),&session,7,3,
      nullptr,nullptr,1,&world,&route)==0);
  assert(route==CABAL_MERIT_ROUTE_DISABLED);
  std::cout<<"DIAMOND_PRODUCTION_GATE_NO_EXECUTION=PASS\n";
}
