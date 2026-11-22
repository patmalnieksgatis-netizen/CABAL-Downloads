#include "diamond_world_bridge.h"
#include <stdint.h>
#include <string.h>

extern "C" uint32_t cabal_diamond_world_bridge_version(void) {
  return CABAL_DIAMOND_WORLD_BRIDGE_VERSION;
}
extern "C" int cabal_diamond_world_execute(
    const cabal_diamond_engine* engine,
    const void* authenticated_world_session, uint32_t authenticated_user_num,
    const cabal_diamond_request* request,
    const cabal_diamond_world_callbacks* callbacks, void* backend_context,
    cabal_diamond_world_result* result) {
  if (!result) return -1;
  *result={};
  result->bridge_version=CABAL_DIAMOND_WORLD_BRIDGE_VERSION;
  result->status=CABAL_DIAMOND_WORLD_BAD_ARGUMENT;
  if (!engine || !authenticated_world_session || !authenticated_user_num ||
      !request || !callbacks ||
      callbacks->version!=CABAL_DIAMOND_WORLD_BRIDGE_VERSION ||
      !callbacks->begin_authenticated_locked || !callbacks->load_trusted_state ||
      !callbacks->commit_durable || !callbacks->abort_transaction ||
      request->abi_version!=CABAL_DIAMOND_ABI_VERSION)
    return -2;
  void* transaction=nullptr;
  bool consumed=false;
  const auto abort_if_needed=[&]() {
    if (transaction && !consumed) callbacks->abort_transaction(backend_context,transaction);
  };
  try {
    if (callbacks->begin_authenticated_locked(backend_context, authenticated_world_session,
                                               authenticated_user_num,&transaction)!=0 ||
        !transaction) {
      result->status=CABAL_DIAMOND_WORLD_AUTH_FAILED;
      abort_if_needed();
      return 0;
    }
    cabal_diamond_state trusted={};
    if (callbacks->load_trusted_state(backend_context,transaction,&trusted)!=0) {
      result->status=CABAL_DIAMOND_WORLD_LOAD_FAILED;
      abort_if_needed();
      return 0;
    }
    // A malicious client MUST NOT be able to set authoritative=1;
    // only load_trusted_state, reached after begin_authenticated_locked, may.
    if (trusted.abi_version!=CABAL_DIAMOND_ABI_VERSION ||
        trusted.server_authoritative!=1) {
      result->status=CABAL_DIAMOND_WORLD_BAD_BACKEND;
      abort_if_needed();
      return 0;
    }
    result->engine_call_status=cabal_diamond_evaluate(engine,&trusted,request,
                                                        &result->evaluated);
    if (result->engine_call_status!=0) {
      result->status=CABAL_DIAMOND_WORLD_BAD_BACKEND;
      abort_if_needed();
      return 0;
    }
    if (!result->evaluated.permitted || !result->evaluated.requires_atomic_commit) {
      result->status=CABAL_DIAMOND_WORLD_REJECTED;
      abort_if_needed();
      return 0;
    }
    // Commit callback owns ALL item/WExp/SQL writes, row revision check and durable commit.
    // The core never sends a client response before its confirmation.
    if (callbacks->commit_durable(backend_context,transaction,request,
                                  &result->evaluated)!=0) {
      // NEVER expose an approved result after a failed storage transaction.
      result->evaluated.permitted=0;
      result->evaluated.requires_atomic_commit=0;
      result->status=CABAL_DIAMOND_WORLD_COMMIT_FAILED;
      abort_if_needed();
      return 0;
    }
    consumed=true;
    transaction=nullptr;
    result->status=CABAL_DIAMOND_WORLD_APPLIED;
    return 0;
  } catch (...) {
    result->evaluated.permitted=0;
    result->evaluated.requires_atomic_commit=0;
    result->status=CABAL_DIAMOND_WORLD_BAD_BACKEND;
    try {abort_if_needed();} catch(...) {}
    return -3;
  }
}
