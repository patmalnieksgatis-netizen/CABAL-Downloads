# CABAL Diamond v291 — v14 session-lease ABI v3 (2026-11-22)

**Status: isolated compiled source/runtime integration PASS; game deployment NOT DONE.**

## Code change

The WorldSvr clone ingress previously used a one-shot `TrustedResolver` that returned
a session pointer and revision without a guaranteed ownership lifetime. It could race
disconnects/character changes or a concurrent save. The new
`DiamondBoundIngress` **ABI 3** requires host-provided
`acquire_exclusive` and `release_exclusive` callbacks, and an RAII
`ScopedLease` keeps that lease held through
`cabal_diamond_merit_verified_shadow_route`, native evaluation and
WorldBridge commit/abort. It is released on success, rule reject,
commit failure and even an exception raised after acquiring the lease.

Old ABI 1/2 binders are refused. The explicit synthetic clone entrypoints
are `cabal_diamond_proc_bind_shadow_clone_v3` and
`cabal_diamond_proc_test_ingress_clone_v3`. Both are absent in default
builds. The v14 exact-source copy patcher and strict linker now target these
symbols, as do GitHub's C++ and dlopen smoke tests.

## Verified against the owner's actual v14 source (offline, NOT live game)

A separately copied `CABAL_V282_SOURCE_v14` source tree was rebuilt under
Linux x64 with `-DDIAMOND_ENABLE_SHADOW_TRIAL`, `-Wl,-z,defs`, native
Diamond rules and the existing EventPass implementation. The library has
the unique SONAME `libDiamondV14LeaseV3Offline.so` and is not a replacement
for the original game's `lib.so`.

- User's current `lib.so_current_v291` SHA256:
  `6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab`
- **144/144 existing defined dynamic symbol names preserved**; clone exports
  161 symbols in total. Symbol compatibility is NOT a guarantee of binary
  runtime compatibility or identical server state layout.
- Clone-only ELF SHA256:
  `6fdb75967205021bae1b19bc8a9539c5e7e4ec28589a904299d2b2cab8e837aa`
- Exact-source offline dynamic loader run: `dlopen` + `dlsym`
  successfully bound ABI-v3 and exercised a synthetic UserNum 900001.
- Two synthetic Mastery 159 purchases (levels 1 and 2) succeeded;
  malformed second payload DWORD, untrusted user and forced storage error
  never charged resources; a **throw-after-acquire** test confirmed the
  session mutex was released safely. Gold/Platinum were unchanged.
- GitHub Actions against a separate *synthetic shared-object shim* PASS:
  https://github.com/patmalnieksgatis-netizen/CABAL-Downloads/actions/runs/45064446575
  (not a substitute for the owner-source offline dlopen above).

## Not yet implemented

This lease mechanism is an **interface** awaiting a real WorldSvr
authenticated-session registry and exclusive per-session/per-character lock.
The synthetic attestor is not production-grade. The true client meaning of
both 0x09F3 payload DWORDs is not proven; the first is used to look up a
server Merit selector, so numeric ID range alone is not authorization.
The real game inventory (item 33554961), WExp, MSSQL/DBAgent durable
receipt and v291 S2C Diamond success serializer are NOT connected.

**Absolutely no active VM/WorldSvr/LD_PRELOAD/Supervisor/SQL or client
modification was made.** Do not copy the offline .so to any game directory.


## WorldSessionBridge → ingress port (later 2026-11-22)

The new `DiamondV14SessionLeasePort.h/.cpp` now connects
`DiamondBoundIngress`'s ABI-v3 callback shape to the pre-existing
`WorldSessionAuthority` and the actual `ProveWorldSessionV14` identity
validation routine. It checks the independently registered session generation,
`USERCONTEXT+0xE8` data pointer, UserNum at `USERDATACONTEXT+0x890`
and CharacterIdx at `+0xA24` **while the host owns an exclusive lease**.

A separate `MeritCatalogAuthority` still must supply the server-owned
selector and both expected 0x09F3 payload values under that same lease;
the code refuses mismatches instead of inventing packet semantics.
When the last check passes, the same owned lease spans the entire
`cabal_diamond_world_execute` commit/abort, including its failure path.

`tests/test_diamond_v14_session_lease_port.cpp` compiles the real existing
v14 identity reader and WorldSessionBridge source against an independent
synthetic registry and synthetic catalog. CI verifies forged owner/character
identities, session generation 0, swapped `+0xE8` pointer, incorrect
server catalog selection and changed packet values cannot debit points.
The test also pauses a purchase inside the commit callback and independently
confirms that a concurrent disconnect cannot acquire the registry mutex until
the commit completes.

**Boundaries remain strict:** this host port does not invent a WorldSvr
registry, login/disconnect hook, SQL/DBAgent inventory port, or client S2C
response. The current running game binary has not been modified. It is a
tested adapter to a future *real authoritative registry*, not that registry.
