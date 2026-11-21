# CABAL v291 x64 Diamond — V4 caller analysis, source verified

**Input:** User-uploaded `CABAL_DIAMOND_MERIT_X64_CALLERS_V4_20261121-212827.zip`, schema 4, `READ_ONLY_X64_FILENAME_SELECTOR_CALLER_AUDIT`. Original EXE SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`; Merit ENC SHA256 `3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a`.

All **six** raw E8 rel32 call candidates to the filename selector `0x21BB98` were independently recomputed and verified to be **true instruction-aligned calls**, disassembling contiguous user-provided code snippets from actual x64 `.pdata` function starts.

| Site | Source function `.pdata` | Interpretation |
|---|---|---|
| `0x21CC08` | `0x21CBD4–0x21CDA4` | Calls filename selector before additional path/resource processing |
| `0x40E1FF` | `0x40E184–0x40E56D` | Diagnostic/message formatting branch |
| `0x40E2F5` | `0x40E184–0x40E56D` | Diagnostic/message formatting branch |
| `0x40E3F4` | `0x40E184–0x40E56D` | Diagnostic/message formatting branch |
| `0x40E471` | `0x40E184–0x40E56D` | Diagnostic/message formatting branch |
| `0x40E4E4` | `0x40E184–0x40E56D` | Diagnostic/message formatting branch |

Key new path: `0x21CBD4` contains, in verified source bytes, `0x21CC08: call 0x21BB98`, `0x21CC2A: call 0x21D938` and `0x21CC90: call qword ptr [rip+0x915d62]` (resolved IAT-like address `0xB329F8`; **import name unverified**). The latter two deserve actual function tracing before declaring an ENC decode routine. The larger `0x40E184` function repeatedly formats file-name-dependent messages and follows an output/diagnostic branch; it is **not proof of actual decryption**.

**No codec, Diamond opcode, SQL persistence or working Diamond game feature has been demonstrated.** Active client only x64; x86 is not in scope. Do not transplant EP45 merit ENC. Platinum for wolverine remains intact.

### Next implemented x64-only read-only audit

`diamond-insignia/client-codec/Inspect-Cabal291-MeritLoader-V5.ps1` extracts SHA-pinned full `0x21CBD4–0x21CDA4` function and actual `.pdata` range of `0x21D938`; finds bounded E8/E9 caller candidates to both, with explicit instruction-boundary review still needed. CI **Windows PowerShell 5.1 native compile + positive/negative synthetic x64 call and PDATA tests PASS**:

https://github.com/patmalnieksgatis-netizen/CABAL-Downloads/actions/runs/44941572864

No execution against owner's game files yet. The script is the next narrowly scoped source collection, and it makes no live client/VM/SQL changes.
