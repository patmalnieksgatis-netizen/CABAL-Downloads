# CABAL v291 Diamond — real MSSQL ODBC bridge, CLONE ONLY

**State (2026-11-22):** all native C++17 sources compile in CI (PASS), `libDiamondNative.so` exports `cabal_diamond_mssql_shadow_callbacks`, and the exact private staged Diamond SCP was independently loaded by that compiled shared library (116,812 bytes; SHA256 `26c9c4cbe3136f67f0298c8e412a4aa7620ba46d62b5c3950880fe821f2ee2e5`). **No actual MSSQL connection has been made from the model runtime, no game client packet has been handled, and no SQL scripts were executed on the user's VM.**

## What is implemented (not just a proposal)

- `native/diamond_mssql_shadow_bridge.h/.cpp`: concrete unixODBC C++ callback backend for `cabal_diamond_world_execute`, all four begin/load/commit/abort callbacks implemented.
- Connect via host-supplied `odbc_connection_string` (no credentials committed); reject **any** connection where `SELECT DB_NAME()` is not exactly `Server01_DiamondLab`, *before* any write. Connection/DSN does not authorize production databases.
- Authenticate host-held `session` pointer against an explicitly configured authenticated test session and match UserNum/nonce against the shadow-wallet row. A client packet cannot directly set `server_authoritative`.
- Use `SQL_TXN_SERIALIZABLE` and `WITH (UPDLOCK,HOLDLOCK)` per user to load shadow WExp, grade, item 33554961 proxy counter, point balance, revision, open slots and mastery levels; enforce revision compare-and-swap; mutate wallet+mastery in one SQL transaction and `SQLEndTran(SQL_COMMIT)` before success; use automatic SQL_ROLLBACK on any exception/failed SQL/abort.
- **Shadow only:** the SQL tables `cabal_diamond_bridge_wallet_v2`, `cabal_diamond_bridge_slot_v2`, `cabal_diamond_bridge_mastery_v2` are completely separate from CABAL tables and do **not** debit genuine WExp or inventory.
- `native/diamond_mssql_shadow_smoke.cpp`: opt-in lab-only test host: rank-up from test revision10, replay rejection, Mastery159 level1, then 4 concurrent requests for level2 with one winner, durable revision13. The host requires `--run-shadow-clone` and a DSN via environment; never prints credentials.

## Source files

- [Exact verified WorldSvr Merit registrations](./WORLDSVR_VERIFIED_MERIT_OPCODES_20261122.md)
- [ODBC C++ source](./diamond_mssql_shadow_bridge.cpp)
- [ODBC ABI header](./diamond_mssql_shadow_bridge.h)
- [MSSQL opt-in test host](./diamond_mssql_shadow_smoke.cpp)
- [SQL schema: 08, isolated clone only](../sql-lab/08_install_odbc_shadow_wallet_TEST_CLONE_ONLY.sql)
- [SQL seed: 09, synthetic UserNum 900001 only](../sql-lab/09_seed_odbc_shadow_user_TEST_CLONE_ONLY.sql)

## Clone-only execution order (do NOT do this on the active VM)

1. Confirm an isolated SQL Server database called **`Server01_DiamondLab`** exists; ensure it has been safely snapshotted and is separate from `Server01`. Never point ODBC to production.
2. Inside the clone, run `08_install_odbc_shadow_wallet_TEST_CLONE_ONLY.sql`, then `09_seed_odbc_shadow_user_TEST_CLONE_ONLY.sql`. Both have exact DB_NAME guards and refusal of accidental reinstallation/overwriting.
3. Build with the **actual clone's** compiler and glibc version; GitHub CI's Ubuntu-26 `libDiamondNative.so` may require GLIBC_2.38 and is NOT a drop-in for older CABAL containers:
```sh
g++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic -fPIC -shared \
  -o libDiamondNative.so \
  diamond_abi.cpp diamond_world_bridge.cpp diamond_mssql_shadow_bridge.cpp -lodbc
g++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic -pthread \
  -o diamond_mssql_shadow_smoke diamond_mssql_shadow_smoke.cpp \
  -L. -lDiamondNative -Wl,-rpath,'$ORIGIN'
```
4. Supply the ODBC connection string via a host-protected environment variable **`DIAMOND_CLONE_ODBC_CONNECTION`**, using an installed Microsoft SQL Server ODBC driver and a service identity **without access to production DBs**. Do not paste credentials into GitHub or chat.
5. With an explicit local copy of the staged `MeritSystem.DIAMOND_STAGED_DO_NOT_INSTALL.scp` in the CLONE, run:
```sh
./diamond_mssql_shadow_smoke --run-shadow-clone ./MeritSystem.DIAMOND_STAGED_DO_NOT_INSTALL.scp
```
This mutates *only* the synthetic shadow user 900001, one time; it is **not** idempotent. To retry, restore the clone snapshot. Do not set the test session nonce via a client request.
6. Verify expected `DIAMOND_MSSQL_SHADOW_CLONE=PASS`, `LAST_REVISION=13`, and manually read `*_bridge_*_v2` rows. The live player DB remains unchanged.

## CI and verification boundary

- All C++ unit tests and the ODBC pre-connection authentication negative tests: https://github.com/patmalnieksgatis-netizen/CABAL-Downloads/actions/runs/45004017426 — PASS. CI compiles `diamond_mssql_shadow_smoke` and verifies it refuses to run without explicit opt-in.
- Static SQL lab guards: `sql-lab/test_lab_v2_static.py` also covers `08` and `09`.
- The compiled ODBC shared library is downloadable in the CI artifact `diamond-native-v291-offline-linux-x64`, but is **offline-only and not presently installable in the active WorldSvr**.

## Game integration: final explicit blockers

The real source WorldSvr SHA256 `caec7772...6705c3` *does* register verified C2S Merit/Platinum opcodes, including `0x09F3` and `0x0B10`; these **are not proven to be Diamond-exclusive**. We have not verified a Diamond-specific client packet, WorldSvr session ABI, real item-debit transaction or game response payload. Never patch `0xA40F00`, overwrite its `0x0B10` handler or inject the clone ODBC module into the live game. The executable does not have a known Diamond handler, so the actual live-game hook remains outstanding. The archived `WorldSvrRealm` extension contains an older `CSC_CUSTOM_PACKET` dispatch but is not proof of compatibility with the v291 active process.

**No ongoing disassembly loops are necessary for this deliverable. To finish actual gameplay, the real Merit/Diamond C2S action and server inventory/WExp persistence code must be bound and integration-tested on an isolated VM clone.**
