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

## 2026-11-23 major client/server protocol gap: actionable v291 Merit-adjacent opcode family

Owner's previously archived **original** 15,089,000-byte v291 client and
10,596,184-byte actual `WorldSvr_FULLCHAIN_20261108` were simultaneously
available and independently SHA-checked. New source:

- `native/client291-semantic-proof/verify_merit_client_server_gap.py`
- `native/client291-semantic-proof/test_merit_client_server_gap.py`
- `native/client291-semantic-proof/VERIFIED_V291_MERIT_UI_WORLD_OPCODE_GAP_20261123.md`

The v291 client has locally registered UI event sender callbacks for the
C2S family `0x0BDA, 0x0BDB, 0x0BDD, 0x0BDF, 0x0BE0`. It also registers
client S2C response handlers for `0x0BDA, 0x0BDB, 0x0BDC, 0x0BDD, 0x0BDF,
0x0BE0`. For all six receiver commands, precise original-client
instructions, RIP-relative callback addresses and binder target were
verified. `0x0BDC` lacks an identified outgoing callback within this
local five-command UI group, not necessarily globally.

In the exact WorldSvr executable, **zero recognized direct static
RIP-relative registration-slot references** were found for the five
client C2S opcodes, while `0x0B10` (existing Platinum grade-up) has
three directly verified positive-control references. This identifies
a real candidate compatibility gap. It does **not** rule out every
dynamic/indirect registration path or establish which commands are
actually Diamond rank-up. Do NOT repurpose Platinum `0x0B10`.

Owner's saved `lib.so_current_v291`, SHA256
`6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab`,
contains generic `ProcSystem::RegisterExtendedHandler` code but no
obvious direct `0x0BDA..0x0BE0` immediate references in a static
disassembly grep. This alone does not rule out dynamic registration.

**New practical next step:** reconstruct the exact C2S fields and S2C
success/error semantics of the proven v291 command family. Correlate
them with the actual client UI grade-up interaction and later the
compatible newer WorldSvr reference. Integrate one real authoritative
GameData/WExp/Diamond transaction on an isolated VM clone only after
proving semantics and receipt recovery; do not touch live WorldSvr.

All work in this checkpoint: offline binary analysis and GitHub source
changes only. No game server, VM, client, SQL data, or account changed.

## 2026-11-23 follow-up: exact Merit-family packet shapes and real SCP grade gate

New implementation files:
- `native/client291-wire/evidence/verify_merit_family_c2s.py`:
  **42** original x64 instruction anchors across five sender functions
  `0x0BDA,0x0BDB,0x0BDD,0x0BDF,0x0BE0` and five verified
  `0x2B7A40` send calls; read-only conservative packet header, size,
  counted-list, singleton and sender-gating checks. Local SHA-pinned
  real-client evidence 42/42 PASS.
- `native/client291-wire/tests/test_merit_family_c2s.py`: count-bound,
  negative and positive synthetic parser tests, now in `run-tests.sh`.
- `native/client291-wire/MERIT_FAMILY_SENDER_SHAPES_20261123.md`:
  exact fields and packet length formulas, with all opaque fields
  explicitly unspecified; a parsed packet is **not** a Diamond transaction.
- `native/catalog-audit/audit_real_merit_grade.py` and tests:
  fail-closed real-SCP grade-2 presence and rank-up-material audit.
- `native/catalog-audit/README_LATVIAN.md`: owner’s actual 54 866-byte
  `MeritSystem.scp` SHA256
  `307fc981ec3efe66f6cc1b0606ed7d86cd9e5a6e46205769a9bb34b012464295`
  contains 158 mastery rows, grade 0=64, grade 1=94, **grade 2=0**.
  Its sole `UpGrade_Material` row is grade 1, 20,000 WExp, item 33554961 ×100,
  **not** the isolated Diamond rule’s grade 2 30,000 WExp.
- `native/client291-semantic-proof/verify_merit_client_server_gap.py`
  has 12 additional actual bytes proving both `0x0BDB` and `0x0BDD`
  response paths feed **client Merit state slot 2** via `0x249730`.
  This is important state evidence, not confirmation of purchase semantics.

### First playable Diamond: remaining non-negotiable gates

1. Identify which verified `0x0BDA..0x0BE0` UI sender actually executes
   for Diamond **rank-up purchase**, the semantic meaning of the outgoing
   fields, and exact S2C success/failure response; preferably an isolated
   client runtime trace. No guessed `0x0BDD`=Diamond claim.
2. Add a **clone-only** valid `Badge_Grade=2` Mastery/resource catalog
   only from verified owner source; never replace existing Platinum config
   or `0x0B10` behavior blindly.
3. Implement authenticated WorldSvr registry/session binding, actual
   `GameData` ticket-stack quantity codec and durable WExp/item/receipt
   transaction with confirmed save barrier and rollback/retry parity.
4. Demonstrate actual player rank-up + relogin + duplicate-packet
   safety in a disposable VM, without breaking EventPass, Platinum,
   Costume, dungeons, SQL or existing accounts.

**Product status remains NOT PLAYABLE and NOT DEPLOYED; local simulations and CI
cannot substitute for the first real clone gameplay test. No live systems changed.**

## 2026-11-23 staged SCP parity closed — not a live runtime claim

The owner's **already-staged** private 116,812-byte
`MeritSystem.DIAMOND_STAGED_DO_NOT_INSTALL.scp` was independently
SHA-verified (`26c9c4cbe3136f67f0298c8e412a4aa7620ba46d62b5c3950880fe821f2ee2e5`).
It preserves all 19 original sections and every original row,
adds exactly 2442 rows including **316 Diamond grade-2 Mastery** and
the grade-2 30,000 WExp + 100 ticket material rule. New offline source
`native/catalog-audit/verify_staged_scp_parity.py` with regression tests
is now tracked and required in the native GitHub CI workflow.

**Updated assessment:** Diamond catalog staging itself is NOT a remaining
data-authoring blocker. Still unproven: true client grade-up C2S/S2C
semantics among `0x0BDA–0x0BE0`, authoritative WorldSvr session binding,
actual GameData stack codec and atomic inventory/WExp/receipt storage.
No deployment to active WorldSvr, client, VM or SQL was made.

## 2026-11-23 decisive C2S correction and first guarded 0BDA rank-up bridge

**Correction:** Earlier `0x0BDD` grade-up identification was
wrong due to an S2C handler attribution error:
`0x6DBDA0` is the client handler for existing Platinum
`0x0B13` **Mastery Slot Open Cancel**, NOT Platinum grade-up.
`0x0BDD` is its newer Merit-state-slot-2 cancellation counterpart,
with the same fixed 14-byte selector payload structure as 0B13.
`native/grade2-ingress/DiamondGrade2Ingress.cpp` has been
permanently made read-only, even if the previous clone macro is defined.

The **correct Platinum grade-up** is `0x0B10` with S2C
handler `0x6DB688`, and the strongest corresponding grade-2
client candidate is **`0x0BDA`** with S2C `0x6DA920`.
Both clients' senders build counted-list packets via
`0x244D3C`, use the same selection `+0xAB88`,
and reuse five success state/UI helpers. The callback's
Merit state index moves from 1 to 2. SHA-pinned evidence:
`native/grade2-ingress/verify_gradeup_0bda.py`,
`native/grade2-ingress/verify_grade2_mirror.py` and tests,
with narrative in
`native/grade2-ingress/PROTOCOL_CORRECTION_AND_0BDA_GRADEUP_20261123.md`.

**New actual code path:** `native/grade2-ingress/DiamondGradeUp0BDA.h/.cpp`
parses exact candidate C2S 0BDA headers, counted 16-bit entries and
length; refuses to trust them without independent server-side
matching of the entire entry list and authenticated session proof.
Normal builds have all mutations disabled. A separate compile-time
clone-only synthetic trial uses the existing Diamond
`DiamondCommandService` and backend with 30k WExp/100 ticket rank-up
rules, tests atomic failure and revision replay. It **never sends S2C**
or claims real game persistence, even on mock backend success.
GitHub CI builds/tests both configurations.

**Still not playable:** actual 0BDA grade-up action and entry semantics
need runtime confirmation, exact S2C format and WorldSvr registration,
actual GameData item 33554961 stack decoder and WExp debit, atomic
MSSQL/DBAgent receipt, cmd46/47 persistence reconciliation and VM-clone
relogin/rollback testing. The staged 316-Mastery SCP has already passed
preservation parity; do not rebuild it or deploy to the active server.

## 2026-11-23 exact Platinum server inventory-slot list mapping

The original **registered** WorldSvr Platinum `0x0B10` rank-up
handler `0xA40F00` was revisited directly in the owner's
10,596,184-byte SHA-verified ELF, rather than inferred from the
client alone.

Source-pinned `native/grade2-ingress/verify_platinum_slot_list_worldsvr.py`
verifies 15 original server x64 anchors and two direct CALLs.
It proves the `0x0B10` C2S packet contains a `u16` count at
`+0xA`, entries from `+0xC+2*i`, and a strict length formula
`12+2×count`. For each element the server checks `<=0x209`
(521) then uses helper `0x587E30` to index a **48-byte stride**
server-owned per-character record array. It reads an item-related
value at record `+8` masked by `0x06000FFF`. This is strong
evidence the list entries are **inventory selection slot/index values**,
not quantities, though the actual stack codec remains unknown.

New explanatory file:
`native/grade2-ingress/ORIGINAL_0B10_SERVER_SLOT_SELECTION_20261123.md`.
The same *client layout* exists in strong Diamond grade-up candidate
`0x0BDA`, but the new command has no corresponding registered
original WorldSvr handler, so its server semantics are still
**NOT PROVEN**; do not copy old binary addresses or trust client
selection for a debit.

CI both compiles the default-disabled/clone-only `0x0BDA`
prototypical ingress, confirms synthetic transaction failure and
replay safety, and tests synthetic ELF map/proof fixtures.
Full native rules workflow on source commit `f4c31b09d752`
completed **success**, including new tests. This is not
live-game certification or installable Diamond. Neither active
WorldSvr, VM, SQL nor game account was modified.

## 2026-11-23 WorldSvr ABI ingress, durability gate and real item quantity decoder

This continuation makes significant **native integration** progress:

1. The owner's archived WorldSvrRealm `PROCESSDATACONTEXT` header
   was reconciled with original WorldSvr `0xA40F14` and `0xA40F31`
   instruction reads. `native/grade2-ingress/Diamond0BDAWorldContext.h/.cpp`
   now performs fail-closed read-only guest process-context ABI and
   frame integrity checks, binds proof to the owner session, and
   forwards only a verified 0BDA candidate. Both default (disabled)
   and clone-mock transactional tests compile and pass CI.
2. `Diamond0BDASaveReplyGate.h/.cpp` stages a **candidate-only**
   7-byte 0BDA status response after `DiamondWorldSaveBarrier`
   cmd46/47 save ACK **and independent persistent inventory/WExp/
   receipt reconciliation**. It cannot send any S2C packet, and
   production builds cannot even encode synthetic success.
3. `DiamondWorldProcRegistryPreflight.h` asserts the actual
   `g_sUsrProcedureMap` registry structure/slots while preserving
   original Platinum 0B10/0B13; it is read-only, refuses occupied
   0BDA slots and **does not authorize installation** without
   verified host `PROCEDUREMAP` allocator/ABI.
4. **New original WorldSvr stack quantity breakthrough**:
   `0xA413AF` calls `0xAE0E90` on a selected 48-byte
   inventory slot. The helper derives quantities from item option
   `slot+0x18` using metadata-class-dependent upper 10, lower 16
   or lower 7 bits (or singleton). New
   `DiamondWorld48TicketUnits.h/.cpp` and synthetic CI tests
   implement these exact branches, but require an independently
   attested original runtime item catalog.
5. For exchange ticket `33554961 = 0x02000211`,
   item catalog key = index **529**, variant **1**,
   runtime metadata VA **`0x13CAB48`**. This address is proven
   in a memory-only, non-file-backed ELF segment. **The actual
   class fields +0x38/+0x3C are unavailable from this binary**,
   so the exact ticket-specific stack encoding is still a hard
   clone-run data dependency.

Source narrative:
`native/grade2-ingress/WORLDSVR_0BDA_CONTEXT_AND_SAVE_GATE_20261123.md`;
`native/grade2-ingress/WORLD_48_TICKET_UNITS_20261123.md`.

All 3 CI suites on code commit `9a441e6bf59b` completed
**success**. Live WorldSvr, client and SQL were not changed.
**Still no real handler registration, authoritative GameData
commit or playable Diamond.** Do not install old sidecar or assume
newer 0BDA server behavior from Platinum 0B10 without proof.

## 2026-11-23 follow-on: 0BDA ticket-list semantic gate and clone metadata capture

The user clarified that the "tickets" are **Merit Medal Exchange
Ticket** (`33554961 / 0x02000211`), required 100× in the
staged grade-2 SCP and original grade-1 materials.

**Safety correction:** the new `0x0BDA` client frame is *similar*
to Platinum `0x0B10` but its `u16[]` entries are NOT yet proven to
identify this item. The previously added
`Diamond0BDATicketSelection` immutable planning code is now
**fail-closed by default**: it requires two extra independent
semantics attestations and otherwise returns
`UnverifiedSelectionSemantics` without constructing the 100-ticket
plan. Only explicitly synthetic fixtures can set these conditions.
The tests cover failure when either is absent, selection bounds,
duplicate slots, incomplete totals, wrong item records, partial
stacks and unchanged inventory.

**Practical next implementation tool:** new
`native/grade2-ingress/capture_clone_ticket_catalog.py` reads
exactly the two 32-bit fields (`+0x38`, `+0x3C`) of the
`33554961` item catalog entry in a separately verified **disposable
clone WorldSvr process**, never the active server. It requires:
exact running WorldSvr SHA256/size, per-process
machine-id/PID/ELF hash authorization marker, valid memory map and
stable process start time, and reads only eight bytes via
`/proc/PID/mem` in O_RDONLY mode. This is a genuine path to resolve
the remaining 7-/10-/16-bit (or singleton) ticket count branch.
**No clone is presently attached, so the real metadata values
remain unknown.** Test fixtures never inspect a real process.
Documentation and clone-only usage contract:
`native/grade2-ingress/CLONE_METADATA_CAPTURE_20261123.md`.

The entire code/test change passed GitHub native rules workflow at
commit `5e13047f3250`, including the selection semantics gate and
clone capture safety test. Both other CI workflows also passed.
This certifies **offline tests only** and not an installable Diamond.

Still required: prove the `0x0BDA` semantics and runtime ticket
classification on a clone; implement host-attested WorldSvr
PROCEDUREMAP handler, real inventory/WExp debit in durable
GameData/MSSQL, exact 0BDA response ABI, relogin/restart/replay
gameplay proof. Never touch the live WorldSvr or assume item-stack
metadata without runtime evidence.
