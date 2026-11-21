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
