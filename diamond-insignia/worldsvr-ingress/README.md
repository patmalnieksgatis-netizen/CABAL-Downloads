# CABAL v291 — WorldSvr Merit ingress integration (PASSIVE CLONE ONLY)

## Implemented

This patches a **copy of the archived WorldSvr lib.so ProcSystem source**, not the running game. It adds a **read-only packet observer** inside the existing ProcSystem::DoProcessDataCtx hook.

The observer recognizes existing C2S main command 0x09F3, classic packet magic 0xB7E2, exactly 18 input bytes, and the first payload DWORD at +0xA in the Diamond Mastery ID range 159–474. The second DWORD at +0xE remains **unknown** and is never used for authorization. Gold/Platinum requests (IDs 1–158, Platinum grade-up 0x0B10) and all other traffic are sent to the **original WorldSvr dispatcher, unchanged**. Diamond candidates ALSO go to that original handler. No new reply, SQL/ODBC, WExp, item deduction, or actual gameplay modification.

Disabled by default. On an isolated clone, set CABAL_DIAMOND_PASSIVE_OBSERVE=1 to log at most 16 candidate Mastery IDs. No account identifiers or packet data are logged.

The hook function 0xB2E0C0 and existing Merit command handler 0xA40D90 were verified against the exact WorldSvr ELF SHA256 caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3. The packet-context length at +0x10 comes from the **archived C2SHandler.cpp**, not a complete runtime ABI validation of the currently customized lib.so.

## Patch a separate source copy

The original source must have both include/Types.h and hooks/Handlers/ProcSystem.cpp with exact pinned SHA256 hashes. Any mismatch is refused, as is overwriting the original or creating a clone inside its source tree.

    python3 Apply-DiamondIngressClone.py \
      --source /path/to/extracted-original-lib-source \
      --output /path/to/new-isolated-diamond-lib-source

The patcher copies the source tree, changes exactly two files, and adds hooks/Handlers/DiamondIngress.h. It does not build, deploy, restart, inject, or copy anything into Docker. Preserve the original lib.so.

Offline compilation of the new source in the isolated tree:

    cd /path/to/new-isolated-diamond-lib-source
    g++ -std=c++17 -fPIC -Iinclude -c hooks/Handlers/ProcSystem.cpp -o /tmp/ProcSystem_DiamondIngress.o

This exact object build passed locally using the actual user archive; one unrelated pre-existing unused-function warning remains. Independent C++ tests passed for the packet gate, rate limit and default-off state.

GitHub CI workflow: https://github.com/patmalnieksgatis-netizen/CABAL-Downloads/actions/workflows/diamond-worldsvr-ingress.yml

## Isolated source-compile preflight (ABI v2)

The separate `Verify-DiamondWorldSvrSourceClone.py` compiles the exact
archived lib.so **source copy** twice and checks exported symbols:

```sh
python3 Verify-DiamondWorldSvrSourceClone.py \
  --source /path/to/unmodified-archived-libso/src \
  --output /tmp/diamond-isolated-v291-clone-build
```

It refuses an incompatible source SHA, an existing destination, missing headers,
and ABI v1. The default build must **not export any Diamond binder**; the
synthetic-only build must export `cabal_diamond_proc_bind_shadow_clone_v2`.
This is only an object-file compile preflight; it does **not** link or launch
WorldSvr, validate the user's currently loaded lib.so, connect to SQL, or
prove in-game Diamond compatibility.

The earlier bound ingress used the old numeric-ID shadow route that no longer
executes. The clone-only ABI-v2 binding instead requires host-verified session,
catalog, server Merit selector, both payload DWORDs and a matching revision.
The actual WorldSvr provider of these proofs remains unimplemented.

## Hard blocker to playable Diamond

This is an **actual C2S code insertion point** but **not a complete game feature**. The new Diamond rank-up action/reply ABI and real server-authenticated inventory/WExp+SQL transaction are not verified. The first payload DWORD under 0x09F3 is a *candidate* ID, not proof that the client already sends grade 2 actions. The prepared native rule engine, SQL Server ODBC *shadow* adapter and this patch do not yet form a production gameplay implementation.

The archived WorldSvr lib.so source may differ from the currently running customized library. Do not LD_PRELOAD this into the active WorldSvr or overwrite any working extensions. To proceed with a real test, back up a separate VM clone, verify the current source/build target and packet ABI, then test this passive observer before enabling actual Diamond transactions.

## Backout

No active client/WorldSvr/SQL changes occurred. Delete the new clone source directory and unset CABAL_DIAMOND_PASSIVE_OBSERVE. Gold and Platinum remain untouched.
