# CABAL v291 Diamond investigation — exact local UI 0x216 to Merit C2S 0x0B10 (2026-11-23)

**STATUS: exact static x64 mapping proven; no gameplay / Diamond rank-up equivalence established.**

Pinned owner archive `CABAL_v291_Diamond_Client_exact.zip` contains 15,089,000-byte `CabalMain.exe`, SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`. All addresses below are **PE RVAs** and are verified against instruction bytes. This is read-only static evidence.

## Verified UI registration

- `0x6D0FD8`: `mov dword [rbp+0x10],0x216` (local UI event ID).
- `0x6D0FE6`: calls existing event entry lookup at `0x16BACC`.
- `0x6D0FEF`: RIP-relative LEA points to callback `0x6E06F8`.
- `0x6D0FFA`: callback registration call to `0x6B69C8`.
- The next local event is `0x217`, set **after** registration at `0x6D1003`, avoiding the previously observed off-by-one error at event 0x1A1.

## Verified outgoing 0x0B10 sender

- Callback `0x6E06F8..0x6E0948` writes magic `E2 B7` and opcode `0x0B10` into a local packet.
- `0x6E08B1` initializes a **14-byte** length when the packed list is empty.
- `0x6E08BB` and `0x6E08BF` adjust the output length based on an accumulated 16-bit count; `0x6E08C2` writes it into the header.
- `0x6E08D7` calls the same packet sender `0x2B7A40` seen elsewhere in the original client.
- The values in the packed entries, their game meaning and whether this action represents Platinum grade-up, Mastery, or something else remain **unverified**. There is **no proof** this command is Diamond rank-up. The protocol must not be hijacked to implement Diamond.

## Additional 0x2178E0 loader callers

A separate SHA-pinned static scan found three **direct `E8` callers** of `0x2178E0`:
`0x21CDE6` (indexed resource), `0x21D19E` (second call in resource initializer), and `0x8DC351` (a distinct large function). All have individually identified `.pdata` owner ranges. This third path is **not** evidence that it loads Merit or any particular ENC: it builds its own path and has no verified resource ID 52/53 assignment. Indirect calls and runtime paths are out of this static scan's scope.

## Reproduction

```bash
python3 diamond-insignia/native/client291-semantic-proof/verify_merit_ui_0b10.py --client-zip /private/CABAL_v291_Diamond_Client_exact.zip
python3 diamond-insignia/native/client291-resource-route/src/verify_all_resource_loader_callers.py --client-zip /private/CABAL_v291_Diamond_Client_exact.zip
```

Synthetic mutation and shape tests are included in GitHub CI. Original executable/ENC bytes are **not committed**.

## Implementation significance

This additional evidence narrows already-existing Merit UI behavior; it does **not** close the primary Diamond blockers: actual Diamond rank-up event/C2S and S2C, real v291 Merit asset loaded/decrypted, authoritative WorldSvr identity, true GameData 33554961 and WExp debit, durable MSSQL/DBAgent receipt/save, and isolated VM-clone gameplay validation. No live VM, WorldSvr, client, SQL or Supervisor files were changed.
