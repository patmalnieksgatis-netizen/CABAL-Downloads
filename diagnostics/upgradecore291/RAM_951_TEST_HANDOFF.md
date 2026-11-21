# CABAL v291 / EP39 — opcode 951 runtime-only compatibility trial

## Real failure and new test method (2026-11-21)

Two independent on-disk binary replacements changed only the opcode 951 guard from `139 + 2*N` to `259 + 2*N`; both SHA matched `08b3316be18d1ffe57d7a88d35ea99e0e4e4b2c3687b5b1a1829512f53a5052f`, but patched WorldSvr failed to start: `supervisorctl start: ERROR (spawn error), FATAL`. Both attempts automatically restored the unmodified binary and successfully started it. **The precise spawn failure mechanism is not proven** (may involve integrity validation or file attributes). Do not repeat V1/V2 on-disk patches.

Live 951 capture from the user's running original WorldSvr:
- Disk/running ELF SHA: `caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3`
- `MainCmd=951`, declared length **259**, old expected length **139**, delta **120**
- `WORD[packet+0x11]` escape slots = **0**; core count 1; main slot 129
- The 139 -> 259 immediate edit in the guard is exactly two bytes at memory VAs `0x7ac101` (0x8b->0x03) and `0x7ac102` (0x00->0x01). The full 259-byte client payload was not captured.

### New RAM-only patch (test VM only)

Conversation artifact: `CABAL_951_RAM_PATCH_TEST.ps1` and `CABAL_951_RAM_PATCH_BUNDLE.zip` (the latter contains C source, reproducible static x86_64 helper, Python remote loader and tests). The PS1 embeds a SHA-verified static Linux native helper and sends it over SSH to the test VM without requiring gdb, package downloads or internet.

- Before applying, remote loader verifies exact SHA of **running and disk** original WorldSvr and resolves host PID through `/proc/PID/status` `NSpid`.
- Native helper uses `PTRACE_SEIZE` and `PTRACE_INTERRUPT` to stop all threads, refuses if new/untraced threads, unexpected original instruction signature, or a thread executing inside the patch location.
- Uses `PTRACE_POKEDATA` to change **the two immediate bytes in process memory only** at the verified guard address. It re-reads the entire original instruction guard and verifies exact new bytes before detaching every thread.
- The executable file and SQL database are unchanged. There is no `supervisorctl` stop/start/restart. **The patch disappears automatically on WorldSvr restart**.
- Includes `check`, `apply`, `rollback`. RAM rollback restores the same two bytes without WorldSvr restart.
- SHA of native static helper: `ce455a77e4fe19bbf560917056f59db2e183fedc59472e93a7b638c8ba4d18b7`.
- Synthetic test with actual ptrace on an isolated 9-thread Linux process passed the 7-step status/apply/status/apply/rollback/status/rollback sequence. NOT YET TESTED ON USER CABAL VM or in-game.
- The test may reveal further incompatible protocol fields after the initial length check. Successful gameplay is not established.

Windows PowerShell after saving PS1 in Downloads:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\CABAL_951_RAM_PATCH_TEST.ps1" -Action check
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\CABAL_951_RAM_PATCH_TEST.ps1" -Action apply
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\CABAL_951_RAM_PATCH_TEST.ps1" -Action rollback
```

If `apply` succeeds, test Upgrade Core then Perfect Core in TEST only, followed by Force/Chaos/Divine regression and persistence after reconnect. Retain full stderr if the next validator fails. The RAM-only patch is a **test**, not a durable release fix.

## Verified in-game after previous RAM length-base trial

The user confirmed **ordinary Upgrade Core now works up to +20** with 259-byte opcode 951 RAM guard. Perfect Core works only to +17, and Safeguard does not work (separate issues). Do not roll back the working base patch while testing either follow-up.
