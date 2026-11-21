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
