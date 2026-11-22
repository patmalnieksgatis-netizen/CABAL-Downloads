#ifndef CABAL_DIAMOND_MERIT_WORLD_ENTRY_H
#define CABAL_DIAMOND_MERIT_WORLD_ENTRY_H
#include "diamond_world_bridge.h"
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
// Packet format grounded in ELF SHA256 caec7772...6705c3, handler 0xA40D90.
// No live hooks, socket access, WorldSvr memory writes or binary patching.
#define CABAL_DIAMOND_MERIT_GATE_VERSION 1u
#define CABAL_DIAMOND_MERIT_C2S_MASTER_UP 0x09F3u
#define CABAL_DIAMOND_MERIT_C2S_PLATINUM_GRADE_UP 0x0B10u
#define CABAL_DIAMOND_LEGACY_C2S_MAGIC 0xB7E2u
#define CABAL_DIAMOND_MERIT_C2S_HEADER_BYTES 10u
#define CABAL_DIAMOND_MERIT_C2S_LEVELUP_BYTES 18u
typedef enum {
 CABAL_MERIT_PACKET_ORIGINAL=0,
 CABAL_MERIT_PACKET_DIAMOND_CANDIDATE=1,
 CABAL_MERIT_PACKET_INVALID=2
} cabal_merit_packet_kind;
typedef struct {
 uint32_t version;
 cabal_merit_packet_kind kind;
 uint16_t main_command;
 uint16_t packet_length;
 // WorldSvr actual Mastery handler reads DWORDs at packet offsets 0xA and 0xE.
 // The second DWORD is UNKNOWN; it is NOT accepted as level, cost or revision.
 uint32_t candidate_mastery_index;
 uint32_t unknown_field_at_0x0e;
} cabal_merit_packet_view;
int cabal_diamond_merit_classify_c2s(const void*,size_t,cabal_merit_packet_view*);

// No game reply serializer exists. This is for a synthetic clone trial ONLY:
// Normal builds NEVER call WorldBridge (compile-time protection).
// Only -DDIAMOND_ENABLE_SHADOW_TRIAL builds may call it when enabled==1.
// caller_expected_revision is trusted host state, NEVER client packet data.
typedef enum {
 CABAL_MERIT_ROUTE_ORIGINAL=0,
 CABAL_MERIT_ROUTE_SHADOW_APPLIED=1,
 CABAL_MERIT_ROUTE_SHADOW_REJECTED=2,
 CABAL_MERIT_ROUTE_DISABLED=3,
 CABAL_MERIT_ROUTE_INVALID=4
} cabal_merit_route_result;
int cabal_diamond_merit_shadow_route(
 const cabal_diamond_engine*,const void*,size_t,
 const void* authenticated_session,uint32_t authenticated_user,
 uint32_t caller_expected_revision,
 const cabal_diamond_world_callbacks*,void* backend_context,
 uint32_t execute_shadow_trial,
 cabal_diamond_world_result*,cabal_merit_route_result*);
#ifdef __cplusplus
}
#endif
#endif
