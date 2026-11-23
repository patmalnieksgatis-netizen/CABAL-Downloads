// Versioned C ABI for the offline Diamond game-rules component.
// Not a network-packet format, and NOT a live WorldSvr hook.
#ifndef CABAL_DIAMOND_ABI_H
#define CABAL_DIAMOND_ABI_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define CABAL_DIAMOND_ABI_VERSION 1u
#define CABAL_DIAMOND_RANK_UP 1u
#define CABAL_DIAMOND_MASTERY_LEVEL_UP 2u
typedef struct cabal_diamond_engine cabal_diamond_engine;
typedef struct {
  int32_t mastery_id;
  int32_t level;
} cabal_diamond_level_entry;
typedef struct {
  uint32_t abi_version;
  uint32_t server_authoritative; // trusted native session only
  uint32_t badge_grade;
  uint32_t platinum_badge;
  uint32_t platinum_maxed;
  uint32_t revision;
  uint64_t wexp;
  uint32_t verified_exchange_ticket_count; // MUST be item 33554961
  int32_t free_points;
  uint32_t active_category_mask; // bit 0 => category 11, bit 15 => category 26
  const uint32_t* server_open_mastery_ids;
  size_t server_open_count;
  const cabal_diamond_level_entry* server_levels;
  size_t server_level_count;
} cabal_diamond_state;
typedef struct {
  uint32_t abi_version;
  uint32_t command; // 1=rank up, 2=mastery purchase
  uint32_t expected_revision;
  int32_t mastery_id;
} cabal_diamond_request;
typedef struct {
  uint32_t abi_version;
  uint32_t permitted;
  int32_t rule_error; // native diamond::Error enum; nonzero on rejection
  uint32_t requires_atomic_commit; // caller MUST perform all writes in ONE transaction
  uint32_t new_revision;
  uint32_t new_badge_grade;
  uint64_t new_wexp;
  uint32_t new_ticket_count;
  int32_t new_free_points;
  int32_t changed_mastery_id;
  int32_t changed_mastery_level;
} cabal_diamond_evaluation;
// Returns 0 on valid invocation, even if rule rejects; nonzero for invalid ABI,
// invalid trusted state pointers or missing/malformed native SCP input.
int cabal_diamond_engine_create(const char* scp_bytes,size_t scp_len,
                                cabal_diamond_engine** out_engine);
void cabal_diamond_engine_destroy(cabal_diamond_engine* engine);
int cabal_diamond_evaluate(const cabal_diamond_engine* engine,
                           const cabal_diamond_state* trusted,
                           const cabal_diamond_request* command,
                           cabal_diamond_evaluation* out_result);
uint32_t cabal_diamond_abi_version(void);
#ifdef __cplusplus
}
#endif
#endif
