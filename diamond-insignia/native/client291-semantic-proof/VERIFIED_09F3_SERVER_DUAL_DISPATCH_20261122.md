# CABAL v291 Diamond — exact WorldSvr 0x09F3 Merit dual dispatch (2026-11-22)

## Verified source and scope

Read-only independent disassembly of the owner's exact `WorldSvr_FULLCHAIN_20261108` ELF SHA256 `caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3`, verified against the previously established active-server SHA. No game launch, VM/SQL change, process injection or packet manipulation.

This complements `VERIFIED_CLIENT_TO_WORLD_MERIT_VS_DIMENSION_20261122.md`, where client local event `0x1A1` sends `0x09F3` and `0x1A2/1A3/1A4` are shown to be **Dimension Inventory**, not Diamond.

## Independently confirmed incoming Merit execution path

Exact registered handler `0xA40D90` (`OnCSCMeritMasteryLvUp`):

1. At `0xA40DC0` read **DWORD [packet+0x0A]**; at `0xA40DCA` read **DWORD [packet+0x0E]**. Both copied to a two-DWORD local structure `[rbp-0x18]`.
2. At `0xA40DD3` calls `0xA3CA50` with **the first DWORD** and the server manager pointer; it then checks the boolean return at `0xA40DD8`.
3. At `0xA40DEB` branches on that server-side boolean:
   - Zero -> `0xA40DED: call 0xA3B2D0`.
   - Nonzero -> `0xA40E00: call 0xA3C3A0`.
4. The selection helper at `0xA3CA50` walks a server-owned ordered-tree structure, comparing the first DWORD with stored keys (e.g. `0xA3CA8C: cmp [rax+0x20],ecx`). For a found entry, `0xA3CAEF: cmp dword [rax+0x24],1` provides the boolean result.

**Implication:** `0x09F3` is NOT one uniform Mastery workflow whose client value can be interpreted solely from its numeric ID. Existing WorldSvr already selects between two distinct processing paths based on **server-owned configuration**. The precise gameplay meaning of the selector's flag=1 and the allowed index ranges must be proven before any Diamond handler could replace either path.

### Why this changes the implementation gate

Current clone-only `diamond_merit_world_entry.cpp` classifies 18-byte `0x09F3` requests as Diamond *candidates* based on first DWORD range 159..474, while the second DWORD remains unknown. This is **not sufficient** for production interception: the original server routes by its own data model, and original Gold/Platinum must be preserved. Therefore keep default builds strictly passthrough/classification-only and **do not enable synthetic shadow routes for real accounts**.

The offline `verify_worldsvr_adjacent_c2s.py` now verifies all the above SHA-pinned byte anchors/call targets and records `mastery_159_474_accepted_proven=false`. Its synthetic regression tests reject modified selector branch instructions and call targets.

Next real proof: compare the active/server-resolved Mastery catalog entries and decoded client Merit resource for Grade 2 against the two server handlers, then implement an *authenticated, server-authoritative* Diamond-only branch and game inventory/WExp/SQL persistence in an isolated VM clone.

**Diamond playable: NOT YET. Active WorldSvr, lib.so, SQL and client are unchanged.**
