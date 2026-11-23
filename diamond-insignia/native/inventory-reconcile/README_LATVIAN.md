# Diamond v291 — v14 GameData inventory persistence audit (READ ONLY)

2026-11-22 — source + CI tested, **not live-game enabled**.

## Why this exists

The native Diamond rule engine and cloned SQL wallet already check that a
Platinum-to-Diamond rank-up spends 30,000 WExp and 100 exchange tickets
(item **33554961**). However, the cloned `MedalItemCount` SQL column
is a synthetic integer; it is **not** the real WorldSvr/DBAgent inventory.
Receiving an IPC cmd47 ACK is also not proof that a GameData item stack
was durably debited.

The owner's exact v14 source exposes the previously verified *normal inventory*
persistence layout (see private
`hooks/Packets/EventPassInventoryPersistV282.h`):

| Offset | Width | Known name |
| --- | ---: | --- |
| +0x00 | 8 | itemId |
| +0x08 | 8 | itemSerial |
| +0x10 | 8 | itemOption |
| +0x18 | 2 | physicalSlot |
| +0x1A | 4 | duration |

The 30-byte row format is reused here WITHOUT copying the owner's private
v14 source. The game-specific encoding of **stack quantity** in a row
remains **unknown**. A database snapshot containing a matching itemId does
not prove the number of units in a stack.

## Code

- `DiamondInventoryReconcile.h/.cpp` parses independently saved inventory
  snapshots as unaligned, packed 30-byte rows.
- Rejects malformed lengths, unknown/duplicate serial or slots, untrusted
  snapshots, changes to other inventory items, ticket serial/slot mutations,
  new ticket identities, unknown quantity encodings and incorrect totals.
  Also rejects any surviving ticket stack whose decoded unit count increases:
  a valid net debit must not conceal a credit to a separate stack.
- Requires an **explicit quantity decoder** originating from a separately
  verified GameData item-stack representation. `nullptr` always rejects.
- `VerifyPersistedTicketDebit` demands an actual decrease in total ticket
  units (rank-up); `VerifyPersistedTicketsUnchanged` demands byte-identical
  inventory (Mastery purchases).
- `tests/test_diamond_inventory_reconcile.cpp` compiles the real
  `DiamondWorldSaveBarrier.cpp` and demonstrates that even a matching
  cmd47 ACK cannot authorize a game success packet without all three:
  independently verified ticket inventory, verified WExp and a committed
  receipt. Fake unit quantities in the test are **synthetic only**.

GitHub CI: `.github/workflows/diamond-native-rules.yml`.

## Required for actual CABAL integration

1. Prove the game's real quantity/stack encoding for item 33554961 and
   what inventory source the GameData persistence procedure returns.
   The v14 EventPass `cabal_sp_eventpass_inventory_snapshot_v282` is
   useful as a read-only reference, **not** a confirmed Diamond debit API.
2. Implement a read-only, identity-bound GameData snapshot provider that
   independently loads the character's *persisted* before/after rows.
   Never accept client-provided bytes or a caller's bare assertion as proof.
3. Independently validate the actual WExp persistence, Diamond progression
   revision and durable receipt for the same player and transaction.
4. Only then connect all evidence to `DiamondWorldSaveBarrier::Reconcile`,
   and emit a proven v291 client success response after confirmation.
5. Test a complete isolated VM clone, retaining all current EventPass,
   Costume, Platinum, dungeons and original WorldSvr handlers.

**Not done:** quantity codec, live GameData queries, authenticated
WorldSvr registry callback, real MSSQL debit, v291 Diamond response codec,
gameplay testing. The source's test `SyntheticStackCodec` must **never**
be copied into a production module.

No live `lib.so`, WorldSvr, VM, SQL or client files were changed.
