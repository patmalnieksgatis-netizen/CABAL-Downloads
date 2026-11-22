# CABAL v291 — ProcSystem → DiamondWorldBridge binding (ISOLATED CLONE)

## Exact delivered result

The archived lib.so source's C2S hook, `ProcSystem::DoProcessDataCtx`, now **calls** `DiamondBoundIngress::Process(pUserCtx,cpPacket,iLen)` for a candidate 0x09F3 Diamond Mastery packet (ID 159–474). The source-copy patch is generated via `Apply-DiamondBoundClone.py`, which first applies the existing SHA-locked passive ingress patch, then injects the new binding. **Every packet continues into the original WorldSvr dispatcher after this call**; no custom reply or real-game purchase is implemented.

The binding can route to the already-tested chain:

```text
ProcSystem::DoProcessDataCtx (archived plugin, copy only)
   -> DiamondIngress::Inspect (C2S 0x09F3; Mastery 159..474)
   -> DiamondBoundIngress::Process
   -> TrustedResolver (HOST-supplied, exact pUserCtx / UserNum / revision)
   -> cabal_diamond_merit_shadow_route (built with DIAMOND_ENABLE_SHADOW_TRIAL)
   -> cabal_diamond_world_execute
   -> cabal_diamond_evaluate (316 real SCP Masteries)
   -> callback begin/load/commit-or-rollback (synthetic shadow data only)
   -> original WorldSvr dispatcher ALWAYS (no packet swallowed)
```

**Two independent protections:** default-build code excludes all callable Diamond native/DB operations; the test build requires both `-DDIAMOND_ENABLE_SHADOW_TRIAL` and `CABAL_DIAMOND_SHADOW_TRIAL=ISOLATED_SYNTHETIC_USER_900001_ONLY`, **plus `CABAL_DIAMOND_PASSIVE_OBSERVE=1` to enter the archived ProcSystem hook branch**, an explicitly installed one-time server `TrustedResolver`, and returned trusted UserNum exactly **900001**. Neither the revision nor the user number is taken from a C2S packet. No resolver means no operation. All Game Gold/Platinum packets go to the original server handler.

## Offline verification completed

- Used the owner's archived `CABAL_FOR_CHATGPT.zip` unpacked `lib.so` sources (not current loaded customized `lib.so`).
- Input source is SHA-pinned by both patch stages; the original source files were hash-checked unchanged after patch.
- The **actual modified** `hooks/Handlers/ProcSystem.cpp` compiled into a GCC x64 object with and without the trial macro; the only warning is the original archived unused `pCallProc`.
- Full bound C2S → trusted synthetic host → WorldBridge **with the owner's actual staged 116,812-byte SCP** passed locally: Mastery159 first level, deliberate storage failure with rollback, second level, malicious/untrusted session rejection and Gold/Platinum no-op.
- A distinct default build confirmed `DIAMOND_DEFAULT_PLUGIN_CANNOT_WRITE=PASS` even when the trial env var is present.
- GitHub Windows? **No**: GitHub **Linux x64** CI compiles the native C++ synthetic-catalog bind test and verifies patcher refusal of unknown source. PASS: https://github.com/patmalnieksgatis-netizen/CABAL-Downloads/actions/runs/45007359041 .

## Apply to a SOURCE COPY, never active game

```sh
python3 Apply-DiamondBoundClone.py \
  --source /path/to/archived-unmodified-lib-source \
  --output /path/to/new-isolated-Diamond-clone-source
cd /path/to/new-isolated-Diamond-clone-source
g++ -std=c++17 -fPIC -Iinclude -c hooks/Handlers/ProcSystem.cpp -o /tmp/ProcSystem_BoundDefault.o
```

The patcher refuses any original source that differs from the archived two-file SHA, existing output paths, overlaps, and changed passive-stage hashes. It does not compile/install into running WorldSvr.

The default object calls only a **nonwriting** inline gate. For synthetic offline clone proof, also compile the object with `-DDIAMOND_ENABLE_SHADOW_TRIAL` and **link** the `diamond_merit_world_entry.cpp` built with the same macro and the existing `libDiamondNative.so`. The only exported bind symbol in this deliberately dangerous TEST-ONLY build is:

```cpp
extern "C" int cabal_diamond_proc_bind_shadow_clone_v1(
    const DiamondBoundIngress::Binding*);
```

The **host must explicitly supply a verified `TrustedResolver`** and WorldBridge callbacks. The archived plugin has *no trusted current WorldSvr UserNum resolver*. Do not stub it with client packet fields or an unchecked cast to a presumed UserContext layout.

## What does NOT work in the real game yet

This is an actual source-level, native API linkage **on an archived plugin source copy**. It is not installed into the current modified WorldSvr extension, and no authentic client grade-2 packet or client reply ABI has been observed. There is no verified game inventory/WExp/SQL atomic adapter; earlier SQL Server ODBC code intentionally commits only to `Server01_DiamondLab` shadow tables.

Also: there is no independently verified per-command replay/idempotency token in the current 0x09F3 packet. When a host supplies a *fresh* revision for two identical requests, two Mastery levels may be purchased. That makes the existing packet **unsafe for a live purchase hook** until client packet semantics, duplicate suppression, and actual WorldSvr atomic persistence/response behavior are proved.

**Do not deploy `libDiamondNative.so`, `libDiamondMeritGate.so`, or this patched `lib.so` to the active game.** Reconcile the patch with exact currently loaded custom source in an isolated VM, verify the real session resolver and packet behavior, then complete response/SQL/inventory integration. Preserving working Gold, Platinum, Costume and dungeons takes priority.

## Files

- [Binding header](./DiamondBoundIngress.h)
- [Two-stage copy-only patcher](./Apply-DiamondBoundClone.py)
- [Synthetic WorldBridge linked C++ integration test](./tests/test_diamond_bound_bridge.cpp)
- [Default/no-write test](./tests/test_diamond_bound_default.cpp)
- [Native MeritWorld gate](../native/diamond_merit_world_entry.cpp)
- [Native WorldBridge API](../native/diamond_world_bridge.h)

This stage is complete as an **offline source link**, not playable Diamond.
