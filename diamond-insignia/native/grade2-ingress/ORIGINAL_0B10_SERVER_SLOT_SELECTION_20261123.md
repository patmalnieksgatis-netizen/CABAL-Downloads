# Real WorldSvr Platinum `0x0B10` — u16 inventory-index list dataflow proof

**2026-11-23 — read-only exact server ELF, no hook/deployment.**

Owner-provided `WorldSvr_FULLCHAIN_20261108`, 10,596,184 bytes,
SHA256 `caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3`.
This is the WorldSvr where the original `0x0B10` Platinum badge grade-up
handler is registered at `0xA40F00`; newer `0x0BDA` is **not**
directly registered in this binary.

## Dataflow supported by exact x64 instructions

1. Handler `0xA40FD2` loads a `uint16` count from **request+0xA**,
   `0xA40FD7` loads declared `uint16` packet length from +2,
   `0xA40FDC` computes **`12 + 2×count`**, and
   `0xA40FE1` compares actual header length with the computed length.
2. `0xA41067` loads each `uint16` value from
   **request+0xC+2×index**. A red-black tree is used during traversal;
   the exact gameplay meaning of duplicate elements remains unproven.
3. `0xA4137D` compares each selected value with **`0x209` (521)**.
   For values in bounds, `0xA4135E` points at server-owned user data
   **`[r13+0x6508]`**; `0xA413F6` calls `0x587E30`.
4. `0x587E30` independently checks the same bound `<=521` at
   `0x587E43`, computes `3×index` at `0x587E9D`, shifts left 4 at
   `0x587EA6`, and adds the base at `0x587EAA`. The resulting
   stride is exactly **48 bytes per index**.
5. Original handler next accesses indexed record fields `+4` and
   `+8` and masks the latter with `0x06000FFF`. This strongly
   supports these `uint16` elements being **server inventory
   selection indices/slots**, not a quantity field or account identity.
   The actual authoritative stack quantity codec for item
   `33554961` is **still unverified**.

Reproducible source verifier
`verify_platinum_slot_list_worldsvr.py` SHA-checks the **exact** ELF,
verifies 15 instruction anchors and 2 relative CALLs with address-to-file
mapping via ELF `PT_LOAD`. Its synthetic ELF tests run in CI without
publishing the owner's original binary:

```bash
python3 diamond-insignia/native/grade2-ingress/verify_platinum_slot_list_worldsvr.py \
  --world /private/WorldSvr_FULLCHAIN_20261108
```

## Relationship to grade-2 candidate `0x0BDA`

The original v291 client's new `0x0BDA` sender uses **the same**
`u16 count + u16[]` packet shape and client selection builder as
existing Platinum `0x0B10`. It is reasonable to test whether the
`0x0BDA` list likewise selects authoritative inventory rows,
but **this is not yet a verified server ABI**: no corresponding 0BDA
WorldSvr handler is present as a direct static registry entry.

Consequently:
- **Do not** interpret the `u16` packet entries as ticket quantities.
- **Do not** spend tickets directly from untrusted packet slot indices.
- **Do not** assume that the old 0B10 handler can simply be retagged as
  0BDA, or register it without authoritative session and full rollback.
- The existing `DiamondGradeUp0BDA.cpp` remains disabled by default,
  requires all entry values to be independently attested by the server
  on clone builds, and emits **no unverified S2C success**.
- The staged 316-Mastery Diamond SCP passes static preservation parity,
  but real GameData and WExp persistence still require clone-only integration.

**No live game/server/account/VM/SQL assets changed.**
