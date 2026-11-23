// Only for Server01_DiamondLab: bridge + real ODBC SQL Server transaction.
// Inventory/WExp/Platinum fields here are SHADOW synthetic data, not CABAL tables.
#ifndef CABAL_DIAMOND_MSSQL_SHADOW_BRIDGE_H
#define CABAL_DIAMOND_MSSQL_SHADOW_BRIDGE_H
#include "diamond_world_bridge.h"
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define CABAL_DIAMOND_MSSQL_SHADOW_ABI 1u
#define CABAL_DIAMOND_MSSQL_SHADOW_SESSION_TAG 0xD1A02B5Du
typedef struct {
  uint32_t tag;
  uint32_t user_num;
  uint64_t nonce; // host-verified session token, never from client request payload
} cabal_diamond_shadow_session;
typedef struct {
  uint32_t abi_version;
  const char* odbc_connection_string; // from host secrets, not checked into GitHub
  const cabal_diamond_shadow_session* active_authenticated_session;
} cabal_diamond_mssql_shadow_config;
// Callback implementation checks DB_NAME() == Server01_DiamondLab before any
// transactional mutation, and touches ONLY *_bridge_*_v2 shadow tables.
cabal_diamond_world_callbacks cabal_diamond_mssql_shadow_callbacks(void);
#ifdef __cplusplus
}
#endif
#endif
