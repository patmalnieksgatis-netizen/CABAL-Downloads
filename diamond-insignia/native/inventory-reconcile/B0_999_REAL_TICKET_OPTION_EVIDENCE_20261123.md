# CABAL v291 — next evidence for the real B0/999 Merit Ticket quantity

**Date:** 2026-11-23. **VM:** `EP36_291_TEST`. **Status:** bounded read-only code
and offline tests complete; real game data sample still awaits owner's VM
execution. The test VM was not modified by GitHub-only work.

## Known facts

- Original running WorldSvr SHA matches
  `caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3`
- Item `33554961 / 0x02000211`, WorldSvr catalog index 529 variant 1
- `kind_field38=0xB0`, `stack_field3C=999` (actual memory read)
- Official CABAL Triumph update notes changed Merit Medal Exchange Ticket
  from Quest to Materials, maximum stack 127 -> 999:
  https://cabal.playthisgame.com/en/News/Content/1489
- Actual `Server01` SQL schema and PK:
  `dbo.cabal_Inventory_table(CharacterIdx PK, Data varbinary(max))`
- Verified v14 reference normal-inventory persisted row: **30 bytes**,
  itemId +0 (8), itemSerial +8 (8), itemOption +16 (8),
  physicalSlot +24 (2), duration +26 (4).
- This v14 layout is a reference, NOT yet experimentally verified
  against the owner's v291 Data blobs.
- Original WorldSvr Platinum quantity helper `0xAE0E90` treats
  kind `0xB0` as a numerical **1** fallback. This must not
  be confused with the *true active count* of a material stack.

## Implemented targeted read-only evidence collector

`probe_live_b0_ticket_options.py`:
- executes in `EP36_291_TEST` host, uses the confirmed
  `sql_main` SQL Server connection
- reads **only** `dbo.cabal_Inventory_table.Data` from saved
  player inventory rows; this is a narrowly scoped inventory
  sampling operation **NOT a metadata-only scan**
- restricts to the known item catalog **LOW 32 bits**
  `0x02000211` so nonzero higher kind flags do not
  accidentally exclude real tickets
- returns no more than **48** ticket-specific 8-byte
  `itemOption` values plus the matching kind's upper 32
  bits; never exports UserNum, CharacterIdx, character name,
  itemSerial, or full inventory
- adds three anonymous `DATALENGTH(Data)` and modulo-30
  shape samples to detect row-layout disagreement
- presents 16-bit, 10-bit and 7-bit candidate interpretations,
  **explicitly marking all as unverified hypotheses**
- bounded query, `LOCK_TIMEOUT=3000`, low deadlock priority,
  no stored procedure execution and no SQL mutations
- result JSON reports `quantity_codec_verified=false`
  even if raw tickets are observed.

`Read-Diamond291-B0TicketOptions.ps1`:
- verifies `EP36_291_TEST` running
- downloads the exact pinned Python source from commit
  `648928b621c95a98769245237a229bc46b6670e1`
- passes it to guest via SSH stdin and validates result
  safety flags before writing a local Downloads JSON.

`tests/test_probe_live_b0_ticket_options.py`:
- validates only the targeted ticket data is selected,
  rejects invented count proof, 49+ items, malformed
  values, and parser output other than explicitly allowed fields
- the GitHub Actions native rules job also parses the
  PowerShell wrapper (no live game connection in CI).

**This is a data collection step, not a rank-up.**
If no target tickets are present, the result can't prove the
codec. If saved blob rows do not align to the v14 format,
the result cannot be interpreted as "the ticket doesn't exist".
Do not infer actual count solely from max stack 999 or
candidate fields; at least one independently known true UI count
for the same stack is required before deriving a codec.
A real durable item writer and `0x0BDA` handler are still absent.

## Current integration status

Existing `DiamondWorld48TicketUnits` /
`Diamond0BDATicketSelection` /
`Diamond0BDAGameplayAction` still reject real B0/999
stack debits until exact count and debit preservation are
independently verified. All source changes are confined to GitHub.
