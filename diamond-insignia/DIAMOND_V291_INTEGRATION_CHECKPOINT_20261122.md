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

## 2026-11-23 follow-up: offline wire trace and durable-ticket audit hardening

**Repository head `c84f49d33556` before this checkpoint update passed all three GitHub Actions suites**: native C++17 tests, SQL Lab Static Safety, and Mastery Offline Policy Gate. The v291 code remains NOT deployed / NOT playable.

New read-only `native/client291-wire/evidence/classify_offline_packet_trace.py` distinguishes known `0x09F3` Merit request/response *shapes* from `0x09F9/0x09FB/0x09FD` Dimension commands in supplied offline packet trace lines. Its tests run from `native/client291-wire/run-tests.sh`. It does **not** establish Diamond rank-up semantics, capture gameplay traffic or grant success.

`native/inventory-reconcile/DiamondInventoryReconcile.cpp` now checks each surviving ticket stack separately to reject an increased unit count hidden by a larger debit on another serial. It also binds the validated overall rank-up ticket debit to the actual native rule engine's `diamond::kDiamondRankTickets == 100` and statically confirms the donor item ID matches. Both fail-closed cases and legitimate split-stack consumption are covered by native CI. These checks continue to require a verified external quantity decoder; the test's `SyntheticStackCodec` is **not** a real game decoder.

The owner's exact archived `CabalMain.exe` + `meritsystem.enc` files were independently revisited off-server: EXE SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`. The 2026-11-22 observation remains: raw primary `.enc` trailer and initial XOR4 bytes do not establish a valid direct DEFLATE path; runtime-selected file/transform still unverified. The owner's v14 EventPass source provides the 30-byte inventory record shape, **not** the real 33554961 stack-quantity codec. No private binaries or v14 sources were committed to the public repository.

### Remaining blocking work
- Verify the actual Diamond UI grade-up C2S opcode, all semantic fields and client S2C response.
- Verify actual Merit file selected/decoded at runtime, not just the static `0x2178E0` loader.
- Establish authoritative WorldSvr session/registry plus real GameData item quantity encoding and durable WExp/receipt/SQL transaction; only then wire the save barrier and game response.
- Restrict any future deployment to a disposable VM clone with rollback; do not repeat old live `lib.so` sidecar path after `exit 78`.

**Working WorldSvr, DB, client installation, Supervisor and VM were not altered.**
