# Exact CABAL v291 Merit-adjacent C2S sender packet formats — 2026-11-23

**Result:** 42/42 exact original executable sender-instruction anchors matched,
including five direct calls to `0x2B7A40`; new offline parser + CI tests PASS.
This is **NOT** a verified Diamond-specific ABI or executable WorldSvr patch.

Exact owner's `CabalMain.exe`, 15,089,000 bytes, SHA256
`52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`.

All C2S packets begin with `E2 B7` at offset 0, little-endian 16-bit
declared length at +2, opaque transport dword at +4, 16-bit opcode at +8.
For the fields below, only **storage width/offset** is proven:
do not label any opaque value as an authenticated item, grade or Mastery ID.

| C2S | PDATA sender RVA | Wire length observed in code | Body |
| --- | --- | --- | --- |
| `0x0BDA` | `0x6DFD08` | n=0:14 B; n>0:`12+2n` | +10 `u16 count`, +12 `u16[n] raw entries` |
| `0x0BDB` | `0x6DFFE8` | total=0:20 B; total>0:`18+2×total` | +10 `u32 raw`, +14 `u16 count_a`, +16 `u16 count_b`, +18 two concatenated `u16[]` lists |
| `0x0BDD` | `0x6E03EC` | exactly 14 B | +10 `u32 raw` from `0x2437C8` object's +`0x178` |
| `0x0BDF` | `0x6DFF60` | exactly 11 B | +10 `u8 raw` from client singleton +`0xAB98` |
| `0x0BE0` | `0x6E0464` | count=0:18 B; count>0:`16+2n` | +10 `u32 raw`, +14 `u16 count`, +16 `u16[n] raw entries` |

The formulas are equivalent to `max(14,12+2n)`,
`max(20,18+2×total)` and `max(18,16+2n)` respectively.
Notice that the zero-entry and one-entry cases can legitimately share the
same declared packet length; **packet length alone is insufficient to
infer entry count**. For `0x0BDB` the sender increments an eight-bit
accumulator `BL` across both lists; the offline analyzer rejects
counts adding to >255 as ambiguous, not a claim that the game accepts
or rejects such inputs.

**Sender gating:**

- `0x0BDD`: function calls the send routine only when the loaded
  32-bit field is **not** `0xFFFFFFFF`.
- `0x0BDF`: the loaded nonzero byte must not exceed an independent
  32-bit client-side threshold at `+0xABA4`. The trace alone
  cannot prove this threshold, so successful shape classification
  is only structural.
- Other commands have client state/access checks and list building; the
  complete gameplay semantics are not established.

## Exact reproducible offline audit

```bash
python3 diamond-insignia/native/client291-wire/evidence/verify_merit_family_c2s.py \
  --client-zip /private/CABAL_v291_Diamond_Client_exact.zip
python3 -m unittest discover \
  -s diamond-insignia/native/client291-wire/tests \
  -p 'test_merit_family_c2s.py' -v
```

Optional `--packet-hex` reads a **provided offline** packet as hex,
checks header/count/length/gating, and outputs opaque raw fields.
It **does not send packets**. In particular
`verified_sender_shape=true` never means Diamond gameplay success.

## Next real-game requirement

Determine which UI interaction among these five corresponds to grade-up,
what its opaque fields represent, and the exact appropriate S2C response.
Then implement authoritative session, actual GameData item/WExp receipt and
crash-consistent save on a disposable clone. Never hijack the working
`0x0B10` Platinum handler or deploy via the old live sidecar (`exit 78`).
Private client executable and game SCP are not published.
