# CABAL v291/EP39 Diamond Insignia — native integration contract and evidence

**Status:** Design, donor graph checks and SQL Lab V2 prepared; no native WorldSvr
Diamond handler or production client integration exists yet. Current Platinum
and Gold are not modified. After Diamond, proceed with Anima Mastery.

## Ground truth from private user uploads (no personal data committed)

- Active \`/etc/cabal/Data/MeritSystem.scp\` SHA256
  \`307fc981ec3efe66f6cc1b0606ed7d86cd9e5a6e46205769a9bb34b012464295\`.
  Contains 64 Gold + 94 Platinum masteries, zero Diamond grade 2.
- Verified EP45 \`meritsystem.enc\` SHA256
  \`74391c4317adb1dcd375de6097812f6fa57f3f52864d4f96c83c4e862de46ec1\`
  decoded to XML SHA256
  \`297078e4cff0918280c824252c4b46e5b17e15a4c57b941b75e8d9f3081c1b9e\`.
- Actual v291 \`meritsystem.enc\` SHA256
  \`3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a\`.
  Not decoded with EP45 key; **do not replace**. EP39 *may* contain built-in
  Diamond UI because Diamond debuted before EP39, but compatibility of this
  modified client has **not** been verified.
- 316 new Diamond grade 2 masteries, IDs 159–474, 1,096 mastery-level value rows,
  and 2,442 add-only native SCP rows staged *offline*. All 158 old Gold/Platinum
  Mastery Base rows byte-identical after reversing the staged additions.
  30 existing base-force value and 14 SpecialMastery value differences vs EP45
  were preserved.
- Exact donor rank-up requirements: \`upgrade_badge=2\`, \`upgrade_wexp=30000\`,
  \`upgrade_item=33554961\`, \`upgrade_count=100\`. Must validate item identity
  in live game data, not only source numeric ID.
- 4 main Diamond categories: \`11→12/13/14\`, \`15→16/17/18\`,
  \`19→20/21/22\`, \`23→24/25/26\`. There are **12 cross-category prerequisite
  edges**, the matching **12 SpecialCategory_Active edges**, and **108
  LinkedMastery_Index edges**. Linked index semantics are **unknown**:
  never assume these are bonuses, purchases, or freely stackable passives.
- The donor has 301 continuous Diamond score bands ending at 800,568 and
  15 passive-exp bands. No server-native Diamond score parser has been proven.

## Actual verified SQL Server01 catalog (2026-11-21 user audit)

Five relevant tables, 34 columns, four PKs, zero FKs/triggers, 14 named
Merit/Platinum procedures with 50 declared parameters. Both Platinum
persistence tables use \`UserNum INT\` primary keys:
\`cabal_merit_platinum_table\` has scalar score/mastery points and
\`varbinary(128/1024)\` slot/passive fields;
\`cabal_merit_platinum_mastery_table\` has \`varbinary(8000)\`.
No named Diamond table or get/set procedures found in the catalog filter.
No game account records were read.

## SQL Lab V2 (isolated DB only)

Source-controlled \`sql-lab/01...\` through \`sql-lab/07...\` include:
- separate \`cabal_merit_diamond_lab_v1\` table, \`UserNum INT\` PK,
  optimistic \`RowRevision\`, Diamond grade 2 and opaque payloads;
- \`cabal_diamond_lab_init_v1\`: Platinum badge required, creates locked
  Diamond row but **does not unlock or deduct** anything;
- \`cabal_diamond_lab_get_v1\`: retrieves that one user's lab state;
- \`cabal_diamond_lab_commit_v1\`: one-user guarded optimistic commit,
  stale/locked rows rejected; no public grants;
- transactional synthetic test with complete rollback; procedure and
  empty-table removal scripts, all forced to \`Server01_DiamondLab\`.

**Tests:** 17 local static/behavioral-model tests on full offline bundle
and 10 GitHub CI static safety tests on committed SQL text passed.
These are **not runtime SQL Server tests**. No live DB writes or WorldSvr
restarts have occurred.

## Native compatibility audit — completed read-only

CI: https://github.com/patmalnieksgatis-netizen/cabal-ep36/actions/runs/44932875548

- Exact original WorldSvr SHA256
  \`caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3\`.
- Debug symbol table gives **zero** \`Merit/Platinum/Diamond\` names; static
  code is stripped enough that handlers cannot be identified from nm alone.
- Binary contains names of existing \`OnCSCMeritPlatinum...\` handlers,
  \`MeritMastery_Base\` and Platinum score formula, but no literal Diamond
  handler or Diamond score table name.
- This basic RIP-relative LEA xref scan found no direct targets; **it does not
  reveal packet opcode IDs**. No guessed offsets are authorized.
- Archived .so modules contain at most some Platinum literals and no Diamond
  literals. The user's live extensions may differ from the archive, and only
  the prior live scan enumerated WorldSvr plus EP36CostumeMileage.so; a full
  live module set was not verified.

## Next native engineering tasks (evidence gates)

1. **Client capability probe:** read-only audit of the **actual**
   \`F:\CABAL_291_TEST\` build to determine whether Diamond UI and rank-up
   request packets already exist. Never transplant incompatible EP45 .enc.
2. **World handler route:** identify the registered Merit C2S opcode IDs,
   response structure, user session and DB transaction APIs from authenticated
   executable/extension evidence. No guessing from string offsets.
3. **Game-authoritative rules engine:** load source-verified 316 Mastery
   definitions, 12 category activations, and 108 linked edges. Check
   prerequisites/level costs, points, expiration and passive forces.
4. **Atomic rank-up:** verify max Platinum state, badge possession, WExp and
   item resources, and persist rank transition without duplicate deductions;
   server rather than client must authorize all balances.
5. **SQL adapter:** connect WorldSvr to schema-validated Diamond persistent
   state only in isolated clone, using server-side trusted calls; verify
   concurrent logins, replay/rollback, disconnect and relog.
6. **Regression suite:** preserve live Platinum progress, Gold compatibility,
   Costume, dungeons, +20 Upgrade Core and Safeguard RAM patches.
7. **Only then** controlled release with rollback. Anima Mastery follows.

No live installation or gameplay claim. The pending hard blocker is the
**actual v291 client/native Merit packet ABI**; SQL DDL alone cannot enable it.

## Continuation: real client codec gate and rules evaluator (2026-11-21)

Official EP38 patch introduced Diamond and official EP39 fixes mention its UI; the **particular user's modified v291 client remains unverified**, and EP45 .enc must not be copied over it. Sources: https://mrwormy.com/2024/04/05/cabal-online-episode-38-full-patch-notes/ and https://mrwormy.com/2024/08/01/cabal-online-episode-39-full-patch-notes/.

### Confirmed from attached exact client files

- EP45 `meritsystem.enc`: 42,290 bytes, SHA256 `74391c4317adb1dcd375de6097812f6fa57f3f52864d4f96c83c4e862de46ec1`, classic CABAL first-four-compressed-byte XOR `92 65 67 57` plus raw DEFLATE -> XML 660,148 bytes, SHA256 `297078e4cff0918280c824252c4b46e5b17e15a4c57b941b75e8d9f3081c1b9e`.
- Actual v291 `meritsystem.enc`: 41,368 bytes, SHA256 `3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a`, little-endian uncompressed size marker 663,334. **Same classic key fails**. Prior dynamic-header prefix brute force found no clean XML output, but that does NOT prove a particular alternate cipher or that all later data bytes are transformed.
- Other v291 client locale `meritsystem_msg.enc` files are distinct sources; key MAY live in actual client DLL rather than CabalMain.exe (seen in community examples). Do not guess memory offsets or use old patch addresses.

### New offline client probe and safe rule validator

Prepared conversation artifact `CABAL_DIAMOND_CLIENT_CODEC_STATIC_AUDIT.zip` SHA256 `ce11ccd9a4818fb6a659f7489abe6bc78c42966c947a5e1d454d69278cdaff2d`, containing 9 files including the exact private donor XML (for local reproducible tests only; **do not commit this XML to public GitHub**):

- `Inspect-Cabal291-MeritCodec.ps1`: read-only static SHA-gated scanner for *actual* `F:\CABAL_291_TEST` `Bin/x64` EXE/DLL; records limited byte-pattern context around Merit/Diamond/ENC/XOR candidate markers, no game process launch, binary export, account data, SQL or game file mutations. **Not yet executed on user's Windows client.**
- `analyze_static_report.py` and 4 synthetic analyzer tests, plus 4 script static safety tests: **21/21 passed locally in the final ZIP (13 donor rules, 4 report-analyzer, 4 scanner static checks)**. A pattern match is NOT proof of a working key or handler.
- `verify_enc_codec.py`: independently validates the EP45 donor classic codec and reports the v291 variant as NOT decoded by that specific codec.
- `DiamondPurchasePolicy_OFFLINE_REFERENCE.py` plus 13 tests run with private decoded EP45 XML. This is a prototype returning a proposed purchase state, **not** active WorldSvr, SQL, item handling or client packet code.

**GitHub committed policy**: `diamond-insignia/policy/diamond_purchase_policy.py` plus 11 synthetic tests and `.github/workflows/diamond-purchase-policy.yml`. CI PASS: https://github.com/patmalnieksgatis-netizen/CABAL-Downloads/actions/runs/44934771665. It enforces authoritative state, grade2, category/verified slot, exact mastery prerequisite, point cost, revision and max level. It FAILS CLOSED on all 108 LinkedMastery relationships until their semantics are proven. It does not auto-activate categories or apply bonuses.

### Immediate next gate

Use Windows PowerShell:

    powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\Inspect-Cabal291-MeritCodec.ps1"

The script creates a ZIP at `UPLOAD_THIS_ZIP=...` containing only static metadata/hit byte windows. Inspect it **before deciding whether** to obtain client module bytes, locate the true `.enc` codec or identify Diamond opcodes. No direct access to the user's private Windows client or VM exists from current connected tools; do not claim this probe has run.

Platinum (wolverine) remains user-confirmed OK. Diamond **not yet installed**. Anima Mastery after Diamond.

## 2026-11-21 20:23 client scanner report received — real results

User uploaded ZIP `CABAL_DIAMOND_CLIENT_CODEC_20261121-202322_bcd9c114.zip`. All report source hashes and scan mode passed independent local validation. 18 EXE/DLL scans. Exact x64 CabalMain SHA `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9` has `meritsystem.enc`/`meritsystem_msg.enc` two file offsets 11917416 / 11917432; x86 CabalMain SHA `7f0aa64333d5c8e1e48c1e8e8512e45b6ea91ce3efee23d8cb7dbbc63f1feb26` has two offsets 8709276 / 8709292. No complete classic XOR key, and **291 short two-byte XOR patterns are not usable codec evidence**. All six Diamond/Insignia hits in the two d3d9 DLL copies are GPU vendor names (Diamond Computer Systems, Diamond Lane Comm., Insignia Solutions): not game features. The exact v291 41,368 byte merit ENC header declares unpacked size 663,334. We cannot conclude presence or absence of Diamond UI from the text scan.

Prepared **read-only targeted PE xref auditor** `Inspect-Cabal291-MeritCodeRefs.ps1`, SHA256 `161c93bb1e2c267aa39809303dd0c6ce52c9e57ca8183c37468f52196c141f88`. It scans only both exact hash-pinned CabalMain EXEs, validates PE architecture/section bounds, locates Merit filenames, searches non-executable pointer tables and code-address references (x86 push/mov immediate and x64 RIP LEA/MOV). Produces bounded code-context metadata ZIP named `CABAL_DIAMOND_MERIT_REFS_*.zip`; no raw binary export, no process memory access, no client changes, no SQL/world restart. NOT YET RUN on user's Windows client; code xref is only a *candidate*, not proven decoder.

Conversation package `CABAL_DIAMOND_CODEC_XREF_V2_BUNDLE.zip`, SHA256 `91b58245de8d0bf240a7a2b6c9a910f65b826c1f8fe9851e93d3da4d9ed4a52e` includes the next script, JSON analysis, independent report validator and tests. **11/11 local static/unit tests passed**, but PowerShell/C# native execution is still pending.

PowerShell command: `powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\Inspect-Cabal291-MeritCodeRefs.ps1"`.

Repo includes `diamond-insignia/client-codec/REPORT_20261121_AND_NEXT_XREF.md` and `analyze_static_report_v2.py` for Codex. The **complete PowerShell scanner** is presently in the conversation artifact, not committed in the repo. Do not claim otherwise.

Until the resulting XREF ZIP is inspected, no Diamond opcode or codec has been found. Keep Platinum, Gold and current 291 WorldSvr untouched. Anima follows after Diamond.

## 2026-11-21 20:23 — Windows PowerShell Add-Type warning-as-error fixed

User ran the initial `Inspect-Cabal291-MeritCodeRefs.ps1` and the embedded C# failed to compile at an unused-variable warning: `int prefix=0,op=off,dispAt=0,instrLength=0;`. No static client analysis was performed, and no ZIP was created; this was a code compilation failure, **not** a client/server issue.

Removed the unused `prefix` and `op` locals, leaving `int dispAt=0,instrLength=0;`. Full fixed scanner **now committed** in `diamond-insignia/client-codec/Inspect-Cabal291-MeritCodeRefs.ps1`, SHA256 `bf1fd2d57a0eb133c1d1d5be790b0615f5b44bedc29a0d6a91a44850732c66ee`. Added `Compile-Test.ps1` and `.github/workflows/diamond-merit-pe-xref-compile.yml`.

**Actual Windows PowerShell 5.1 CI PASS** for embedded C# `Add-Type`, with warning handling enabled, and malformed PE negative self-test: https://github.com/patmalnieksgatis-netizen/CABAL-Downloads/actions/runs/44937118960. Output `WINDOWS_POWERSHELL_51_ADD_TYPE_COMPILE=PASS`, `PE_NEGATIVE_SMOKE=PASS`. This is a native Windows build check but still not execution on user CABAL game files.

Fixed conversation artifact `CABAL_DIAMOND_CODEC_XREF_V2_FIXED.zip`, SHA256 `c705c5e36ba55dca7c2203b9eeb4679deac6ea2b35ded181041ee4b10271f6af`. Standalone corrected PS1 has same SHA as checked-in file above. All five previous report-analysis and documentation files retained in fixed ZIP.

On user's machine save the new PS1 to `Downloads`, overwriting the old copy, then run:
`powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\Inspect-Cabal291-MeritCodeRefs.ps1"`

Expected `PE_PARSER_NEGATIVE_TEST=PASS`, then `AUDITED=` for x64/x86 clients, and `UPLOAD_THIS_ZIP=...`. Inspect the ZIP to find actual Merit-loader code reference candidates. This does **not** identify the native packet codec or install Diamond. No production WorldSvr, SQL, game files or Platinum data touched.

## Continuation: 2026-11-21 20:50, user uploaded actual Merit PE xref ZIP

Uploaded ZIP `CABAL_DIAMOND_MERIT_REFS_20261121-205002_a91fc2da.zip` was parsed and independently verified (exact source EXE + ENC SHA pinned, source `schema=2`, read-only safety flags). The V2 scan's `code_xref_candidates=4` x64 count is inflated by one-byte overlapping RE​X and prefix-less hits: **x64 has only 2 distinct reference instructions**, x86 has 2, **4 total**. No pointer-table hits in either executable.

Instruction sites and immediate branch landings:
- x64 `meritsystem.enc`: LEA RIP-relative RVA `0x21C4A5`, E9 -> RVA `0x21C20A`.
- x64 `meritsystem_msg.enc`: LEA RIP-relative RVA `0x21C564`, E9 -> RVA `0x21C37C`.
- x86 `meritsystem.enc`: PUSH absolute VA RVA `0x1BCA96`, E9 -> RVA `0x1BCE38`.
- x86 `meritsystem_msg.enc`: PUSH absolute VA RVA `0x1BCAA2`, E9 -> same RVA `0x1BCE38`.

All source instructions re-decoded from bounded `BytesAroundInstructionHex`; RIP-relative/absolute targets match exact Merit string RVAs. All E9 destinations are inside executable `.text` sections. This demonstrates a **candidate resource/file dispatch table**, not a proven `.enc` decryptor or Diamond opcode, and it says nothing about Diamond UI capability. Verified analyzer `analyze_xref_v2.py` and 10/10 local mutation tests in user conversation artifact.

Committed technical report: `diamond-insignia/client-codec/MERIT_XREF_VERIFIED_20261121.md`.

### Next probe

Committed read-only Windows PowerShell V3 `diamond-insignia/client-codec/Inspect-Cabal291-MeritDispatch-V3.ps1`, with SHA-256-locked EXEs and four exact opcode signatures. It samples bounded windows around the four instruction sites and **three** distinct branch destinations; obtains x64 `.pdata` function boundary hints. Does not run game, copy EXEs, access SQL/VM/process memory, or modify files. Has a synthetic `-SelfTestOnly` test gate.

Windows PowerShell 5.1 GitHub CI **PASS** for V3 synthetic jump/context tests: https://github.com/patmalnieksgatis-netizen/CABAL-Downloads/actions/runs/44938288553 . This does NOT prove successful execution against the user's actual CABAL client yet.

User can download the **committed CI-checked** PS1 from the GitHub branch; run:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\Inspect-Cabal291-MeritDispatch-V3.ps1"
```
Output `UPLOAD_THIS_ZIP=...CABAL_DIAMOND_MERIT_DISPATCH_V3_*.zip`; inspect code windows at branch targets, identify the enclosing loader/decompressor call if possible, then determine target v291 Merit codec. No native install until proven. Keep `wolverine` Platinum intact.

## 2026-11-21 21:20 — Active CABAL client is x64 ONLY (user correction)

The user explicitly clarified that the **active / supported CABAL build for this project is x64 only**. The same Windows V3 run reported both x64 and x86 because old x86 files happen to remain on disk. **Never treat x86 references or ABI as production targets.**

User successfully ran original V3, with `MERIT_V3_POWERSHELL_SELF_TEST=PASS` and the exact x64 refs:
- `meritsystem.enc` branch RVA `0x21C20A`
- `meritsystem_msg.enc` branch RVA `0x21C37C`

V3 produced `CABAL_DIAMOND_MERIT_DISPATCH_V3_20261121-212022.zip` locally on user's Windows under Downloads. **User has not yet attached this V3 archive in this turn**, so the branch-landing code snippets are not available for analysis here. **No new scan needed**: original ZIP already contains both x64 code windows. Ask only for that generated ZIP to continue. Do not infer decoder or native opcode from console summary.

The committed V3 script `diamond-insignia/client-codec/Inspect-Cabal291-MeritDispatch-V3.ps1` was adjusted to **x64-only**, with `independent_sites=2`, and no `Bin\x86\CabalMain.exe` dependency for future use. This is a future quality fix, not a reason to rerun the successful user scan. Prior full x64/x86 source probes were research references only.

Preserve live Platinum for account `wolverine`; no active server/SQL/client writes. Diamond still not installed.

## 2026-11-21 21:20 V3 ZIP inspected — x64 Merit resource string selector found

The user attached their successful V3 branch-window ZIP. It contains exactly 2 x64 source references and 2 x64 branch landings, all inside one `.pdata` function `0x21BB98–0x21CBD2` (4,154 bytes). Opcode and displacement bytes were independently re-decoded from the uploaded `bytes_hex`. This is **not a decoder**.

Case `r8d=0x34` (52) selects `meritsystem.enc`, LEA `0x21C4A5` -> landing `0x21C20A`; case `r8d=0x35` (53) selects `meritsystem_msg.enc`, LEA `0x21C564` -> landing `0x21C37C`. Message landing loads literal length `0x13` (19). Both are ordinary filename resource selector IDs, **not Diamond opcodes**.

Next collector is checked-in `diamond-insignia/client-codec/Inspect-Cabal291-MeritCaller-V4.ps1`. Exact SHA gates the **x64-only** `CabalMain.exe` plus v291 Merit ENC; scans raw E8/E9 relative candidate references to function entry `0x21BB98`, reports bounded caller windows and enclosing `.pdata` function bounds, captures 4,154-byte selector body, does not alter any CABAL data. Windows PowerShell 5.1 C# compilation and synthetic call/jmp/pdata checks **PASS** in https://github.com/patmalnieksgatis-netizen/CABAL-Downloads/actions/runs/44940866262. **V4 still not executed on user's actual client**.

One-line Windows command to download the exact repo source and run without x86:
`$u='https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/feature/diamond-insignia-v291-20261121/diamond-insignia/client-codec/Inspect-Cabal291-MeritCaller-V4.ps1'; $p="$env:USERPROFILE\Downloads\Inspect-Cabal291-MeritCaller-V4.ps1"; Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $p -ErrorAction Stop; powershell -NoProfile -ExecutionPolicy Bypass -File $p`

The produced ZIP `CABAL_DIAMOND_MERIT_X64_CALLERS_V4_*.zip` is needed to advance caller graph; no further broad EXE/DLL scans. If there are zero direct candidates, don't claim absence; find indirect calls. No live WorldSvr/SQL/client change; Platinum wolverine preserved, Diamond not yet operational.

## 2026-11-21 21:28 — x64 Merit V4 caller collector executed successfully

User ran the committed `Inspect-Cabal291-MeritCaller-V4.ps1` against the active `F:\CABAL_291_TEST` client. Output:

```text
MERIT_X64_CALLER_V4_WINDOWS_SELF_TEST=PASS
CABAL_DIAMOND_MERIT_X64_CALLER_V4=READ_ONLY_STATIC
ACTIVE_ARCHITECTURE=x64;GAME_RUN=NO;SQL_OR_VM=NO;CLIENT_EDIT=NO
DIRECT_E8_OR_E9_CANDIDATE_COUNT=6
SELECTOR_FULL_BODY_BYTES=4154
EXPORTED_CALLER_CONTEXTS=6
UPLOAD_THIS_ZIP=C:\Users\patma\Downloads\CABAL_DIAMOND_MERIT_X64_CALLERS_V4_20261121-212827.zip
CLIENT_AND_SERVER_UNMODIFIED=YES
```

**Interpretation:** six RAW E8/E9 rel32 byte-pattern candidates to selector RVA `0x21BB98`, not yet six validated instruction-boundary callers, nor the ENC decoder/ Diamond packet handler. The collector exported all six bounded code contexts and the 4,154-byte selector body. Its on-device smoke test passed and the game/server remained unchanged.

**Immediate next input is the already-generated ZIP above. Do not ask for another scan.** Once attached, parse `MERIT_X64_CALLER_V4_REPORT.json`, decode candidate branch instructions and inspect enclosing `.pdata` ranges; discard bytes inside other instructions, map real caller flow to file IO/decode code if evidence permits. Keep investigation x64 only. Do not change live WorldSvr, SQL, active client, or Platinum account wolverine.

## 2026-11-21 21:28 V4 ZIP analyzed, exact x64 function callers proven

User supplied `CABAL_DIAMOND_MERIT_X64_CALLERS_V4_20261121-212827.zip`. This is schema 4 read-only, active only x64. Both EXE and v291 Merit ENC hashes match expected. The 6 reported E8 calls were revalidated by reconstructing overlapping windows, recomputing rel32 destinations to `0x21BB98`, and disassembling code from known `.pdata` entry points: **ALL SIX are real instruction-aligned call sites** (unlike the prior V2 duplicate REX matching).

Calls grouped by enclosing x64 function:

- `0x21CC08` in `.pdata 0x21CBD4–0x21CDA4` (one call). The same function contains `0x21CC2A: call 0x21D938` (new helper target), and `0x21CC90: call qword ptr [rip+0x915d62]`, resolving to IAT-like slot RVA `0xB329F8`. No claim yet about import name or actual ENC decryption.
- `0x40E1FF`, `0x40E2F5`, `0x40E3F4`, `0x40E471`, `0x40E4E4` all in `.pdata 0x40E184–0x40E56D`. This large function repeatedly feeds selected filename into formatting routine `0x289A8` and diagnostic output paths. Likely diagnostics/message formatting rather than the primary decoder. *Exact semantics not proven*.

Full owner-facing analysis `/mnt/data/CABAL_DIAMOND_V4_X64_CALLER_ANALYSIS.md` was created and GitHub summary saved at `diamond-insignia/client-codec/V4_X64_CALLERS_VERIFIED_AND_V5_GATE.md`.

**Next CI-passed x64 V5 collector:** `diamond-insignia/client-codec/Inspect-Cabal291-MeritLoader-V5.ps1`, pinned to exact CABAL v291 x64 EXE and ENC SHA. It extracts full `.pdata` body of the selector wrapper (`0x21CBD4–0x21CDA4`) and the dynamically discovered `.pdata` body containing direct callee `0x21D938`, and finds relative E8/E9 candidates to both. It additionally parses native PE x64 import descriptors/IAT to try resolving exact slots `0xB329F8` (suspected file-related) and `0xB32C28` (diagnostic path). Unknown entries remain explicitly `UNRESOLVED`, rather than making up an API name. All data read-only; no x86, no live process, SQL, game patches or WorldSvr restart.

GitHub Windows PowerShell 5.1 C# compilation + synthetic positive/negative x64 caller/PDATA/PE import tests **PASS**: https://github.com/patmalnieksgatis-netizen/CABAL-Downloads/actions/runs/44941880124. The earlier CI iteration had a C# UInt64 vs Int32 type mismatch; corrected and CI now green. **The user has NOT yet executed V5** against the real CABAL executable.

One-line PowerShell (fetch checked-in code before executing):
`$u='https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/feature/diamond-insignia-v291-20261121/diamond-insignia/client-codec/Inspect-Cabal291-MeritLoader-V5.ps1'; $p="$env:USERPROFILE\Downloads\Inspect-Cabal291-MeritLoader-V5.ps1"; Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $p -ErrorAction Stop; if($?){powershell -NoProfile -ExecutionPolicy Bypass -File $p}`

Next input: `UPLOAD_THIS_ZIP=...CABAL_DIAMOND_MERIT_X64_V5_*.zip` from that one targeted x64 run. It will establish whether `0x21D938` is file IO/decoding or other; **do not describe it as a known decoder before evidence**.

Diamond is still not installed; Platinum for `wolverine` remains user-reported working and untouched.

## 2026-11-21 continuation: do more offline without rerunning user's V4

Reopened the exact user-uploaded x64 V4 ZIP in the local workspace. The relevant 0x21CBD4 wrapper code from its source function entry was disassembled again with `objdump`. The confirmed instruction sequence calls the filename selector `0x21BB98` at `0x21CC08`, sets a destination string, calls helper `0x21D938` at `0x21CC2A`, checks boolean `AL`, and conditionally calls an IAT-like function at `0x21CC90` whose name remains unknown. The code strongly suggests a path/resource handling chain, **NOT a proven raw-deflate, XOR or file-decode routine**. There is no basis to patch or replace `meritsystem.enc` yet.

Five V4 call contexts are distributed through the complete .pdata diagnostics function `0x40E184–0x40E56D`. Reassembled the function from the overlapping user-uploaded windows (1001/1001 bytes, zero mismatches). Native `objdump -M intel` confirms five instruction-aligned E8 CALLs to `0x21BB98` at `0x40E1FF`, `0x40E2F5`, `0x40E3F4`, `0x40E471`, `0x40E4E4`. All are filename formatting branches, not independent decoders. Wrapper snippet covers only its first 244 bytes of 464, so V5 remains necessary to inspect it fully.

**Important newly verified EP45 donor linked skill topology:** each of 12 Diamond subcategories has exactly **9 LinkedMastery edges**: **6 toward the group's main category + 3 within the same subcategory**, for 108 total across 4 main category groups. The relationships always point backward to existing grade-2 mastery IDs. This structure mirrors grouping; the actual effect of the link on bonuses/unlocking remains unknown and is NOT to be guessed. Source-gated reusable checker committed at `diamond-insignia/policy/linked_mastery_topology.py`; seven synthetic mutation tests at `diamond-insignia/policy/test_linked_topology.py`. **GitHub CI PASSED 18/18 tests**, combining 11 prior purchase policy and 7 new graph tests: https://github.com/patmalnieksgatis-netizen/CABAL-Downloads/actions/runs/44943222823. Private donor XML remains local and is not checked in.

Added `diamond-insignia/client-codec/analyze_v5_loader_report.py` to prevalidate next static evidence ZIP from x64 V5 (exact SHA, source call opcodes, function bounds, flags). This is preparation, not evidence that V5 ran on owner's machine.

**Only missing proof for actual code path:** user has not supplied output ZIP from the already CI-checked V5 client scanner `Inspect-Cabal291-MeritLoader-V5.ps1` (see prior one-line command). No need to re-run V4 or earlier x86/full-DLL scans. Owner must run V5 on their x64 executable if full native loader/helper analysis is to continue. No direct access to owner's F: drive exists in available connector tools.

Production server, client binaries, SQL, and Platinum for account wolverine remain unchanged; Diamond is staged, not installed. Anima follows Diamond.

## 2026-11-22 native engineering milestone: compiled Diamond library (NO GAME INTEGRATION)

After stopping the endless V1–V9 client codec inspection, the native implementation advanced materially:
- `native/diamond_rules.hpp`: C++17 pure Diamond rank-up and mastery level-up proposal engine.
- `native/diamond_transaction.hpp`: trusted WorldSvr session transaction bridge, with atomic/replay/rollback interface. The only working backend currently is a **test fake**, NOT actual SQL Server/WorldSvr.
- `native/diamond_catalog.hpp`: authentic `MeritSystem.scp` parser with fail-closed counts: 64 Gold, 94 Platinum, 316 Diamond masteries (IDs 159–474), 1096 Diamond level values, **four** native `SpecialMastery_Active` Diamond edges, 108 linked dependencies and grade-2 rank cost validation. Do not confuse this with the 12 EP45 client category activation links.
- `native/diamond_abi.h` and `native/diamond_abi.cpp`: versioned C ABI; builds `libDiamondNative.so`, no live binary hooks or guessed opcode; `native/test_diamond_abi.cpp` tests the compiled library against synthetic data.
- CI all native suite PASS: https://github.com/patmalnieksgatis-netizen/CABAL-Downloads/actions/runs/45001061964. Downloadable artifact `diamond-native-v291-offline-linux-x64` with 7-day retention, not a drop-in WorldSvr plugin. This CI build requires at least GLIBC_2.38; rebuild in the real target container for compatible execution.

**Real private-data milestone:** Original `MeritSystem.scp` 54,866 bytes SHA256 `307fc981ec3efe66f6cc1b0606ed7d86cd9e5a6e46205769a9bb34b012464295`; staged add-only SCP 116,812 bytes SHA256 `26c9c4cbe3136f67f0298c8e412a4aa7620ba46d62b5c3950880fe821f2ee2e5`. Independently checked same 19 sections, original Gold/Platinum rows untouched, +2442 additive rows. The *actual compiled* `libDiamondNative.so` was loaded locally with the real private staged SCP and accepted it (`engine_create=0`). Pure native tests with this exact data succeeded: rank-up from WExp=40,000/tickets=105 -> Diamond with WExp=10,000/tickets=5, revision8->9; mastery159 first-level cost=5 and revision9->10; linked mastery473 explicitly denied by unknown LinkedMastery semantics (error 13; confirmed by actual library ABI). **These are offline computations, not player account modifications or game tests.** Private SCP not committed to public repository.

**Remaining hard blocker:** the currently available `cabal-ep36` source `EP36Compat_v282 (1).c` is a send/packet translation hook, NOT the current server's authenticated Merit request handler. A working WorldSvr Diamond packet entrypoint, verified server session offsets, and real SQL+inventory atomic persistence are not yet available. Do not blindly hook packet IDs, try live LD_PRELOAD, overwrite /etc/cabal/Data/MeritSystem.scp, or claim playable Diamond. To finish: integrate the real server ABI + true SQL transaction in the isolated VM clone, verify gameplay/relogin/restart, only then deploy. Gold/Platinum must remain intact.
