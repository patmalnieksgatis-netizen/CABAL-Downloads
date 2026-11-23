# Diamond x64 V3 filename selector — verified function boundaries and case IDs

Evidence: user-uploaded `CABAL_DIAMOND_MERIT_DISPATCH_V3_20261121-212022.zip`. Reviewed *only the active x64* record. Source executable SHA `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`; ENC SHA `3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a`. Verified `schema=3` read-only flags, exact x64 LEA bytes, both E9 displacements and `.pdata` function range.

## Key result

**Both Merit filename references are branches inside a single x64 function RVA `0x21BB98` to `0x21CBD2` (4,154 bytes).** Code layout resembles a resource filename/string selection routine, *not* the actual ENC decryptor.

| Resource | Selector ID | LEA site | E9 landing |
| --- | --- | --- | --- |
| `meritsystem.enc` | 52 (`0x34`) | `0x21C4A5` | `0x21C20A` |
| `meritsystem_msg.enc` | 53 (`0x35`) | `0x21C564` | `0x21C37C` |

At RVA `0x21C21E`, x64 `cmp r8d,0x34` selects the first case. At RVA `0x21C4C1`, `sub r8d,0x35` is part of the selector for the second. At the message landing `0x21C37C`, `mov edx,0x13` loads length 19 for the message filename. Other switch cases use the same string construction machinery. These **52/53 resource IDs are not CABAL opcode numbers or mastery IDs**.

Neither `.enc` decode nor Diamond packet opcode is established. Do not modify the selector function or transplant EP45 `.enc`.

## New V4 x64 caller evidence collector

`diamond-insignia/client-codec/Inspect-Cabal291-MeritCaller-V4.ps1` is committed on the Diamond branch. Uses only x64 CabalMain (no x86), verifies its exact SHA and ENC SHA, extracts the previously verified 4,154-byte selector function, and searches executable bytes for raw `E8/E9 rel32` branches to selector RVA `0x21BB98`. Each candidate is annotated with enclosing `.pdata` function boundaries and a limited instruction context (up to 120 exported). `E8/E9` byte hits remain **candidates** until validated as actual instruction boundaries; no positive match is fabricated.

The built-in C# helper and its synthetic E8/E9/PDATA unit checks are tested using **Windows PowerShell 5.1 on actual GitHub Windows runner**, PASS:
https://github.com/patmalnieksgatis-netizen/CABAL-Downloads/actions/runs/44940866262

V4 not run yet on the user's x64 files. User can run:
```powershell
$u='https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/feature/diamond-insignia-v291-20261121/diamond-insignia/client-codec/Inspect-Cabal291-MeritCaller-V4.ps1'; $p="$env:USERPROFILE\Downloads\Inspect-Cabal291-MeritCaller-V4.ps1"; Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $p -ErrorAction Stop; powershell -NoProfile -ExecutionPolicy Bypass -File $p
```

Attach only the `UPLOAD_THIS_ZIP=...CABAL_DIAMOND_MERIT_X64_CALLERS_V4_*.zip` output to trace actual loader callers. Does not run CABAL, read memory, modify client/server/SQL/Platinum, or upload original executable.

Next proof gate: validate the actual call instructions and caller function logic. If no direct CALL/JMP sites, investigate indirect references rather than declaring a missing loader.

Do not conflate this resource selector with Diamond game logic. The active WorldSvr still has no proven Diamond handler; Diamond remains NOT INSTALLED.