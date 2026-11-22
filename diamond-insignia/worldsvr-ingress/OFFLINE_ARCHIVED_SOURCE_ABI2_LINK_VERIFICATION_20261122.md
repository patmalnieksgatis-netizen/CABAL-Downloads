# Archived-source Diamond ABI-v2 strict link verification (2026-11-22)

**OFFLINE ONLY.** The owner's original hash-locked WorldSvr `lib.so` extension
source was copied into an isolated working directory and upgraded to the
`DiamondBoundIngress` ABI-v2 source contract. No live WorldSvr, VM, SQL
database or client was started or modified.

Local compiler verification against the **actual archived original source**:

- Original `hooks/Handlers/ProcSystem.cpp` SHA256:
  `b687c3bb9607aa886f37bcf203dcf4fb1a315cf6e9a23d4e67adea69e1486d88`.
- Original `include/Types.h` SHA256:
  `c32a66118f439cf1a1279f703c3a9a1e272a4dfbb89a0745c93983ce5a2e3b61`.
- Source-copy patch and independent C++17 compile: **PASS** with and
  without `DIAMOND_ENABLE_SHADOW_TRIAL`.
- Default-build global Diamond binder exports: **0**.
- Explicit synthetic trial global bind export:
  `cabal_diamond_proc_bind_shadow_clone_v2`.
- Full archived source `*.cpp` plus ABI-v2 verified Merit entry and
  the owner's previously compiled offline `libDiamondNative.so` linked with
  `-Wl,-z,defs -lodbc`: **PASS**.
- Link required **`-lodbc` after the source/object arguments**; otherwise
  `SQLAllocHandle`, `SQLExecDirect`, and other legacy EventPass symbols
  remained unresolved. The new reproducible helper
  `Link-DiamondWorldSvrCloneLab.py` preserves this ordering.
- The resulting ELF is deliberately **not named `lib.so`** and identifies
  itself as `libDiamondWorldCloneOffline.so`; it exports the new native
  Merit route `cabal_diamond_merit_verified_shadow_route`.
- Local lab ELF SHA256:
  `091245d28115ea13481b662ba5741ec55b83556bcc495211d178755d0dbfe40f`.
  That checksum identifies this particular **offline compiler output**;
  changes in compiler/toolchain, source formatting or libraries can change it.
- Original/current uploaded `lib.so_current_v291` SHA256 remained
  `6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab`.

This verifies **source compilation and ELF linking only**. It does NOT
establish that the new library is compatible with the actively customized
WorldSvr, that the real game session resolver or database mutation exists,
that all Diamond client packet fields are understood, or that Rank Up /
Mastery and S2C responses function in-game.

The full archived game source and executable artifacts were **not committed**
to this public repository. All previous game features (Platinum, Costume,
Dungeons and their extensions) must remain untouched.
