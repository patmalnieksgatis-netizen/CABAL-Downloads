# CABAL v291 Diamond — corrected x64 UI event to Merit C2S map (2026-11-22)

## Inputs, exact identity

Independently read the owner's original 15,089,000-byte `CabalMain.exe` from prior `CABAL_v291_Diamond_Client_exact.zip`. SHA256 **`52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`**. PE32+ text RVA-to-file mapping is `file_offset=RVA-0xC00` within the relevant section. No game launch, client modification, process memory, VM, SQL, or server access.

## IMPORTANT correction of earlier event attribution

Previous notes asserted `0x6FF14C` (C2S `0x09F3` sender) is local event **`0x1A2`**. **This is incorrect**: the new direct byte-level event-registration sequence proves it is **`0x1A1`**.

At registration site `0x6F1228`, the exact client executes:

1. `mov DWORD PTR [rbp+0x10],0x1A1`;
2. `call 0x16BACC` at `0x6F1236`, obtaining the event entry;
3. `lea rdx,[rip+...] -> 0x6FF14C` at `0x6F123F`;
4. `add rcx,0x18` followed by `call 0x6B69C8` at `0x6F124A`, binding the callback.

**Only after that binding**, the code at `0x6F1253` sets the *next* event ID **`0x1A2`** and binds `0x6FCD44` at `0x6F126A`. Confusing these adjacent setup blocks caused the one-event shift in the prior report.

## Independently verified five-event neighborhood

| Local UI event | Callback RVA | Statically visible outgoing C2S |
| --- | --- | --- |
| `0x1A0` | `0x6FFA8C` | not assigned in this audit |
| `0x1A1` | `0x6FF14C` | `0x09F3`, **18 bytes** |
| `0x1A2` | `0x6FCD44` | `0x09FD`, **20 bytes** in examined send branch |
| `0x1A3` | `0x6FCD00` | `0x09FB`, **10 bytes** |
| `0x1A4` | `0x6FCF44` | `0x09F9`, **10 bytes** |

Raw call-site anchors:

- `0x6FF157: mov eax,0x9F3`, `0x6FF161` sets `E2 B7 12 00`, `0x6FF19B: call 0x2B7A40` (send).
- `0x6FCE79: mov eax,0x9FD`, `0x6FCF0C` sets length `0x14`, `0x6FCF18: call 0x2B7A40`.
- `0x6FCD15: mov eax,0x9FB`, `0x6FCD25` sets `E2 B7 0A 00`, `0x6FCD2D: call 0x2B7A40`.
- `0x6FCF59: mov eax,0x9F9`, `0x6FCF69` sets `E2 B7 0A 00`, `0x6FCF71: call 0x2B7A40`.

The 510-byte `0x6FCD44–0x6FCF42` PDATA-backed handler of `0x1A2` contains conditions and multiple response data paths, so `0x09FD` is observed in one branch; it is **not** proof of unconditional send or a particular rank-up mechanic.

## Implications for Diamond

These are adjacent *Merit/UI* events. No source evidence yet maps `0x1A1`/`0x1A2`/`0x1A3`/`0x1A4` specifically to **Diamond** Rank Up. The earlier `0x09F3` payload has singleton fields at +0x118/+0x11C; do not assume first DWORD is a trustworthy Diamond mastery ID or second is rank. Platinum grade-up `0x0B10` remains separately verified and must not be hijacked.

New SHA-pinned verifier `verify_ui_event_binding.py` rebuilds the exact mapping and asserts sender opcode byte anchors. Synthetic test `test_ui_event_binding.py` explicitly checks the off-by-one error and rejects altered constructor or callback calls. Neither is a live game patch.

**Important follow-up:** trace the UI producers of the `0x1A2 -> 0x09FD` branch and compare the command handling with exact server Gold/Platinum; determine whether a Diamond-specific UI event/command exists **before** implementing any new responder. No live `lib.so`, Sidecar, MSSQL or Supervisor mutation.
