# CABAL v291 — Merit 0B10/0B13 versus 0BDA/0BDD: corrected client map (2026-11-23)

**Important correction:** the first exploratory note incorrectly matched new
`0x0BDD` to *Platinum grade-up* `0x0B10`. It compared the **wrong**
Platinum S2C callback. The actual original S2C handler for `0x0B10`
is **`0x6DB688`**. The similarly shaped success callback
`0x6DBDA0` is registered for **`0x0B13`**, the old
`CSC_MERIT_PLATINUM_MASTERY_SLOT_OPEN_CANCEL`. No `0x0BDD`
rank-up hook is allowed.

## Verified corresponding old/new actions

| Existing Platinum action | New client grade-2 counterpart | Evidence |
| --- | --- | --- |
| `0x0B10` — Platinum **Badge Grade Up** | `0x0BDA` — **strong grade-2 grade-up candidate** | Both client C2S build 14B + counted 16-bit entries from `0x244D3C`; both use selected Merit state `+0xAB88`, identical `0x2B7A40` sender; S2C handlers `0x6DB688` and `0x6DA920` implement analogous state/GUI update pipelines with group 1 versus 2 |
| `0x0B13` — Platinum **Mastery Slot Open Cancel** | `0x0BDD` — **strong grade-2 slot-cancel candidate** | Both C2S fixed **14 bytes**, send a 32-bit selector from Merit singleton `+0x174` versus `+0x178`, reject `0xFFFFFFFF`; both S2C success callbacks `0x6DBDA0` and `0x6DB0FC` clear Merit state group 1 versus 2 and call the same GUI refresh helpers |

**Real source:** owner's original exact `CabalMain.exe` SHA256
`52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`.
The original server's command registry independently confirms `0x0B10` is
Platinum grade-up and `0x0B13` is Platinum mastery slot-open cancel.
The **new** `0x0BDA` opcode is not directly registered in the exact
`WorldSvr_FULLCHAIN_20261108`; do NOT hijack the existing 0B10 handler.

### Byte-level proof

- `verify_grade2_mirror.py` verifies 22 exact C2S/S2C instruction
  anchors, 12 direct calls and 3 exact S2C bindings to correct the
  `0B13/0BDD` slot-cancel mapping.
- `verify_gradeup_0bda.py` independently verifies the actual
  `0B10/0BDA` C2S/S2C pairing and common grade-state client flows.
- These only read the private exact client archive. GitHub CI
  contains synthetic regressions; **private EXE/ENC not committed**.

```bash
python3 diamond-insignia/native/grade2-ingress/verify_grade2_mirror.py \
  --client-zip /private/CABAL_v291_Diamond_Client_exact.zip
python3 diamond-insignia/native/grade2-ingress/verify_gradeup_0bda.py \
  --client-zip /private/CABAL_v291_Diamond_Client_exact.zip
```

### Corrected engineering decision

Earlier `DiamondGrade2Ingress` attempted a clone-only rank-up route under
0BDD; that design was **immediately withdrawn**. Its code now remains a
**permanently non-mutating, compile-flag-independent classifier** and
the native CI actively proves that even the old trial macro cannot apply
rank-up or send success.

**Prioritize `0x0BDA` as the grade-up candidate** for future disposable
VM clone work. Do not yet treat the client list entries as verified
item-stack quantities or declare gameplay success: runtime selected UI,
real packet semantics, WorldSvr authenticated registration, GameData
stack-count decoder, WExp+MSSQL transaction and independent save receipt
must still be proven. No active server, VM, SQL, game client, account
or Supervisor modified.
