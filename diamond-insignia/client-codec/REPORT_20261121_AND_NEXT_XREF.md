# Diamond v291 Client Codec: static report verified; next PE xref gate

## Audited source

User supplied `CABAL_DIAMOND_CLIENT_CODEC_20261121-202322_bcd9c114.zip`, containing `CLIENT_CODEC_STATIC_REPORT.json`. An offline parser independently verified report mode, two exact CabalMain SHA256 checksums and the expected v291 merit ENC hash. 18 files scanned, no game process launched or modified. No server or SQL access.

Actual 64-bit executable: `Bin\x64\CabalMain.exe`, SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`, 15,089,000 bytes. `meritsystem.enc` and `meritsystem_msg.enc` filename-table hits at file offsets 11917416 and 11917432.

Actual 32-bit executable: `Bin\x86\CabalMain.exe`, SHA256 `7f0aa64333d5c8e1e48c1e8e8512e45b6ea91ce3efee23d8cb7dbbc63f1feb26`, 10,099,560 bytes. Corresponding filename-table hits at 8709276 and 8709292.

v291 `Data\meritsystem.enc`: SHA256 `3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a`, 41,368 bytes; little-endian declared unpacked size 663,334. Classic EP45 key `92 65 67 57` failed to yield raw deflate or XML. Do not install EP45 `.enc` over v291.

The scanner recorded **291 hits of short two-byte 34 92 / 34 65 / 34 67 / 34 57 sequences**, which are not evidence that the client is decoding `.enc` with those XOR constants: most are simply incidental byte pairs. No complete classic `92 65 67 57` key literal found.

All six `Diamond`/`Insignia` text hits in the report are **false positives** in `d3d9.dll` and the byte-identical `d3d9_dxvk291_original.dll`, listing unrelated graphics vendors `Diamond Computer Systems`, `Diamond Lane Comm.`, `Insignia Solutions`. Neither CabalMain reported ASCII/UTF16 Diamond/Insignia literal. **This does not prove the Diamond UI is absent**; it may be encoded in resources or referenced numerically.

## Prepared next read-only tool

`Inspect-Cabal291-MeritCodeRefs.ps1` SHA256 `161c93bb1e2c267aa39809303dd0c6ce52c9e57ca8183c37468f52196c141f88` (in conversation artifact, not yet installed on Windows) parses PE32/PE32+ executable sections, determines RVAs/VA for Merit filename strings, searches non-executable .rdata/.data pointer tables referring to these strings, then searches candidate X86 push/mov-immediate or X64 RIP-relative LEA/MOV code references. It records only bounded code context snippets, not complete EXEs, binary patches or memory. Exact executable hashes are pinned; read-only and fail-closed.

User command once the `.ps1` is saved to Downloads:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\Inspect-Cabal291-MeritCodeRefs.ps1"
```

Output `UPLOAD_THIS_ZIP=...CABAL_DIAMOND_MERIT_REFS_*.zip`; attach that. **No xrefs verified yet.** A code xref is a candidate, not verified Merit decoder or opcode.

Offline companion `analyze_diamond_codec_report_v2.py` verified the source report and generated `CABAL_DIAMOND_CLIENT_REPORT_ANALYSIS_20261121.json` (static evidence only). Eleven local unit/static safety tests passed; the *PowerShell C# PE reference scanner has not been run on the user's Windows system*, so its actual runtime result is pending.

Complete conversation artifact `CABAL_DIAMOND_CODEC_XREF_V2_BUNDLE.zip` SHA256 `91b58245de8d0bf240a7a2b6c9a910f65b826c1f8fe9851e93d3da4d9ed4a52e`. It includes the PowerShell scanner, parser, tests, static report analysis and Latvian README. No proprietary original client bytes in it.

## Integration status

Platinum on account `wolverine` is user-reported working. Diamond cannot be installed merely by adding donor SCP or SQL: Merit `.enc` decode and native C2S opcode/WorldSvr dispatch still unproven. No live SQL/WorldSvr/client changes in this continuation. Keep prior Diamond SQL Lab V2 and 316 mastery dependency graph isolated. Anima Mastery after Diamond.
