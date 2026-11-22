# Verified running lib.so exact-binary compatibility gate — 2026-11-22

## User-supplied active module

Received the **actual active** `/usr/lib/cabal/lib.so` copied from the `EP36_291_TEST` VM, also verified by the user against both running WorldSvr PIDs 43882 and 80716. SHA256:

```text
6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab
```

Binary: ELF64 little-endian x86_64 **shared object**, 193,496 bytes, symbol table present (not stripped). Build-ID `41a92d4a1fe8a283bfb1e00d4f06375365ad222f`, RUNPATH `/usr/lib/cabal`, requires glibc up to 2.38. The source archive from February 2026 contains an old 91,568-byte `build_tmp_libso/build/lib.so`, **NOT** the live binary.

Backed up by user, verified matching:

```text
/root/cabal_diamond_backup/lib.so_before_diamond_20261122
```

The running process loaded the library as `/usr/lib/cabal/lib.so`. It also uses active executable `/etc/cabal/migration_tools/ep36-costume-trial-v1/native/WorldSvr_01_01`.

## Proven directly by current ELF (not archived source inference)

- `ProcSystem::DoProcessDataCtx(void*,PROCESSDATACONTEXT*)` at **ELF RVA 0x68E0**, 326 bytes. At `0x68FF` reads main command from packet pointer at context `+0x8`; instruction branches for `0x0BB6`, `0x0BB7`, `0x0BB8`, `0x0BC3`, and **falls through to the original WorldSvr dispatcher** for the existing Merit Mastery opcode `0x09F3`.
- Existing original-dispatch trampoline stored in static local `ProcSystem::oDoProcessDataCtx` at **RVA 0x2B510**; the current function jumps via it at RVA `0x692F`. This is an internal runtime pointer, not a server binary file address.
- The active module also exports `ProcSystem::Attach()` at **RVA 0x6D00** and `ProcSystem::ForceRegisterHandlers()` at **RVA 0x67C0**.
- **This current binary contains substantial newer user features absent from the archived 19-file source**, including `EventPassClaimTxnV282`, `EventPassRelogReplayV282`, `EventPassPersistV282`, `EventPassClaimWindowV282`, `EventPassRecoveryV282`, `EventPassPushRuntimeV282`, `OnEventPassClaimDryRun`. Rebuilding archived `CABAL_FOR_CHATGPT.zip` source to replace the current .so would silently remove these features and is UNSAFE.
- Current ELF has **no exported `DiamondBoundIngress`, `cabal_diamond_world_execute`, or `cabal_diamond_proc_bind_shadow_clone_v1` implementation**. The previously compiled bridge was for the old source clone; **not** a drop-in replacement for this exact running lib.so.

## Exact conclusion and next action

The user supplied the correct live binary, but a reliable *functional* Diamond replacement cannot be built just by re-linking the February archived source because it would lose the current EventPass recovery system. Further, the existing Diamond native bridge is only verified against **synthetic** account 900001, fake inventory and SQL Server shadow test schema. No actual WorldSvr-backed WExp/inventory/DB atomic commit or v291 Diamond response serializer has yet been implemented.

**Do not overwrite /usr/lib/cabal/lib.so with the archive-built Diamond .so; no live deploy yet.** Recovery copy is verified, but restoring a .so would not undo failed player-data updates.

Find the matching current source tree with read-only source search on the VM (SSH through host OS; Docker CLI may hang). A useful source file is `ProcSystem.cpp` containing `VerifyRuntimeSignatures` and `OnEventPassClaimDryRun`; its companion `OnEventPass.cpp` should contain `EventPassRelogReplayV282`. If available, patch *that* project and rebuild in an isolated source tree. If source is unavailable, a binary-only interposer needs independent compatibility/reentrancy tests; it cannot magically provide missing inventory/SQL/response semantics.

*The actual uploaded lib.so was analyzed locally. No modifications to the active VM were made.*
