# v291 WorldSvr 0BDA — 142 moved functions: isolate the linker cause

Evidence from the owner's EP36_291_TEST offline ABI audit:
- Original v291 lib.so has 144 exported names.
- Reconstructed unmodified v14: 147 exports, 33 compiled C++ files.
- Fully patched v14: 153 exports, 34 compiled C++ files.
- Strong original exports missing in patched build: 0.
- New losses caused by hook vs reconstructed: 0.
- One exact known std::vector<void*> weak template name absent from BOTH
  reconstructed unmodified v14 and patched v14.
- Compared with reconstructed same-toolchain v14, patched v14 moved 142
  exported function addresses; versus original live lib.so, 138.
- Original WorldSvr/lib.so and GameData are unchanged.

The 142 changes CANNOT reasonably all be attributed to the 0BDA branch
itself: the previous patcher also inserts 09F3 observation code and
compiles an additional translation unit (33 → 34). A linker's source/object
ordering can move code addresses even when game logic is unchanged.
This is a plausible cause, not yet established by a comparison.

The offline builder now compiles and compares THREE variants:
1. hash-pinned original v14 (33 translation units);
2. **minimal passive 0BDA source copy** (33 translation units, no extra
   Merit/Shadow C++ file, original WorldSvr fallback retained);
3. previous full Diamond v14 source copy (34 translation units).

The new JSON reports `minimal_vs_original_function_rva_moves`,
`minimal_hook_newly_lost_exports`, and both original-vs-live and
patched-vs-live comparisons. It still ALWAYS reports
`can_install_on_active_worldsvr: false`. This comparison is NOT a
permitted production install or evidence of a working 0BDA handler.

`Resume-DiamondV14-0BDA-ABI-Windows.ps1` pins the updated builder and
writes only to a fresh /tmp ..._v3 directory on the owner's VM; it uses
the existing already uploaded source staging, one SSH connection, and
does not touch active lib.so, WorldSvr, Supervisor, SQL or client.

Even if the minimum moved-function count is zero, that only says the
pass-through stub is very close to the original code. A source-only stub
can be optimized away entirely and is NOT a real Diamond rank-up. For
playable activation we still need a functional authenticated handler,
exact 0BDA request/response ABI, live WorldSvr state modification
consistent with DBAgent cmd46/47 saves, an isolated restorable clone,
and tested recovery from the earlier WorldSvr exit status 78.

CI verifies the minimal source patch without adding any .cpp, retention
of original dispatcher and fail-closed source validation. Only the
owner's private VM can run the full exact source comparison.
