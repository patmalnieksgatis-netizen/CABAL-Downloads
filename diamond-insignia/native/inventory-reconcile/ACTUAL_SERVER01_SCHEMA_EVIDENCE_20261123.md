# CABAL v291 — actual Server01 GameData metadata evidence (2026-11-23)

The owner ran the metadata-only `Read-DiamondB0-GameDataSchema-291.ps1`
on VirtualBox `EP36_291_TEST` and returned
`CABAL_DIAMOND_B0_GAMEDATA_SCHEMA_20261123_193323.json`.

The JSON reports:
- `status=PASS`, `database=Server01`, `metadata_only=true`
- `player_rows_read=false`, `sql_mutations=false`,
  `worldsvr_changed=false`
- `result_may_be_truncated=true`: **180** stored procedures and **500**
  procedure parameters reached TOP caps, though **89** tables and **524**
  column rows did not. Missing procedure names/parameters in this
  FIRST report are NOT evidence of absence.

## Grounded GameData storage candidates

| SQL Table | Relevant observed columns | Confidence |
| --- | --- | --- |
| `dbo.cabal_Inventory_table` | `CharacterIdx int NOT NULL`, `Data varbinary(max) NULL` | Actual table and column types verified; packed `Data` item/quantity codec NOT established |
| `dbo.cabal_inventory_ex_table` | `CharacterIdx int NOT NULL`, `Data varbinary(8000) NOT NULL` | Secondary inventory candidate; game semantics NOT established |
| `dbo.cabal_WarExp_Table` | `WarExp bigint NOT NULL`, `WarExpEarn bigint NOT NULL`, `WarExpUsed bigint NOT NULL` | WarExp storage structure verified; CharacterIdx index/primary key still needs targeted query |
| `dbo.cabal_merit_platinum_table` | `UserNum int NOT NULL`, `HaveMeritPlatinumBagde tinyint NOT NULL`, `MeritPlatinumPoint int NOT NULL`, `MeritPlatinumMasteryPoint int NOT NULL` | Existing Platinum schema, **not** a verified Diamond grade 2 schema |
| `dbo.cabal_merit_platinum_mastery_table` | `UserNum int NOT NULL`, `MeritPlatinumMastery varbinary(8000) NOT NULL` | Existing Platinum Mastery schema |
| `dbo.cabal_merit_table` | `UserNum int NOT NULL`, `MeritPoint int NOT NULL`, `MeritMasteryData varbinary(8000) NOT NULL` | Existing base Merit schema |

The initial first-pass scan also finds procedure names:
- `dbo.cabal_tool_inventory_get`,
  `dbo.cabal_tool_inventory_set`
- `dbo.Cabal_Sp_InstantWar_GetWarExp`,
  `dbo.Cabal_Sp_InstantWar_SetWarExp`
- `dbo.cabal_tool_merit_platinum_set`,
  `dbo.cabal_tool_merit_platinum_mastery_set`

Known signature fragments from the first-pass scan:
`cabal_tool_inventory_set(@CharacterIdx int,@Data varbinary(max))`;
`Cabal_Sp_InstantWar_SetWarExp(@CharacterIdx int,@WarExp bigint,
@WarExpEarn bigint,@WarExpUsed bigint)`.
These are the **GM/procedure signatures**, not proven WorldSvr online
save ABI. Do not call these writers to "test" and do not assume they
can be combined safely without an authenticated owner lock and a
durable, transactional GameData path.

## Concrete next action: focused schema/transaction contract

Added:
- `audit_verified_gamedata_contract.py`: selects SQL `sys.*` metadata
  only for the six exact tables and 10 relevant procedures. Reads
  columns, primary-key and other index keys, triggers, procedure
  parameters, and only **structural booleans** about source definitions
  (`BEGIN TRAN`, `COMMIT`, `ROLLBACK`, Inventory/WExp/Merit
  references). Does NOT read or dump procedure source, game data or
  SQL credentials.
- `Read-Diamond291-GameDataContract.ps1`: exact
  `EP36_291_TEST` wrapper that downloads the pinned auditor and
  saves a JSON summary locally. No VM, WorldSvr, SQL or file mutations.
- `tests/test_audit_verified_gamedata_contract.py` and CI
  wrapper PowerShell syntax check.

This is the shortest defensible path toward confirming how to execute
**one atomic** Diamond debit in the *actual* inventory/WExp data
rather than the synthetic `Server01_DiamondLab` wallet.

## Still missing for in-game Diamond

- Real `0xB0` ticket count codec in inventory `Data`, not 999
  maximum stack and not the legacy `0xAE0E90` fallback of one.
- Real WorldSvr `0x0BDA` handler and verified selection semantics.
- Durable atomic debit and rank-save semantics under live character lock.
- Verified client S2C response and post-relogin in-game tests.

No VM/server or SQL changes have been performed by the assistant.
