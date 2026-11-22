# Diamond Insignia v291 / v14 — integration checkpoint, 2026-11-22

**Current status:** complete isolated/native rule and synthetic persistence
pipelines; **NOT playable** and **NOT deployed** on the live CABAL server.

## End-to-end code in this repository

The previously archive-only ODBC backend is now available as ordinary
source under:
- `native/world-session-bridge/deps/DiamondLabOdbcBackend.cpp`
- `native/commit-gate/DiamondCommitGate.cpp`
- `native/world-session-bridge/DiamondWorldSessionBridge.cpp`
- `native/world-session-bridge/tests/FakeOdbc.cpp`

A new CI test
`native/world-session-bridge/tests/test_diamond_session_odbc_endtoend.cpp`
now executes one contiguous, real C++ pipeline:

```
WorldSessionAuthority (synthetic registered session + exclusive lock)
 -> ProveWorldSessionV14 (real v14 +0xE8/+0x890/+0xA24 identity reader)
 -> DiamondCommitGate::Execute
 -> DiamondLabOdbcBackend (real parameterized, serializable ODBC source)
 -> FakeOdbc transaction engine (SIMULATED SQL, no real MSSQL)
 -> wallet / mastery / durable receipt in one synthetic commit
 -> retry: same receipt, no second debit
```

Passed in GitHub CI: rank-up, two Mastery levels, malformed/forged sessions,
wrong database guard, rank/mastery replay and 8 concurrent identical requests
(**one applied, seven replayed**). The backend also separately compiles and
strict-links against genuine unixODBC headers/library; those link checks
are not proof of a live SQL Server connection.

## GameData inventory proof now partially implemented

`native/inventory-reconcile/DiamondInventoryReconcile.h/.cpp`
uses the *owner-provided v14* persisted normal-inventory row shape (30 B)
to compare independently read before/after inventory snapshots. It
requires a real game-specific, trusted item-quantity decoder. Rank-up must
actually debit item 33554961; Mastery must leave ticket inventory unchanged.
The `DiamondWorldSaveBarrier` test proves that a cmd47 response on its own
cannot unlock success. Synthetic test quantity encoding is **not** a verified
CABAL encoding and must not be used in game.

## Strict blockers for playable Diamond

1. Determine the **actual v291 Diamond client command, both C2S payload
   semantics, and correct S2C response**. The existing 0x09F3 ID range is
   still a candidate and the client's success branch reads bytes +7..+10
   in some states; do not invent an 11-byte success payload.
2. Bind to a genuinely authoritative WorldSvr session registry and game
   Merit selector. Current source uses a synthetic authority in tests.
3. Prove actual item 33554961 stack count/encoding in GameData persisted
   30-byte rows; the preexisting v14 EventPass inventory snapshot routine
   can be audited read-only but is **not** a Diamond debit primitive.
4. Implement ONE atomic actual GameData/WExp/Diamond commit with receipt,
   or durable outbox and DBAgent cmd46/47 recovery. The current
   `Server01_DiamondLab` wallet is completely separate from game storage.
5. Connect verified native response codec, only test on a disposable VM
   clone, and preserve Gold, Platinum, Costume, dungeon and EventPass
   behavior. The shadow ingress must never double-handle a real packet.

**No active VM, game client, WorldSvr process, lib.so, LD_PRELOAD,
Supervisor, or SQL data were changed.** Private SCP and binaries are not
committed to public GitHub.
