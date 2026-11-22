// CABAL v291 / Diamond: callable C bridge to an authenticated WorldSvr handler.
// This interface is not a packet format or a hook. No opcode or binary address is assumed.
#ifndef CABAL_DIAMOND_WORLD_BRIDGE_H
#define CABAL_DIAMOND_WORLD_BRIDGE_H
#include "diamond_abi.h"
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define CABAL_DIAMOND_WORLD_BRIDGE_VERSION 1u
#define CABAL_DIAMOND_WORLD_APPLIED 0u
#define CABAL_DIAMOND_WORLD_REJECTED 1u
#define CABAL_DIAMOND_WORLD_BAD_ARGUMENT 2u
#define CABAL_DIAMOND_WORLD_AUTH_FAILED 3u
#define CABAL_DIAMOND_WORLD_LOAD_FAILED 4u
#define CABAL_DIAMOND_WORLD_COMMIT_FAILED 5u
#define CABAL_DIAMOND_WORLD_BAD_BACKEND 6u

// The caller MUST be a real, authenticated WorldSvr Merit handler; neither
// user_num nor world_session is to be taken from untrusted client packet fields.
typedef struct {
  uint32_t version;
  // Must authenticate the live session, lock the relevant user/character state,
  // and begin an atomic operation spanning inventory/WExp and SQL persistence.
  // out_transaction receives an exclusive backend token owned until commit or abort.
  int (*begin_authenticated_locked)(void* context, const void* world_session,
                                    uint32_t user_num, void** out_transaction);
  // Must load ALL gameplay fields from authoritative WorldSvr and SQL state.
  // Array pointers remain valid until transaction is consumed.
  int (*load_trusted_state)(void* context, void* transaction,
                            cabal_diamond_state* out_trusted);
  // Must atomically verify revision, update Diamond data, and deduct
  // EXACT item 33554961 + WExp within the SAME rollback-capable transaction.
  // Return success only after ALL writes are durable. Consumes transaction
  // on success. On failure, leave it active for abort_transaction.
  int (*commit_durable)(void* context, void* transaction,
                        const cabal_diamond_request* request,
                        const cabal_diamond_evaluation* evaluated);
  // Aborts and releases lock/token. Must be safe after begin/load errors.
  void (*abort_transaction)(void* context, void* transaction);
} cabal_diamond_world_callbacks;

typedef struct {
  uint32_t bridge_version;
  uint32_t status;
  int32_t engine_call_status;
  cabal_diamond_evaluation evaluated;
} cabal_diamond_world_result;

uint32_t cabal_diamond_world_bridge_version(void);
int cabal_diamond_world_execute(
    const cabal_diamond_engine* engine,
    const void* authenticated_world_session, uint32_t authenticated_user_num,
    const cabal_diamond_request* request,
    const cabal_diamond_world_callbacks* callbacks, void* backend_context,
    cabal_diamond_world_result* out_result);

#ifdef __cplusplus
}
#endif
#endif
