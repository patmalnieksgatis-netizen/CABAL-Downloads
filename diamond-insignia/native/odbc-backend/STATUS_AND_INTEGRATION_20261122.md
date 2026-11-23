# Diamond Insignia v291 — ODBC transaction backend (2026-11-22)

**Source implementation and runnable offline tests delivered as conversation archive**
\`CABAL_v291_Diamond_ODBC_Transaction_20261122.zip\`, SHA256:
\`a134e82ac5815d2862e7e2476903b5f9a4334d0ec005ecd1137f456ab3e3689d\`.

> **Deployment status: NOT installed. NO live game server, VM, SQL database, or Supervisor changes.**
> This is Diamond Insignia, not Mandarat.

## Completed work

Created \`DiamondLabOdbcBackend.h/.cpp\` implementing the existing \`DiamondCommitGate::Backend\` interface through actual unixODBC APIs. The adapter:

- Rejects every DB except **Server01_DiamondLab** using \`SELECT DB_NAME()\` before any write; hard-restricts owner to synthetic \`UserNum=900001\`, \`SessionNonce=123456789\`. Identity is supplied through an external WorldSvr session-attestation callback, not a client packet.
- Reads the existing synthetic tables \`cabal_diamond_bridge_wallet_v2\`, \`...slot_v2\`, \`...mastery_v2\`, and prior receipt ledger \`cabal_diamond_v291_receipt_v1\`.
- Starts a **SERIALIZABLE** connection with autocommit disabled; holds a \`WITH (UPDLOCK,HOLDLOCK)\` lock on the account wallet for the entire rank-up or mastery purchase operation.
- Calls the real native staged 116,812-byte Diamond rules engine, then atomically updates the wallet (WExp, medal count, rank, points, revision), mastery level, and a committed receipt through the **same** ODBC transaction. On any failed statement, SQL_ROLLBACK is attempted; no success result is emitted before SQL COMMIT succeeds.
- Replays the original receipt on identical retry rather than charging twice, rejects different operations with the same revision, and refuses unrecognized Mastery IDs (Gold/Platinum are not replaced).
- Uses parameterized ODBC binding, no raw concatenated player query text.

The user-facing archive includes the complete new source, previous \`DiamondCommitGate\` source, a deterministic \`FakeOdbc\` test driver, the real compiled \`libdiamond_lab_odbc.so\` dynamically linked to \`libodbc.so.2\`, previous synthetic SQL scripts 08/09/10, plus a new READ-ONLY schema audit \`11_read_only_preflight_Server01_DiamondLab.sql\`.

## Actual tests completed

Compiled full adapter with \`-Wall -Wextra -Wpedantic -Werror\` against installed actual ODBC headers and \`libodbc.so.2\`. The *same* adapter source was run against a controlled fake ODBC driver with a real native rules evaluation:

\`\`\`
DIAMOND_V291_ODBC_GATE_TEST=PASS
SYNTHETIC_MSSQL_TRANSACTION=EXERCISED_VIA_FAKE_ODBC
SAME_TRANSACTION_WALLET_MASTERY_RECEIPT=PASS
COMMIT_FAILURE_ROLLS_BACK=PASS
DB_NAME_SERVER01_GUARD=PASS
CONCURRENT_8=ONE_APPLIED_SEVEN_REPLAYED
REAL_ODBC_DRIVER_COMPILATION=SEPARATE
ACTUAL_MSSQL_CONNECTION=NOT_TESTED
LIVE_WORLDSVR=UNCHANGED
\`\`\`

AddressSanitizer and UndefinedBehaviorSanitizer: PASS.

**Do not conflate a fake-ODBC driver with a real SQL Server integration test.** No actual MSSQL connection, WorldSvr authenticated session resolver, real game inventory or WExp persistence, exact v291 Diamond C2S/S2C codec, or game activation exists at this stage. The synthetic \`MedalItemCount\` field is NOT proven to represent game item 33554961 in actual live storage.

## Where Codex should continue

1. Use the complete ODBC implementation now committed at `diamond-insignia/native/world-session-bridge/deps/DiamondLabOdbcBackend.cpp`, plus existing `commit-gate` source; the original ZIP remains a historical reference.
2. On a disposable database **clone**, install/verify SQL scripts 08/09/10/11 in the embedded order and connect the compiled ODBC adapter to a real SQL Server driver. Prove actual transaction rollback on receipt failure and concurrent exactly-once behavior.
3. Authenticate actual \`WorldSvr\` session and map real game items/WExp and durable DBA ack/outbox; do NOT trust shadow wallet as game inventory.
4. Prove client v291 Diamond request and response format; do not hijack existing Platinum opcode 0x0B10.
5. Do not touch active v291 lib.so, LD_PRELOAD, or Supervisor. Previous direct lib.so and sidecar attempts failed with exit 78 and one rollback required manual config restoration; owner confirmed game is working after that restoration.

**Later update:** the complete clone-only ODBC C++ adapter is now committed
to `native/world-session-bridge/deps/DiamondLabOdbcBackend.cpp`.
`tests/FakeOdbc.cpp` and `tests/test_diamond_lab_odbc.cpp` use a
freshly generated **synthetic** Merit SCP and exercise row locking,
serializable wallet/mastery/receipt commit, rollback, duplicate replay and
eight concurrent requests. GitHub Actions also compiles a shared object
against **real** unixODBC headers/library. None of this connects to a
real SQL Server, a production player account, GameData inventory or WorldSvr.
