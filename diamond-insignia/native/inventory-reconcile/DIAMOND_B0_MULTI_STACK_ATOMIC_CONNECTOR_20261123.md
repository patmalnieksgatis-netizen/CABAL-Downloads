# CABAL v291 Diamond — real-material 100-ticket debit integration checkpoint

**Date:** 2026-11-23 (Europe/Riga). **Target:** `EP36_291_TEST` only.
**Deployment:** not installed on the VM; GitHub-only source and tests.

## Evidence actually collected

- WorldSvr original executable SHA `caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3`
- Item `33554961` metadata `kind+0x38 = 0xB0`,
  `stack+0x3c = 999`
- Owner's read-only `Server01` sample: two *anonymous* target
  inventory records, both `itemOption64 = 0x00000000000003E7`
  (decimal 999), high 32 bits of item kind are 0, row sizes
  divisible by v14's 30B format. The two records are not known
  to belong to the same character.
- Original `0xAE0E90` count helper returns numerical 1 for B0
  (default branch). That is **not** the true quantity proof.
- Exact SQL table keys: normal inventory and WarExp on CharacterIdx;
  Merit Platinum/mastery on UserNum. `cabal_character_table` on
  this VM has CharacterIdx but **no UserNum** column. Cross-table
  account/character mapping must be proven by authenticated native
  WorldSvr or actual account-slot mapping. A public older-server
  `CharacterIdx/8` rule is only an external clue; not proof for
  this VM. Do not derive credentials or ownership from arithmetic alone.

## New implementation useful for a REAL adapter

- `DiamondB0QuantityCodec.h` now supports
  `B0CountProfile::PlainPositiveOptionNoFlags`: with a known
  **independent game UI/native** count on the exact material stack
  and independently validated flag-free layout, the ENTIRE
  option word `1..999` is interpreted directly. There is no
  practical low10-vs-low16 ambiguity for these clean values:
  the two masks agree for every integer 1..999. High option bits,
  zero, >999, bad WorldSvr metadata, missing native evidence
  all reject.
- `DiamondB0PartialDebit30.h`: stages a single 999→899
  ticket-stack decrement, changing only eight `ItemOption`
  bytes of a clone.
- `DiamondB0SelectedDebit30.h`: stages a
  **WorldSvr-selected, multi-stack exact-100** decrement using
  an explicit verified mapping
  `(WorldSlot, persistedPhysicalSlot, persistedSerial)`.
  It parses all 30B saved inventory records, checks uniqueness,
  verifies their amounts, rejects unrelated changes, and
  independently verifies the resulting inventory with
  `VerifyPersistedTicketDebit`.
  Tests:
  - one 999 stack plus untouched 20-ticket stack: 1019→919 total
  - 60+80: consume 60+40, leaving exactly 40
  - 60+40: remove both exhausted ticket records
  - wrong slot / serial / duplicate / missing owner and codec proof
    all fail closed
  - full record removal requires **separate independently
    verified server removal semantics**, disabled by default.
- `Diamond0BDAGameplayAction` has an offline synthetic
  integration fixture for a single real-kind B0/999 stack
  whose 100-unit selected debit passes all rules; no S2C
  success is sent.

All tests in GitHub Actions operate on **synthetic memory and
privately deidentified observed options**, NEVER player inventory
SQL writes, production client process, or WorldSvr hooks.

## Work remaining before playable Diamond

1. Prove the same v291 client's actual B0 stack UI shows the
   amount represented in `ItemOption` for the very same
   inventory record; for plain 999, that is enough to activate
   the restricted count profile IF flags/row shape match.
2. Prove the actual `0x0BDA` packet's selected index means
   the same native inventory selection as original Platinum
   `0x0B10` and map its live 48B WorldSvr row to the saved
   30B physical slot + serial for the same owner. No
   guessed `slot+47` mapping.
3. Implement actual authenticated WorldSvr grade-2
   handler registration without disturbing Platinum 0B10/0B13
   and fix the previous experimental `lib.so` startup exit 78.
4. Implement ONE real durable serializable SQL/GameData
   transaction for inventory + WarExp + Diamond grade state
   with character-account binding and idempotent intent receipt.
   The individual existing inventory_set and WarExp_Set
   procedures are NOT proven one atomic operation.
5. Independently verify cmd46/47 saves, persist grade state
   across relog/restart, prove the client 0BDA S2C ABI,
   and only then enable the response.

**No game resources have been spent and Diamond still is not playable.**
GitHub CI success proves C++ and security gates, not a live server install.
