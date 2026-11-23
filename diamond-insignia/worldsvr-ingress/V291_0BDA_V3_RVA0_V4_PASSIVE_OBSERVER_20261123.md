# CABAL v291 Diamond — actual v3 ABI result and v4 passive observer

**Owner VM:** EP36_291_TEST, 2026-11-23. **Game deployment:** none.

## Actual v3 offline ELF measurements

SHA-pinned source v14 manifest:
`2efba153ae4d7bfcbeee2203f7b7d7a47f0a5686e31dc20dd8638ca7ac3947c2`.

- **Original live lib.so** (read-only baseline copy):
  SHA256 `6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab`,
  144 exported symbols.
- **Unmodified source rebuild:** 33 C++ files, 147 exports,
  SHA256 `702832acabab93835d2b0489f2957e7ebaeb3d4a5b18d7eb82e501fe1e3a1782`.
- **Minimal passive 0BDA source rebuild:** 33 C++ files, zero
  exported function RVA moves versus reconstructed original, zero
  newly missing export names. SHA256
  `7745cad9246488df7a48b7611a1057dc19ae4713c35fc253c81aa20e5d929cba`.
- **Full v14 Diamond source rebuild:** 34 C++ files, 142 exported
  function RVA moves versus reconstructed original, 138 versus live,
  153 exported symbols. SHA256
  `d8f366cd36d118b032712bc31cd02c92562629444b4d66fd0f0762eb2bf50074`.
- Both source builds lack the *same* weak
  `_ZNSt6vectorIPvSaIS0_EE17_M_realloc_appendIJRKS0_EEEvDpOT_`
  symbol relative to the live library. No strong ABI exports lost;
  no **new** missing exports due to the hook.
- **Strict original live exported-symbol parity remains FALSE**,
  including the minimal build. This is a blocker, not a waived check.
- Actual active WorldSvr, Supervisor, SQL and client were NOT modified.

## Key conclusion

**Zero function RVA changes is not evidence of a working hook.**
The minimal port's `Process()` is defined inline to always return
`false`, and the original dispatch occurs regardless. An optimizing
compiler can eliminate the entire branch: this is the leading,
**not yet ELF-disassembly-confirmed**, explanation for the 0-RVA result.

The 142-RVA drift cannot currently be assigned exclusively to the
34th source file: the full patch also includes independent 0x09F3
observation and other source changes. To isolate it, test a new
observable passive 0BDA counter built from the 33-file minimal source.

## v4 implementation in GitHub

`Build-DiamondV14Real0BDAOffline.py` now builds **four**
isolated, never-installable ELF objects under fresh /tmp:

1. untouched reconstructed original v14 (33 .cpp)
2. inline no-op 0BDA branch (33 .cpp)
3. **observable read-only 0BDA hit counter** (33 .cpp)
4. full Diamond v14 clone (34 .cpp)

The observer uses a GCC atomic increment ONLY for strict 0x0BDA packet
candidates. It exposes a read-only getter
`cabal_diamond_0bda_passive_hits_v1()`. It does not store any
player identifiers, packets, WarExp or inventory; it never consumes a
packet or sends a client reply, and the original native dispatcher
always runs.

The builder uses actual `objdump` disassembly to require the
observer's `ProcSystem::DoProcessDataCtx` bytes DIFFER from the
unmodified function, and requires the exact getter symbol export.
It also preserves all baseline strong exports and reports the
observer-induced exported-function RVA moves.

**This v4 instrumented ELF has NOT been compiled in the user's VM yet.
GitHub CI tests the builder and synthetic disassembly extraction only.**

## Next action

`Resume-DiamondV14-0BDA-ABI-Windows.ps1` was updated to pin the v4
builder and a fresh `/tmp/cabal_diamond_v291_0bda_offline_build_20261123_v4`
output directory. It reuses the previously transferred source tree.

Inspect especially:
- `observer_dispatch_bytes_differ_from_original` (must be true)
- `observer_rva_moves_vs_rebuilt_original`
- `observer_newly_lost_exports` (must be empty)
- `observer_missing_strong_exports` (must be empty)
- `can_install_on_active_worldsvr` (must still be false).

**Do not replace live lib.so based on these checks.**
Until the native memory save barrier, grade persistence, full
0x0BDA request/response ABI, and previous WorldSvr exit 78 causes
are resolved, in-game Diamond is NOT functional.
