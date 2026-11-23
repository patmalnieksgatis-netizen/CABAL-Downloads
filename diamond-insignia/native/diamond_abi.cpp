#include "diamond_abi.h"
#include "diamond_catalog.hpp"
#include <cstdint>
#include <limits>
#include <map>
#include <memory>
#include <new>
#include <sstream>
#include <string>
#include <utility>
struct cabal_diamond_engine {
  diamond::NativeCatalog catalog;
  explicit cabal_diamond_engine(diamond::NativeCatalog value)
      : catalog(std::move(value)) {}
};
extern "C" uint32_t cabal_diamond_abi_version(void) {
  return CABAL_DIAMOND_ABI_VERSION;
}
extern "C" int cabal_diamond_engine_create(
    const char* scp_bytes,size_t scp_len,cabal_diamond_engine** out_engine) {
  if (out_engine==nullptr) return -1;
  *out_engine=nullptr;
  if (scp_bytes==nullptr || scp_len<1000 || scp_len>2u*1024u*1024u)
    return -2;
  try {
    const std::string source(scp_bytes,scp_len);
    std::istringstream data(source);
    diamond::NativeCatalog catalog=diamond::read_native_catalog(data);
    *out_engine=new cabal_diamond_engine(std::move(catalog));
    return 0;
  } catch(const std::exception&) {
    return -3; // Malformed config; never fall back to synthetic defaults.
  } catch(...) {return -4;}
}
extern "C" void cabal_diamond_engine_destroy(cabal_diamond_engine* engine) {
  delete engine;
}
extern "C" int cabal_diamond_evaluate(
    const cabal_diamond_engine* engine,const cabal_diamond_state* input,
    const cabal_diamond_request* command,cabal_diamond_evaluation* result) {
  if (result==nullptr) return -1;
  *result={};
  result->abi_version=CABAL_DIAMOND_ABI_VERSION;
  if (engine==nullptr || input==nullptr || command==nullptr ||
      input->abi_version!=CABAL_DIAMOND_ABI_VERSION ||
      command->abi_version!=CABAL_DIAMOND_ABI_VERSION)
    return -2;
  if (input->server_open_count>316 || input->server_level_count>316 ||
      (input->server_open_count>0 && input->server_open_mastery_ids==nullptr) ||
      (input->server_level_count>0 && input->server_levels==nullptr) ||
      (input->active_category_mask & 0xffff0000u)!=0 ||
      input->server_authoritative>1 || input->platinum_badge>1 ||
      input->platinum_maxed>1 ||
      (command->command!=CABAL_DIAMOND_RANK_UP &&
       command->command!=CABAL_DIAMOND_MASTERY_LEVEL_UP))
    return -3;
  try {
    diamond::TrustedState state;
    state.authoritative=input->server_authoritative==1;
    state.platinum_maxed=input->platinum_maxed==1;
    state.platinum_badge=input->platinum_badge==1;
    state.badge_grade=static_cast<int>(input->badge_grade);
    state.revision=input->revision;
    state.wexp=input->wexp;
    state.tickets=input->verified_exchange_ticket_count;
    state.free_points=input->free_points;
    for(int i=0;i<16;++i)
      if ((input->active_category_mask & (1u<<i))!=0)
        state.active_categories.insert(i+11);
    for(size_t i=0;i<input->server_open_count;++i) {
      const auto id=input->server_open_mastery_ids[i];
      if (id<159 || id>474 || !state.server_open_slots.insert(static_cast<int>(id)).second)
        return -4;
    }
    for(size_t i=0;i<input->server_level_count;++i) {
      const auto e=input->server_levels[i];
      if (e.mastery_id<159 || e.mastery_id>474 || e.level<0 ||
          !state.levels.emplace(e.mastery_id,e.level).second)
        return -5;
    }
    const diamond::TransactionProposal proposal=command->command==CABAL_DIAMOND_RANK_UP
      ? diamond::rank_up(state,command->expected_revision)
      : diamond::mastery_level_up(state,engine->catalog.diamond,
                                 command->mastery_id,command->expected_revision);
    result->permitted=proposal.result==diamond::Error::Ok?1u:0u;
    result->rule_error=static_cast<std::int32_t>(proposal.result);
    result->requires_atomic_commit=proposal.requires_atomic_commit?1u:0u;
    result->new_revision=proposal.after.revision;
    result->new_badge_grade=static_cast<std::uint32_t>(proposal.after.badge_grade);
    result->new_wexp=proposal.after.wexp;
    result->new_ticket_count=proposal.after.tickets;
    result->new_free_points=proposal.after.free_points;
    if (proposal.result==diamond::Error::Ok &&
        command->command==CABAL_DIAMOND_MASTERY_LEVEL_UP) {
      result->changed_mastery_id=command->mastery_id;
      result->changed_mastery_level=proposal.after.levels.at(command->mastery_id);
    }
    return 0;
  } catch(...) {return -6;}
}
