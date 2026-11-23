# EP36_291_TEST actual GameData SQL contract — 2026-11-23

Source: operator-uploaded `CABAL_V291_REAL_GAMEDATA_CONTRACT_20261123_195042.json`,
obtained via metadata-only script on the original `Server01`. Status **PASS**.
This result is complete for the six targeted tables and ten procedures:
26 columns, six PK indexes, zero triggers, 28 parameters,
ten procedure metadata-only signatures and ten module structural summaries.

## Actual table identities and persisted fields

| Table | SQL primary key | Confirmed payload |
|---|---|---|
| `dbo.cabal_Inventory_table` | `CharacterIdx` | `Data varbinary(max) NULL` |
| `dbo.cabal_inventory_ex_table` | `CharacterIdx` | `Data varbinary(8000) NOT NULL` |
| `dbo.cabal_WarExp_Table` | `CharacterIdx` | `WarExp`, `WarExpEarn`, `WarExpUsed` all `bigint NOT NULL`; `ModifiedDateTime datetime NULL` |
| `dbo.cabal_merit_platinum_table` | `UserNum` | `HaveMeritPlatinumBagde tinyint`, Merit points/mastery and other Platinum status fields |
| `dbo.cabal_merit_platinum_mastery_table` | `UserNum` | `MeritPlatinumMastery varbinary(8000) NOT NULL` |
| `dbo.cabal_merit_table` | `UserNum` | `MeritPoint`, `MeritMasteryPoint`, `MeritMasteryData varbinary(8000)` |

**Crucial:** `UserNum` is NOT the SQL PK of `cabal_Inventory_table`
or `cabal_WarExp_Table`. The real live WorldSvr owner adapter MUST
independently attest that a given `CharacterIdx` belongs to the same
authenticated `UserNum`. Guessing arithmetic on an integer ID is forbidden.

## Actual saved-procedure metadata

- `dbo.cabal_tool_inventory_set(@CharacterIdx int, @Data varbinary(max))`
  — no internal `BEGIN TRAN` or `COMMIT` text detected; references inventory table.
- `dbo.Cabal_Sp_InstantWar_SetWarExp(@CharacterIdx int,
  @WarExp bigint, @WarExpEarn bigint, @WarExpUsed bigint)`
  — `BEGIN TRAN` and `COMMIT` occur; `ROLLBACK` text **not**
  detected. This does not establish that its behavior safely joins
  another caller-controlled transaction.
- `dbo.cabal_tool_merit_platinum_set` uses `UserNum` as first arg
  and writes several Platinum fields; no standalone transaction markers.
- `dbo.cabal_tool_merit_platinum_mastery_set(@UserNum int,
  @MeritPlatinumMastery varbinary(8000))`
  — no standalone transaction markers.

The actual source bodies were not exported, only boolean structural
hints from `sys.sql_modules`. The checks above cannot prove atomicity
or absence of all error paths. There are **no triggers** on the six
inspected tables to silently join separate writes.

## Implemented next code safeguard

`grade2-ingress/Diamond0BDAGameplayAction.h/.cpp` now includes
`RealGameDataBackendContract`. Before any `AtomicCommitCallback`
it demands identical original WorldSvr `UserNum`/`CharacterIdx`,
validated mapping, exact PKs, one transaction across Inventory,
WarExp, Platinum and Platinum Mastery, CAS/replay-proof revision and
receipt, and explicit proof the adapter is **not merely chaining**
`cabal_tool_inventory_set` and `Cabal_Sp_InstantWar_SetWarExp`.

All these capabilities **default false**. A host must implement them
in reality; merely toggling flags is not evidence. A test fixture
explicitly uses synthetic data; no game DB writes are performed.

## What this DOES NOT prove

The true B0/999 item 33554961 quantity encoding in `Data` remains
unknown. 999 is the maximum configured stack, **not the ticket count**.
The WorldSvr 0xAE0E90 fallback of one is not a verified ticket count.

No true WorldSvr registration for `0x0BDA`, durable Diamond-grade
representation, verified client S2C or actual in-game rank-up exists.
Do not deploy or enable an unfinished resource debit.

No part of this work changed the EP36_291_TEST VM, WorldSvr or SQL.
