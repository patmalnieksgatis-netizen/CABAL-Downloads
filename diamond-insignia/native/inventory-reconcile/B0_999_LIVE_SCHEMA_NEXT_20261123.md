# CABAL v291 — Merit Medal Exchange Ticket 0xB0/999, GameData schema next step

**Date:** 2026-11-23. **Status:** instrument prepared and tested in offline
GitHub CI; **not yet run on EP36_291_TEST**.

## What is now independently grounded

1. The owner's `EP36_291_TEST` WorldSvr PID 438 returned exact
   original SHA256 `caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3`.
2. For item `33554961`, WorldSvr memory at catalog kind `0x13CAB80`
   returned `0xB0` and stack configuration `999`.
3. CABAL's own official **Triumph Update Review** explicitly confirms
   `Merit Medal Exchange Ticket` changing its max combination
   `127 -> 999` and its category **Quests -> Materials**. Source:
   https://cabal.playthisgame.com/en/News/Content/1489
4. The actual older WorldSvr `0xAE0E90` item count helper falls through
   to numeric **1** for `0xB0`; this is not evidence of true amount.
   The current Diamond ticket parser therefore returns
   `UnverifiedStackQuantity` and refuses actual debits.
5. `0x0BDA` and game-specific receipt/wexp/inventory persistence
   are still unproven, so **no in-game Diamond rank-up exists**.

## New verified-preflight route to real GameData

- `audit_live_inventory_schema.py` (VM host) queries SQL Server
  `Server01` **sys.tables**, **sys.columns**, **sys.procedures** and
  **sys.parameters** only, looking for inventory, character, item,
  Merit and WExp candidates. It never SELECTs player rows.
- Reuses previously successful `docker exec -i sql_main ... sqlcmd`
  connection model from `Audit-DiamondSqlDeep-v291.ps1`, obtaining
  password only inside the SQL container from existing environment.
  Does not print credential, SQL error contents, or connection string.
- Ensures VM hostname `cabalep33` and `sql_main` container RUNNING;
  Windows wrapper additionally checks that `EP36_291_TEST` is
  running before SSH.
- `Read-DiamondB0-GameDataSchema-291.ps1` downloads the script from
  a pinned GitHub commit, sends Python over SSH stdin, validates the
  metadata-only flags and saves only metadata JSON to Downloads.
  No WorldSvr restart, SQL write, CLI password or item manipulation.
- `tests/test_audit_live_inventory_schema.py` checks system-only SQL
  sources, output integrity, bad database and packet shape rejection,
  plus password handling; GitHub CI parses PowerShell wrapper.

**Important scope:** This will identify the actual schema and candidate
stored procedure signatures, **NOT automatically decode a B0 item's
quantity**. Only after the real GameData source is identified can a
read-only, narrowly-scoped stack comparison and authoritative debit
adapter be written.

## Why not skip the schema

The current laboratory backend `Server01_DiamondLab` uses a synthetic
`MedalItemCount`. It is NOT the real WorldSvr/DBAgent inventory.
Blindly charging `100` using synthetic AF/999 tests, treating
B0 as one item per slot, or modifying the production `lib.so` would
repeat previous unverified steps and can corrupt player inventory.

**No code or data was deployed to the VM** by adding these GitHub files.
