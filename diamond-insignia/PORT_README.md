# Diamond Insignia: EP45 donor → v291 / EP39 target

Date: 2026-11-21. **Status: source/target preflight only; Diamond feature NOT yet ported or enabled.**

## Verified origin and comparison

Diamond Insignia is the new tier of CABAL Merit Mastery introduced in Episode 38;
v291/EP39 is likely to include some client UI, but **this must be verified on
the specific client installation**. EP45 is a donor/reference only, not a
target engine replacement.

Sources inspected without modifying either project:

1. Private \`patmalnieksgatis-netizen/CABAL-EP45\` repository inventory,
   57,851 entries for shared "CABAL Transcendence (UTS).7z":
   - \`data/meritsystem.enc\` **42,290 bytes**
   - \`data/Language/Korean/meritsystem_msg.enc\` **6,976 bytes**
   - \`data/Language/Korean/UI/help/meritmedal_01.jpg\` through \`08.jpg\`
   - \`data/honor_medal.enc\` is **not** necessarily Diamond; don't
     replace unrelated honor medal files blindly.
   - Source repository contains **no server runtime or DB**. Selected
     client files still require readback/extraction and comparison.
   - Audit: https://github.com/patmalnieksgatis-netizen/CABAL-EP45/actions/runs/44916126798
2. Archived **old EP36/v282 baseline**, SHA-pinned WorldSvr from private
   \`patmalnieksgatis-netizen/cabal-ep36\`:
   - \`home/data_main/cabal/Data/MeritSystem.scp\` includes
     \`[MeritScore_Fomula]\`, \`[MeritScore_Fomula_Platinum]\`,
     \`[MeritMastery_Base]\`, \`[MeritMastery_Value]\`.
   - Native WorldSvr already includes \`OnCSCMeritMasteryLvUp\`,
     \`DoMeritMasteryPacking\`, \`OnMeritMasteryReset\`.
   - This is **not proof** that the current customized v291 WorldSvr is
     identical, and does not establish Diamond handlers. Do not infer
     an opcode or SQL schema from this baseline.
   - Audit: https://github.com/patmalnieksgatis-netizen/cabal-ep36/actions/runs/44916163671
3. Public authoritative behavior:
   https://cabal.playthisgame.com/en/update/Content/5219
   - rank up only when Platinum Merit is maxed; 100 Merit Medal
     Exchange Tickets + 30,000 WExp
   - four Diamond main categories, three subcategories each; only one
     subcategory may be selected per main category
   - Special Mastery options, passive Diamond EXP, time reducers
   - 3 Platinum time reducers exchange for 1 Diamond reducer of same time.

## Migration contract: missing parts only

### Client
- Record exact v291 \`meritsystem.enc\` and language file SHA/size;
  decode/compare to the EP45 donor before replacing or appending.
- Identify whether v291 already has Diamond UI, event identifiers,
  icons/textures. Don't replace the whole UI or use an EP45 executable.
- Respect data/packet schema differences. Never invent opcode lengths.

### Server
- Inspect **active container** \`/etc/cabal/Data/MeritSystem.scp\` and
  exact running WorldSvr/extension module identities; compare to archived
  baseline. Old archive does NOT define current live server behavior.
- Preserve Gold/Platinum rows and indexes, points, upgrades and resets.
- Add Diamond rank-up validation, level/category prerequisites, WExp/item
  transaction, mastery purchases, mutually exclusive subcategories,
  time-reducer actions and passive recalculation **only when donor
  definitions and wire contracts are verified**.
- Database migration: require schema preflight, transaction, additive
  tables/columns, backfill defaults, rollback plan; preserve characters
  and Gold/Platinum progress. Never apply guessed SQL.
- Packet integration: capture real v291 client requests for rank-up,
  tree state, mastery upgrade/reset and passive. Preserve exact versioned
  layouts and existing player authorization checks.

### Non-regression
- Preserve working Costume, dungeons, Mileage, Cash Shop, SkillBook,
  Guardian Arcana, Warp and existing character data.
- Preserve confirmed Upgrade Core +20 plus Safeguard compatibility.
  The separate Perfect Core +17 defect is out of scope.
- Do not touch live VM or old WorldSvr until a test-only backup, baseline
  signatures, binary packet compatibility, SQL delta and rollback exist.

## Evidence still required to implement safely

- Actual v291 \`meritsystem.enc\` and active \`MeritSystem.scp\`.
- Actual EP45 \`meritsystem.enc\` bytes (inventory alone proves only
  presence; extraction can be bounded via existing Drive 7z reader).
- Evidence from active v291 WorldSvr that it has/doesn't have Diamond
  mastery handler and DB persistence.
- Verified client request/response packet samples when opening Merit UI
  and attempting Diamond rank-up on test account.
- After this preflight, implement only the missing data + server adapters
  and write acceptance tests for 4 categories, 12 subcategory choices,
  level/point caps, transactions, passive, reconnect and reboot.

## Read-only preflight

An attached \`Audit-DiamondInsignia-v291.ps1\` checks:
- local candidate v291 \`meritsystem.enc\` files (without editing)
- active Docker MeritSystem.scp rows and badge grade distribution
- writes a JSON report in local Downloads
- neither client nor VM is modified

For the working Windows host:
\`\`\`powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\Audit-DiamondInsignia-v291.ps1"
\`\`\`
Optional \`-ClientRoot 'D:\path\to\game'\` narrows the local file search
to the actual v291 client root.

**No feature files have been merged into the v291 client/server yet.**

## Active-v291 user preflight and exact next source collection (2026-11-21)

The user ran the initial read-only preflight. Active VM:
- \`/etc/cabal/Data/MeritSystem.scp\` SHA256 \`307fc981ec3efe66f6cc1b0606ed7d86cd9e5a6e46205769a9bb34b012464295\`, 54,866 bytes.
- \`[MeritMastery_Base]\` contains exactly 158 rows: Badge_Grade 0 (64 rows), Badge_Grade 1 (94 rows), **no Diamond grade**; \`[MeritMastery_Value]\` has 840 rows.
- \`Common.ini\` loads \`MeritSystem=Data/MeritSystem.scp\`.
- Archived baseline \`MeritSystem.scp\` SHA \`c32dd3aa8cd4...\`, 54,899 bytes, same Gold/Platinum grade counts. It is not identical to the active VM; **do not replace the active copy**.

Windows Downloads matches (none yet verified as the active v291 game):
- EP45 \`CABAL Transcendence (UTS)/CABAL Transcendence (UTS)/data/meritsystem.enc\`: **42,290 bytes**, SHA256 \`74391c4317adb1dcd375de6097812f6fa57f3f52864d4f96c83c4e862de46ec1\`.
- CABALOnline_20251008 \`Data/meritsystem.enc\`: 42,231 bytes, SHA256 \`eb00cfdf8e54aabeaabfbff025dc837468039b6aa0127ba8dee62b84b498855d\`. Similar size/header is not proof this is the target v291 client.
- EP275 and EP35 have older, smaller variants (26,122 and 20,205 bytes).

**Critical target root** from existing v291 project tool \`Collect-Client291-WorldDefinitions-v1_1.ps1\` is \`F:\CABAL_291_TEST\`. The original preflight scanned Downloads, hence **missed the active v291 Merit file**.

Created \`diamond-insignia/Collect-DiamondInsignia-Sources.ps1\` (SHA256 \`267c5a81a6125c64165671dfc824a67ecf457b37b1677363fd1571fed80329fd\`, 6,963 bytes), a standalone PowerShell 5.1 **read-only collector** that copies ONLY:
1. Actual \`F:\CABAL_291_TEST\Data\meritsystem.enc\` and optional Merit message files.
2. EP45 donor \`data\meritsystem.enc\` and optional Korean Merit message file.
3. Active Docker \`/etc/cabal/Data/MeritSystem.scp\` via SSH; base64 transport plus SHA256 integrity.

Writes one small \`CABAL-DIAMOND-SOURCES-<nonce>.zip\` in Windows Downloads; neither client files, VM, WorldSvr, SQL nor player records are modified. Does not substitute EP275/EP35.

\`\`\`powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\Collect-DiamondInsignia-Sources.ps1"
\`\`\`

If target v291 directory changed, pass \`-ClientRoot 'F:\real\client\path'\`. User should upload just this archive in the conversation for direct byte-level .enc inspection. This is needed before any actual port or SQL migration. No feature has been enabled yet.


### 2026-11-21 Windows collector run: six sources collected, ZIP path check false negative

The user executed \`Collect-DiamondInsignia-Sources.ps1\` in Windows PowerShell 5.1; source readback succeeded:
- v291 \`F:\CABAL_291_TEST\Data\meritsystem.enc\`: 41,368 bytes, SHA \`3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a\`.
- v291 English \`meritsystem_msg.enc\`: 9,328 bytes, SHA \`ab324be83f31ed6da63572e49bd6a4dd9c4b0edb177f190773b3109b5b0d1a16\`.
- v291 Korean \`meritsystem_msg.enc\`: 7,658 bytes, SHA \`b3b200d937823b2b17c1fd5d5735dfba0da1ef06e7ac015318f3d8fa3233a2ed\`.
- EP45 \`meritsystem.enc\`: 42,290 bytes, SHA \`74391c4317adb1dcd375de6097812f6fa57f3f52864d4f96c83c4e862de46ec1\`.
- EP45 Korean \`meritsystem_msg.enc\`: 9,736 bytes, SHA \`8325002522e565b7d06cf82b9e64bbe0b00a564be38f5f2474dfa018a7078e76\`.
- active server \`MeritSystem.scp\`: SHA \`307fc981ec3efe66f6cc1b0606ed7d86cd9e5a6e46205769a9bb34b012464295\`.

Original script called \`ZipFile.CreateFromDirectory\`, then checked \`ZipArchiveEntry.FullName\` against manifests containing forward slashes. Windows .NET Framework may write archive entry names with backslashes. Result \`ZIP_MISSING: client/v291/meritsystem.enc\` happened **after ZIP file creation**, not during content collection. Script \`finally\` deletes only the temporary source copies, **not** the ZIP in Downloads. The latest \`CABAL-DIAMOND-SOURCES-*.zip\` likely already contains all six sources; verify entry names normalized with \`.Replace('\\','/')\` before any re-run. Fix committed in \`diamond-insignia/Collect-DiamondInsignia-Sources.ps1\` as of \`a209abdb2f7627cf5eccc83eb32db502d6b1eb42\`. Do not require the user to rerun SSH collection if the already-existing ZIP is valid. No client or VM modifications occurred. Feature port pending direct source analysis.


## USER-UPLOADED ZIP: exact EP45 Merit binary decode + add-only delta (2026-11-21)

Source (user-provided, no remote VM access required): \`CABAL-DIAMOND-SOURCES-1bec4d3ce4.zip\`. ZIP manifest and all **six** source file byte lengths/SHA256 checks pass.

- EP45 \`meritsystem.enc\` is successfully decoded to **660,148 bytes** of actual XML, with verified 4-byte uncompressed size and raw DEFLATE data using the classic 4-byte XOR key \`92 65 67 57\`.
- EP45 \`meritsystem_msg.enc\` decodes to **97,784 bytes** of XML; category labels and descriptions are present.
- Actual v291 \`meritsystem.enc\` = **41,368 compressed/encoded bytes**, first 4 bytes represent 663,334 uncompressed bytes. It does **not** decode with EP45's classic XOR key. DO NOT replace it with the EP45 .enc; preserving the working v291 client is essential.
- EP45 includes exactly **474 Mastery definitions**: 64 Gold (grade0), 94 Platinum (grade1), **316 new Diamond (grade2)** over 16 new category IDs 11-26. Active WorldSvr SCP has precisely 158 Gold/Platinum rows and zero grade2 rows.
- All **158 of 158** old \`MeritMastery_Base\` records match EP45 byte-for-byte as TSV fields; existing \`MeritMastery_Value\` has **30** differences within its 840 old rows, and existing \`SpecialMastery_Value\` has **14** differences in 183 rows. Therefore **preserve existing** Gold/Platinum value rows rather than transplanting the entire EP45 configuration.

Offline add-only donor deltas in conversation artifact \`CABAL-DIAMOND-INSIGNIA-EP45-DIFF-REVIEW.zip\`:
| Native table | Additive rows | Existing differences (preserve old) |
| --- | ---: | ---: |
| MeritMastery_Base | 316 | 0 |
| MeritMastery_Value | 1096 | 30 |
| UpGrade_Material | 1 | 0 |
| SlotOpen_Material | 616 | 0 |
| SlotOpen_Time | 308 | 0 |
| SpecialMastery_Material | 1 | 0 |
| SpecialMastery_Value | 100 | 14 |
| SpecialMastery_Active | 4 | 0 |

Also decoded EP45 contains new client-only categories/sections:
\`dia_meritscore_fomula\` (301), \`SpecialCategory_Active\` (12),
\`Category_Summary\` (154), \`Category_Group\` (4), \`MasteryIndex_Group\` (4),
\`SpecailMastery_Passive\` (15). **Native server equivalents/persistence must be established**, not guessed.

Verified Diamond group mapping and EP45 English labels:
- 11 **Steadfast Resolution** → 12,13,14
- 15 **Fatal Strike** → 16,17,18
- 19 **Indomitable Spirit** → 20,21,22
- 23 **Powerful Judgment** → 24,25,26

EP45 Diamond rank-up material: \`upgrade_badge=2\`, \`upgrade_wexp=30000\`,
\`upgrade_item=33554961\`, \`upgrade_count=100\` (item ID, NOT a textual name).
Requires native server validation, transactional accounting and persistent DB state.

**Not safe to deploy data alone**: The actual WorldSvr's recognition of grade 2, script sections, new packet types, and SQL state is not established. The offline bundle deliberately contains \`STAGED_ONLY\` rows/JSON, not a one-click binary patch or deployable SCP. It includes decoded EP45 XML plus a reproducing Python3 comparison tool, validations and an audit report. The project branch \`feature/diamond-insignia-v291-20261121\` and draft PR #2 remain the handoff for Codex. Full game data is NOT committed to the public repository.

### Native follow-up
Private \`cabal-ep36\` branch \`feature/diamond-insignia-ep39-audit-20261121\`
adds a SHA-matched static WorldSvr scan of Diamond parser and handler tokens.
It does not modify any VM. Then verify actual v291 client packets, current
extension modules and database schema before integrating any new rows.


### Original WorldSvr capability scan — completed

GitHub Actions static read-only run:
https://github.com/patmalnieksgatis-netizen/cabal-ep36/actions/runs/44924708106
validated **the exact same** WorldSvr SHA-256 as the user VM. Binary-string
inspection found Gold/Platinum loader tags \`MeritScore_Fomula_Platinum\`,
\`MeritMastery_Base\`, \`MeritMastery_Value\`, \`SpecialMastery_Ratio\`,
\`OnCSCMeritMasteryLvUp\`, plus **one generic** \`Category_Group\` token.
It found **zero** ASCII/UTF16 occurrences of:
\`Diamond\`, \`diamond\`, \`DIAMOND\`, \`MeritScore_Fomula_Diamond\`,
\`SpecialCategory_Active\`, \`MasteryIndex_Group\`,
\`SpecailMastery_Passive\`, and \`Category_Summary\`.

This makes a **server-native extension/adapter very likely necessary**, but
string absence alone cannot disprove unnamed handlers or code inside loaded
external extension modules. Never apply the staged config rows directly
to the live WorldSvr without handler/SQL testing. **Preserve the two working
RAM compatibility patches** for Upgrade Core +20 and Safeguard.

Next implementation milestone (still unimplemented): audit loaded extension
modules, exact merit-related packets and SQL schema on an isolated test VM,
then build Diamond-specific native adapter, preserving old Gold/Platinum rows.


## 2026-11-21 NEXT PHASE — native add-only SCP built; legacy-code limits and codec audited

The user explicitly requested autonomous continuation after the six-file binary
Merit audit. Performed offline from the exact uploaded source ZIP and reviewed
Diamond delta. **No changes to their active game/client/VM/SQL.**

### Staged native candidate (not deployable)

The conversation attachment \`CABAL-DIAMOND-NATIVE-STAGED-DO-NOT-INSTALL.zip\`
contains a fully assembled native \`MeritSystem.DIAMOND_STAGED_DO_NOT_INSTALL.scp\`,
a source-based reproducible builder, and SHA-256 manifest.

- Base **active SCP** SHA256 \`307fc981ec3efe66f6cc1b0606ed7d86cd9e5a6e46205769a9bb34b012464295\`, 54,866 bytes.
- New **staged SCP** SHA256 \`26c9c4cbe3136f67f0298c8e412a4aa7620ba46d62b5c3950880fe821f2ee2e5\`, 116,812 bytes.
- Appends 2,442 *only Diamond* rows to eight existing tables, without adding
  speculative new native section headers:
  - \`MeritMastery_Base\` 316, \`MeritMastery_Value\` 1096,
  - \`SlotOpen_Material\` 616, \`SlotOpen_Time\` 308,
  - \`SpecialMastery_Active\` 4, \`SpecialMastery_Material\` 1,
  - \`SpecialMastery_Value\` 100, \`UpGrade_Material\` 1.
- The source builder **removes the appended rows and byte-compares the result
  to the original**. Exact recovery passed.
- Highest new Diamond Mastery_Index **474**, categories 11–26. Old loaded
  parser/array lengths need audit before any attempt to ingest these values.
- Four Diamond groups' subcategory indices:
  \`11 -> 12,13,14\`, \`15 -> 16,17,18\`,
  \`19 -> 20,21,22\`, \`23 -> 24,25,26\`.
- The 301 Diamond score bands are contiguous (0–800,568); 15 passive-exp
  bands are contiguous (0–600,000). EP45 XML includes source definitions
  but not the missing native server \`SpecialMastery_Ratio\` table extension.
- **Do not install** this candidate on live WorldSvr: grade=2 arrays,
  category selection handler, packet versions, expiry, SQL persistence and
  passive effects are not proven and could crash or corrupt game state.

### Client codec blockers — verified, not guessed

- Actual v291 compressed Merit file: 41,368 bytes, declared **663,334**
  uncompressed bytes; EP45 donor: 42,290 bytes, declared **660,148**
  bytes. v291 might already have newer Merit client fields; file sizes
  cannot prove Diamond support.
- Classic v282/EP45 XOR first 4 compressed bytes, key
  \`92 65 67 57\`, successfully decodes EP45 XML. It fails on v291.
- An independent offline brute-force sanity check of **1,903,680 complete
  standard-DEFLATE dynamic-header candidates** (plus BFINAL=0) failed to
  produce a valid XML prefix from v291 unchanged suffix bytes. This is
  not a proof of the actual v291 codec, but shows *do not* assume EP45
  encoding. Need v291 client codec/runtime data-cache analysis.
- **Never transplant the EP45 \`.enc\` over v291.**

### Additional source inventory

Private \`cabal-ep36\` branch's read-only CI audited both
\`CABAL_EXTRA_SOURCE.tar.gz\` and \`CABAL_VPS_FULL.tar.gz\`.
The extra source is an **incomplete WorldSvr extension project** with
87 files (WorldSvrRealm, packet structs, macro BM3, warp, etc.),
not a full proprietary game WorldSvr. It has no Merit/Diamond code
keyword hits. The full server tar has SQL backups and scripts but
no ready Diamond implementation. Native Diamond adapter therefore
requires reverse engineering verified current modules / wire protocol
and DB table schema. No unsafe guessed ABI or SQL migration was emitted.

### Safe active-runtime audit artifact

Conversation-local \`Audit-DiamondRuntime-v291.ps1\` (SHA256
\`36443647641d808e8b6b712a5841fddb59b7bf252f994647f5095e0f033a5608\`)
performs a **read-only** single SSH audit:
- inspect mapped \`/etc/cabal/*.so\` and WorldSvr file SHA256 and limited
  Merit/Diamond text symbol hints;
- query **only** \`Server01.INFORMATION_SCHEMA.COLUMNS\` via \`sql_main\`
  if \`sqlcmd\` and container environment credentials exist;
- writes no files to VM and reads no character/account table rows;
- stores \`CABAL_DIAMOND_RUNTIME_AUDIT.json\` in Windows Downloads.
- **Not run on user's private VM**. SQL metadata may be unavailable if
  \`sqlcmd\` is missing; fail closed and do not read secret config files.

Next implementation gates: live mapped module inventory and SQL column names,
versioned v291 client Merit packet captures, additive DB persistence design,
native Diamond-only handler in isolated clone, Gold/Platinum and core+20
regression tests.


## Priority clarification — 2026-11-21: Platinum + Diamond together, Anima Mastery next

User instruction: **Merit system must include both Platinum Insignia and
Diamond Insignia**. Only after these work, proceed with **Anima Mastery**.
Do NOT conflate Anima Mastery with Diamond Merit; it is a separate later system.

Acceptance/implementation sequence:
1. Preserve **all existing Platinum Insignia** config, mastery purchase,
   stats and character persistence (94 \`Badge_Grade=1\` rows) and old Gold
   compatibility data (64 \`Badge_Grade=0\` rows).
2. Add **Diamond Insignia** \`Badge_Grade=2\`, 316 Mastery definitions in 16
   category IDs 11–26, four groups and prerequisites; do not modify
   Platinum index/force tables or packet layouts.
3. Implement/test **server-authoritative** Diamond rank-up, points and
   category restrictions; verify SQL persistence across logout/restart,
   passive effects and cost validation, preserving existing character data.
4. Verify older working systems (Costume, dungeons, Upgrade Core +20,
   Safeguard, etc.) are unaffected. Only then begin **Anima Mastery**.

A newly committed offline \`diamond-insignia/test_platinum_diamond_integrity.py\`
checks SHA-pinned original and staged SCP files, identical existing rows,
Gold 64 / Platinum 94 / Diamond 316, 16 categories, 474 contiguous
Mastery_Index values, no orphan new Mastery_Value references,
and Diamond rank-up source values (30,000 WExp + 100 units item 33554961).
This test PASSED against the user's uploaded ZIP and offline staged ZIP,
but **gameplay, SQL and wire packet compatibility remain unverified**.

The read-only \`Audit-DiamondRuntime-v291.ps1\` in conversation is ready
to query the active VM's WorldSvr module identities and available
\`Server01.INFORMATION_SCHEMA.COLUMNS\` **only**; it does not read any
player records, alter game files, SQL or restart WorldSvr. A remote SSH
run by the Windows host is needed for actual runtime schema evidence.


## 2026-11-21 live runtime preflight returned by user — SQL metadata available

The user ran the previously prepared \`Audit-DiamondRuntime-v291.ps1\` on the
private VM, with these exact read-only results:

\`\`\`
WORLD_INNER_PID=64516
MODULE=WorldSvr_01_01;SHA256=caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3;HAS_DIAMOND_LITERAL=False
MODULE=EP36CostumeMileage.so;SHA256=5d50a5b0f8c7b7d522631138750ef134c19c9ce909339e673a6d1bec8d0e2007;HAS_DIAMOND_LITERAL=False
SQL_METADATA_STATUS=SERVER01_METADATA_READ
SQL_MATCHING_COLUMNS=74
SERVER_SQL_AND_CLIENT_UNMODIFIED=YES
\`\`\`

**Important scope:** \`SQL_MATCHING_COLUMNS=74\` is a count from a
\`Server01.INFORMATION_SCHEMA.COLUMNS\` query where table or column names
match Merit/Mastery/Insignia/Diamond/Medal. It does **NOT** establish that
Diamond persistence exists. The report contains the exact 74 rows, but the
user's pasted shell output does not display them. Do not guess table names or
write migrations until the report has been obtained.

The authoritative local report path is
\`C:\Users\patma\Downloads\CABAL_DIAMOND_RUNTIME_AUDIT.json\`.
Ask the user to attach this **already existing JSON** only; no further
SSH or VM reads are needed to determine the returned table/column names.

The repository now includes \`diamond-insignia/analyze_runtime_schema.py\`
and \`test_analyze_runtime_schema.py\`. The offline analyzer groups all
returned columns by schema/table, surfaces possible but **unconfirmed**
character keys, and marks missing PK/FK/constraints/packet evidence. It
rejects missing/unsafe read-only markers. Both tests pass on synthetic
metadata, but **actual live column names cannot be analyzed until the
saved JSON is supplied**.

Next work: inspect the report; then, if needed, perform a narrow read-only
PK/FK/constraint audit of exactly the observed Merit tables. Preserve
Platinum and Gold, and keep Anima Mastery as a separate future milestone.


## 2026-11-21 — user-provided live SQL metadata report fully inspected

User attached \`CABAL_DIAMOND_RUNTIME_AUDIT.json\`, which contains a successful
read-only \`Server01.INFORMATION_SCHEMA.COLUMNS\` result (74 matching column
records across 34 distinct tables; no truncation, limit 140).

**Actual active tables (from attached source, not inferred):**

- \`dbo.cabal_merit_table\`:
  \`UserNum int\`, \`MeritPoint int\`, \`MeritMasteryPoint int\`,
  \`MeritMasteryData varbinary\`.
- \`dbo.cabal_merit_platinum_table\`:
  \`UserNum int\`, \`HaveMeritPlatinumBagde tinyint\`,
  \`MeritPlatinumPoint int\`, \`MeritPlatinumMasteryPoint int\`,
  \`UsingMeritPlatinumPageID tinyint\`,
  \`MeritPlatinumMasteryOpenIndex int\`,
  \`MeritPlatinumMasteryOpenDate datetime\`,
  \`MeritPlatinumMasteryRemainPoint varbinary\`,
  \`MeritPlatinumMasteryOpenSlot varbinary\`,
  \`MeritPlatinumSpecialMastery varbinary\`,
  \`MeritPlatinumPageExtendedCount tinyint\`.
- \`dbo.cabal_merit_platinum_mastery_table\`:
  \`UserNum int\`, \`MeritPlatinumMastery varbinary\`.
- \`dbo.cabal_contents_control_etc_table\`:
  \`MeritUse tinyint\`, \`MeritPlatinumUse tinyint\`.
- \`dbo.cabal_honormedal_user_table\`:
  \`UserNum int\`, \`Grade int\`, \`Score int\`.

Among columns/tables matching Diamond or Insignia in this catalog query,
**none** are found. However the query is filtered by names, so that does not
prove the absence of opaque/unrelated Diamond data elsewhere; no other tables
or rows have been read.

**Runtime code fact**: current WorldSvr has literal Platinum handlers
\`OnCSCMeritPlatinumBadgeGradeUp\`,
\`OnCSCMeritPlatinumBadgeMasterySlotOpen\`,
\`OnCSCMeritPlatinumPageChange\`,
\`OnCSCMeritPlatinumSpecialMastery\`, and
\`OnCSCMeritPlatinumSpecialMasterySeal\`. No Diamond literal in the two
identified loaded modules. This supports a likely Diamond-specific native
feature gap but does not prove all dynamically resolved handlers are absent.

**Critical boundaries**:
1. The initial Information Schema report only returns matching *columns*;
   it does NOT give \`varbinary\` lengths, PK, FK, indices, null/default
   constraints, or Merit-related stored procedure parameter signatures.
2. Do not create/alter SQL tables merely based on guessed names. Platinum is
   demonstrably a user-level (\`UserNum\`) data model with binary payloads.
3. No live Diamond client packet capture or its v291 \`.enc\` serializer has
   been decoded. Do not deploy the staged Diamond SCP in isolation.
4. Platinum + Diamond is the single current target, Anima Mastery next.

A new conversation-local **read-only** Windows PowerShell script
\`Audit-DiamondSqlDeep-v291.ps1\` inspects only
\`sys.tables\`, \`sys.columns\`, \`sys.types\`, \`sys.indexes\`,
\`sys.index_columns\`, \`sys.foreign_keys\`, \`sys.triggers\`,
\`sys.procedures\` and \`sys.parameters\` for the five grounded existing
tables and Merit/Platinum/Diamond named procedures. It does not read game rows
or SQL procedure bodies; it writes a JSON report to Windows Downloads.
The embedded remote Python passed an offline syntax check and query string
static review; **not yet executed on user's private VM**.

\`\`\`powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\Audit-DiamondSqlDeep-v291.ps1"
\`\`\`

Next, use the resulting \`CABAL_DIAMOND_SQL_DETAILS_*.json\` to design
an additive, reversible **test-only** Diamond persistence migration (with
transactions, unique user key and verified binary layout). Do not modify the
working Gold/Platinum tables until this is proven in an isolated clone.

## 2026-11-21 Diamond phase after Platinum user acceptance

The user reported Platinum for the wolverine account is OK. Treat this as user-reported success; no independent in-game persistence regression proof was supplied.

Retested the exact uploaded source ZIP against the offline Diamond staged SCP: PASS (64 old Gold and 94 Platinum untouched, 316 new Diamond grade2 masters, 16 Diamond categories, 2442 additive rows). Source SCP SHA256 307fc981ec3efe66f6cc1b0606ed7d86cd9e5a6e46205769a9bb34b012464295; candidate SHA256 26c9c4cbe3136f67f0298c8e412a4aa7620ba46d62b5c3950880fe821f2ee2e5.

Do NOT install the staged SCP: loaded old WorldSvr and EP36CostumeMileage.so do not expose named Diamond handlers; the user SQL metadata includes Platinum tables but no named Diamond persistence; the live v291 ENC codec is not decoded.

Next required isolated proof is the already created read-only Audit-DiamondSqlDeep-v291.ps1, SHA256 f010b3fd8ff0dc76f6cf3a58454a19e3f5e57965811d9192c371c5a161128596. It inventories only SQL catalog (exact column lengths/nullable/defaults, keys/indexes, FKs, triggers, stored procedure names and parameter types). It has passed the embedded Python syntax and SQL static checks, not yet run on the private VM. Output in Downloads/CABAL_DIAMOND_SQL_DETAILS_*.json. Then prepare separate Diamond persistence adapter in an isolated VM, packet compatibility tests, and v291 client Merit serializer research.

Order remains Platinum -> Diamond -> Anima Mastery. No server or client modifications in this update.


## 2026-11-21 user's complete deep SQL audit integrated, clone-only Diamond LAB V1 built

The attached verified JSON \`CABAL_DIAMOND_SQL_DETAILS_20261121_194146.json\`
was programmatically inspected. **Actual counts**: 5 requested tables,
34 columns, 4 PK indexes, 0 FK relationships, 0 triggers, 14 matched
Merit/Platinum procedures, 50 parameter declarations. The SQL catalog query
returned \`SERVER01_SQL_CATALOG_READ\`, no game/account rows and no changes.

**Confirmed primary keys:** \`UserNum INT\` in \`cabal_merit_table\`,
\`cabal_merit_platinum_table\`, \`cabal_merit_platinum_mastery_table\`
(and \`cabal_honormedal_user_table\`). Platinum stores
\`MeritPlatinumMastery VARBINARY(8000)\`, remaining points
\`VARBINARY(128)\`, open slots \`VARBINARY(1024)\`, Special Mastery
\`VARBINARY(1024)\`. Binary encodings remain unknown.
There is no matching Diamond-named SQL table or stored procedure in the
filtered catalog. Platinum \`cabal_tool_merit_platinum_get/set\` and
\`cabal_tool_merit_platinum_mastery_get/set\` procedures exist.

**Delivered ZIP:** \`CABAL_DIAMOND_SQL_LAB_V1_TEST_ONLY.zip\`,
SHA256 \`2f949adac9969f9164a0bd846c58aca823208d9c25353ae6cd002be5d0004dd0\`.
Contains \`01_install_TEST_CLONE_ONLY.sql\`, metadata verification,
zero-row-only rollback, future get/set contract, user's SQL catalog
(metadata only), offline validation script and six unit tests.
All six offline tests pass on the uploaded report; SQL Server runtime
execution has NOT been attempted.

**Safety:** \`01_install_TEST_CLONE_ONLY.sql\` and rollback use a hard-coded
\`USE [Server01_DiamondLab]\`, check \`DB_NAME()\`, validate existing
Gold+Platinum source objects and \`UserNum\` PK, and only create/drop
\`dbo.cabal_merit_diamond_lab_v1\`. They do NOT create test DB
automatically; do NOT mutate production \`Server01\`, player data,
Gold/Platinum tables or WorldSvr. The table is a persistence *prototype*,
not the yet-missing Diamond runtime handler. It intentionally uses
\`VARBINARY(MAX)\` for opaque future payloads rather than guessing actual
Diamond packet sizes.

SQL prototypes are checked into this branch in
\`diamond-insignia/sql-lab/\` with README. Do not call it installed,
functional in-game, or deployable until client codec, WorldSvr handler,
server-authoritative validation and login/logout SQL persistence pass in
an isolated full environment.
