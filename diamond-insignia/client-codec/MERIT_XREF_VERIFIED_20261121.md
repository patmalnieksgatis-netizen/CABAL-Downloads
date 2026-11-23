# Diamond Merit x86/x64 code references — verified 2026-11-21

Source: user-uploaded `CABAL_DIAMOND_MERIT_REFS_20261121-205002_a91fc2da.zip`, schema 2 `READ_ONLY_PE_MERIT_REFERENCE_AUDIT`. Both exact v291 CabalMain SHA-256 checksums and the v291 `meritsystem.enc` SHA are unchanged.

## Corrected count

The initial scanner reported 4 x64 and 2 x86 candidates. In x64 it counts each `REX + LEA` twice: once at the REX prefix, once at the next byte as a prefix-less overlapping instruction. **Therefore only TWO independent instructions in x64 + TWO in x86 = FOUR** real Merit filename reference sites.

## Verified static references and relative jump landings

| EXE | Filename | Reference RVA | Opcode bytes | Unconditional jump landing RVA |
| --- | --- | --- | --- | --- |
| x64 | meritsystem.enc | `0x21C4A5` | `48 8D 15 BC 29 94 00` | `0x21C20A` |
| x64 | meritsystem_msg.enc | `0x21C564` | `4C 8D 0D 0D 29 94 00` | `0x21C37C` |
| x86 | meritsystem.enc | `0x1BCA96` | `68 9C F0 C4 00` | `0x1BCE38` |
| x86 | meritsystem_msg.enc | `0x1BCAA2` | `68 AC F0 C4 00` | `0x1BCE38` |

Verified by independently decoding displacement bytes in the uploaded 128-byte windows and checking targets lie inside executable PE `.text` sections. x86 both filenames branch to the **same** RVA `0x1BCE38`; x64 references have different immediate branch targets. Their containing logic resembles a shared filename/resource selector; no decoder algorithm, XOR key, client Diamond functionality or network packet ABI has been established.

## Next test gate

Prepared conversation artifact `CABAL_DIAMOND_MERIT_DISPATCH_V3_BUNDLE.zip`, SHA-256 `8b57944390729b14ea5d25f7ef8df3e53e19ec64907e3e5ba545cdf52d5192f4`.

Standalone PowerShell `Inspect-Cabal291-MeritDispatch-V3.ps1`, SHA-256 `80a3b77f20c4c7445c3cdb27b56eca98ded1c820779186c8e83a2eba7bed7d59`.

The V3 utility parses the exact hash-pinned v291 PE files, verifies the four source instruction opcodes, calculates immediate JMP destinations, takes bounded executable code windows around each source/target and tries to locate x64 `.pdata` function ranges. No game execution, process memory access, SQL/VM or client writes. The script includes a synthetic PE self-test; **it has not been run on user's Windows yet**. The ZIP contains `analyze_xref_v2.py`, a verified JSON results file and **10/10 passing local tests**. All game binaries remain on the user's machine, not committed to public GitHub.

Next user command:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\Inspect-Cabal291-MeritDispatch-V3.ps1"
```
Then inspect `UPLOAD_THIS_ZIP=...CABAL_DIAMOND_MERIT_DISPATCH_V3_*.zip` to trace common loader/decoder calls. Do **not** interpret a branch address alone as a validated `.enc` decoder.

Preserve working `wolverine` Platinum, Gold, active WorldSvr and SQL. Diamond remains NOT installed; Anima Mastery follows Diamond.