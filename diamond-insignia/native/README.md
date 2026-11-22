# Diamond Insignia v291 — compiled native rules module

**Build status:** real C++17 implementation and versioned Linux x64 C ABI, CI PASS.  
**Game status:** NOT integrated with the active WorldSvr, SQL, or live client. NO gameplay claim.

## Implemented and source-controlled

- `diamond_rules.hpp`: server-authoritative Gold/Platinum-safe Diamond grade 2 rank-up, 30,000 WExp / 100 exchange ticket checks, mastery prerequisite/max-level/point validation, revision/replay protection. Transactions return *proposals*; no hidden writes.
- `diamond_catalog.hpp`: parses the real `MeritSystem.scp` field/section layout; requires **64 Gold, 94 Platinum, 316 Diamond definitions, 1096 Diamond level-cost rows, exactly 4 `[SpecialMastery_Active]` Diamond edges**, 108 `LinkedMastery_Index` edges, and the source-proven grade 2 upgrade costs. Missing or inconsistent values are rejected. No donor XML or private stage data is committed.
- `diamond_transaction.hpp`: typed authenticated session-to-WorldSvr transaction interface. Real backend must own the authority snapshot, inventory item 33554961, compare-and-swap revision, atomic SQL+resource debit and rollback.
- `diamond_abi.h` + `diamond_abi.cpp`: callable `cabal_diamond_engine_create`, `cabal_diamond_evaluate`, `cabal_diamond_engine_destroy` with versioned C structs, fail-closed catalog parser, no guessed packet offsets. Produced `libDiamondNative.so` is **offline/experimental**: not a ready WorldSvr plugin, not tested for ABI compatibility with the existing guest OS.
- Executable native tests: `test_diamond_rules.cpp`, `test_diamond_transaction.cpp`, `test_diamond_catalog.cpp`, `test_diamond_abi.cpp` plus shared synthetic SCP fixture.

CI (all tests PASS): https://github.com/patmalnieksgatis-netizen/CABAL-Downloads/actions/runs/45001061964  
Artifact: **diamond-native-v291-offline-linux-x64** from that run, contains `libDiamondNative.so`. Artifact expires per the 7-day retention setting. **Do not LD_PRELOAD or dlopen this into the live WorldSvr.**

## Private staged native SCP: real-data preflight, not published

Compared exact private uploaded files in the authorized conversation work container:

- Original active `MeritSystem.scp`: 54,866 bytes, SHA256 `307fc981ec3efe66f6cc1b0606ed7d86cd9e5a6e46205769a9bb34b012464295`.
- Diamond staged SCP: 116,812 bytes, SHA256 `26c9c4cbe3136f67f0298c8e412a4aa7620ba46d62b5c3950880fe821f2ee2e5`.
- Same 19 sections, every original section's nonempty row prefix intact. Added rows: Mastery Base 316, Mastery Value 1096, Upgrade Material 1, SlotOpen Material 616, SlotOpen Time 308, SpecialMastery Material 1, SpecialMastery Value 100, **SpecialMastery Active 4** = total **2442**. Real-data byte comparison passed.
- The `12` client/donor SpecialCategory activation edges are **not** 12 `SpecialMastery_Active` rows in the native SCP. The server-native staged table has 4 added main-category activations. Their gameplay semantics still require server adapter verification.

**The staged SCP is not installed**, and private game content should not be pushed to a public GitHub repository.

## Actual integration still required

The confirmed original `WorldSvr` is a proprietary/stripped binary; the available `EP36Compat_v282 (1).c` source is a packet-translation/unicast hook, **not** a Diamond Merit server handler and not a safe native hook address for this feature.

1. Find an authenticated, verified Merit C2S handler and the exact v291 request/response ABI in the **actual target WorldSvr**. Do not invent opcodes, offsets or vtable slots.
2. Hook the verified session context into `diamond_transaction.hpp` and the authoritative inventory/platinum state. Never populate `server_authoritative` or exchange-ticket count from client packets.
3. Implement an actual SQL Server clone transaction + inventory/WExp debit and Diamond state commit under a single revision-checked unit. Current `sql-lab` is only an isolated stub.
4. Load verified native SCP in the clone, not the live server. Exercise rank-up, masteries, single active subcategory, linked effects, reconnect, restart, rollback, replay and preservation of existing Platinum and other extensions.
5. Only deploy after binary/ABI compatibility, entire clone integration and rollback pass.

**Do not claim Diamond is playable yet.** The achievement here is a compiled, tested rules/config/ABI module plus a transaction-boundary contract, not the missing WorldSvr hook. Stop producing V10+ client diagnostic probes as substitutes for the native integration.
