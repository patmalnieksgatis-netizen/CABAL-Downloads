# CABAL v291 x64 Merit / Diamond — V6 owner-run outcome (2026-11-22)

**Evidence status:** this note is grounded **only in the PowerShell stdout pasted by the owner**, not in the ZIP's JSON or extracted code bytes. The ZIP `CABAL_DIAMOND_MERIT_X64_V6_20261122-092848.zip` was generated on the owner's Windows computer but **has not yet been supplied for independent disassembly**. Do not label conclusions about V6's function bodies as verified until its report is inspected.

## Command provenance and safety

Script: `diamond-insignia/client-codec/Inspect-Cabal291-MeritResource-V6.ps1` from SHA-pinned commit `7332fca9bbbad0ee1e52e766356e893e65790062`. Windows synthetic test reports `MERIT_X64_V6_WINDOWS_SELF_TEST=PASS`. Actual run reports `READ_ONLY_STATIC`, x64, `F:\CABAL_291_TEST`, `GAME_LAUNCHED=NO`, `PROCESS_MEMORY=NO`, `SQL_OR_VM=NO`, `CLIENT_EDIT=NO`, `CLIENT_AND_SERVER_UNMODIFIED=YES`.

The script checks the same pinned source binary + ENC SHA256 as V5, and emits PDATA-bounded function source bytes or limited fallback windows into the JSON ZIP. These checks are script design assertions; the stdout does not display the actual SHA values.

## 10 exported source contexts

All ten listed targets returned PDATA-bounded ranges; every range is below the script's 8192-byte full leading-byte limit, so the script should mark each `code_complete=true` in the **pending** JSON (verify when ZIP is received).

| Analysis label (not binary symbol) | PDATA RVA begin–end | Bytes |
|---|---|---:|
| filename_selector | `0x21BB98–0x21CBD2` | 4154 |
| filename_builder_helper | `0x21B720–0x21B886` | 358 |
| false_branch_path_builder | `0x216FAC–0x217241` | 661 |
| missing_file_path_builder | `0x217244–0x217570` | 812 |
| indexed_resource_slot_callee | `0x2178E0–0x217A5C` | 380 |
| special_resource_string_callee | `0x273C8–0x27433` | 107 |
| bulk_resource_initializer | `0x21CE38–0x21D35B` | 1315 |
| indexed_path_wrapper_caller | `0x21CDA4–0x21CE36` | 146 |
| special_id_0x89_caller | `0x6828A0–0x682DB5` | 1301 |
| path_append_callee | `0x27350–0x273C5` | 117 |

## Imports independently checked by corrected V6 parser

- `IAT 0xB329F8 = SHLWAPI.dll!PathFileExistsA`
- `IAT 0xB32C28 = USER32.dll!MessageBoxA`

**Correction to V5:** its former DLL names `DINPUT8.dll!PathFileExistsA` and `DINPUT8.dll!MessageBoxA` were misleading because its import parser could walk into a different descriptor's thunk entries. V6's parser validates the descriptor membership up to the first zero thunk, and the owner-run output confirms the corrected mappings. The V5 audit document was amended accordingly.

## Remaining evidence / next action

Request the existing owner-created ZIP (no need to rerun PowerShell):
`C:\Users\patma\Downloads\CABAL_DIAMOND_MERIT_X64_V6_20261122-092848.zip`.

Upon receipt, validate the ZIP/report schema/hash and code lengths. Disassemble bounded byte arrays with verified x64 instruction alignment. Follow dataflow for resource ID `0x89` and other Merit candidates, check exact filename mapping and resource-table indexing, and distinguish filename/path selection from actual I/O/ENC decryption. Follow V5's `0x21D938` classifier only as a resource-type switch, not a codec.

**Not established:** any Merit ENC decoder, Diamond packet/opcode, persistence logic, fully working Diamond feature. Do **not** transfer EP45 ENC into v291, patch live client, or change server/SQL on this evidence alone.
