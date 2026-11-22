# Diamond Insignia — native C++17 rules core (not yet plugged into WorldSvr)

## Implemented, compiled and tested

- `diamond_rules.hpp`: server-trusted and revision-gated rank-up proposal from maxed Platinum to Diamond grade 2. Requires verified Platinum badge/max, at least 30,000 WExp and 100 server-verified exchange tickets of donor item ID 33554961.
- Mastery level purchase proposal: validates authoritative state, grade 2, 316-ID window (159..474), verified active category/slot, mastery cap, prerequisite level, points and SQL-compatible revision. LinkedMastery effects fail closed.
- `test_diamond_rules.cpp`: compiled with `g++ -std=c++17 -Wall -Wextra -Werror -pedantic` and executed via GitHub Actions (PASS after revision overflow fix).
- No Gold/Platinum state changes, no live server binary modification, no SQL writes. Neither API mutates its input state; it returns proposed new state for a real WorldSvr/DB adapter to atomically commit.

CI: https://github.com/patmalnieksgatis-netizen/CABAL-Downloads/actions/runs/45000282808

## Why this is not yet a playable Diamond feature

The existing running WorldSvr has no verified Diamond packet handler or DB adapter. `diamond_rules.hpp` is a **working compiled native rules component**, not a WorldSvr integration. It does not decode the v291 Merit ENC or synthesize game packets. No runtime / gameplay claim.

## Specific integration contract for the native adapter

1. Identify existing authenticated Merit handler/packet dispatch inside **the real v291 WorldSvr**. Do not guess opcode sizes or replace the binary from an EP45 donor.
2. Populate `TrustedState` solely from verified WorldSvr/SQL inventory, badge/score, session and character states. Bind ticket count specifically to item 33554961; do not accept a free-form count from the client.
3. Load exact 316 Diamond mastery definitions and costs from verified staged add-only SCP. Enforce actual server-verified slot/category selections and 108 LinkedMastery rules before unblocking any linked effects.
4. After `rank_up` or `mastery_level_up` returns `Error::Ok`, atomically debit the item/WExp or mastery points and persist Diamond grade/levels under the same user's transaction and revision. On any failure, no deductions or partial updates; replay/duplicate packets must not double-debit.
5. Serialize the *confirmed* v291 response ABI; retain original Gold/Platinum handlers and buffers untouched. Check reconnect and restart persistence against a test account in a fully backed-up isolated clone.
6. Integrate to current clone WorldSvr and SQL first, not live. Preserve working Platinum, Costume, dungeons, upgrades and character data.

**Stop condition:** No release or live apply until authenticated packet IDs, actual runtime loader behavior, and atomic persistence are verified. Additional V10+ client disassembly alone does not satisfy these requirements.
