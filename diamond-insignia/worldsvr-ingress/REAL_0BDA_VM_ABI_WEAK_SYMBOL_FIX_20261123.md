# EP36_291_TEST v14 0BDA offline build: actual owner result and ABI recovery

Observed by owner on 2026-11-23 from first Windows staging wrapper:

    DIAMOND_EXACT_V14_SOURCE_CLONE_PATCH=PASS
    DIAMOND_V14_REAL0BDA_SOURCE_HOOK=CONNECTED_OFFLINE
    ORIGINAL_DISPATCH_PASSTHROUGH=YES
    BINDER_ENABLED=NO
    DIAMOND_WORLD_0BDA_SOURCE_COMPILE_OFFLINE_ONLY=STOP:
      exported ABI loss:
      _ZNSt6vectorIPvSaIS0_EE17_M_realloc_appendIJRKS0_EEEvDpOT_
    STOP: build failed, live WorldSvr/lib.so unchanged

The observed name is a C++ std::vector<void*> template instantiation,
a weak compiler-generated symbol, not an identified CABAL gameplay
function. Its absence alone DOES NOT prove that the new 0BDA hook
dropped an app ABI, but we also CANNOT simply ignore the missing
weak export. It may be due to compiler settings/link ordering or
the source change's optimization effects.

## Fix to the diagnosis, not a blind ABI bypass

Build-DiamondV14Real0BDAOffline.py was changed to compile BOTH

1. unmodified, hash-pinned original v14 source under the CURRENT
   VM compiler, into a non-game reconstructed-original SONAME;
2. cloned, patched original source with the 0BDA hook, into another
   NON-installable SONAME.

The script compares **three** exports inventories:
- original SHA-pinned active lib.so *backup*,
- same-toolchain reconstructed untouched v14,
- same-toolchain v14 with 0BDA hook.

It reports whether the missing std::vector weak symbol is already absent
in the unpatched reconstruction. Only that exact historically observed
weak symbol is classified as a known reconstruction/toolchain difference.
All strong exported symbol losses and NEW symbol losses attributable
to the 0BDA hook are STOP conditions. Even a known weak drift yields
strict_live_export_parity=false and explicitly
can_install_on_active_worldsvr=false.

It also counts exported function address shifts (old-vs-unpatched,
unpatched-vs-0BDA). Function RVA shifts are a possible risk to
pre-existing plugins that use hard-coded function addresses.

## Fast rerun without retransmitting the 221-source-file archive

Resume-DiamondV14-0BDA-ABI-Windows.ps1:
- targets only EP36_291_TEST at 192.168.56.101 with exact host check;
- downloads the PINNED revised builder source;
- pipes the source through ONE SSH connection into the existing
  /tmp/cabal_diamond_v291_0bda_source_20261123 source staging;
- does not duplicate or rewrite the 221 already staged files;
- creates a new output under
  /tmp/cabal_diamond_v291_0bda_offline_build_20261123_v2;
- prints full JSON report to the Windows console, no separate upload
  needed if the console output is pasted.

No WorldSvr restart, LD_PRELOAD, Supervisor or live lib.so/SQL write.
This deliberately remains an offline binary compatibility diagnostic.
It does NOT enable playable Diamond.

## What the report will tell us

- If the weak symbol is absent from BOTH new binaries, it's a
  current-toolchain reconstruction difference, not caused by 0BDA.
  Exact live ABI parity is still false, so no live installation.
- If the symbol is in unchanged v14 but absent after adding 0BDA,
  the hook/code optimization has removed a weak symbol: this is
  a newly introduced exported-name loss and must be addressed.
- If *any* strong original export disappears, stop unconditionally.
- If the source hook shifts function addresses, compare these against
  the WorldSvr/plugin hard-coded call sites before deploying any .so.
- Actual WorldSvr memory and cmd46/47 saving, v291 grade-state
  and S2C reply ABI are still unresolved. Green CI is NOT
  evidence of working in-game Diamond.

The source and Windows wrapper AST pass GitHub CI, but the dual
private-source build cannot run in CI; only owner VM can supply
actual source-matched results.
