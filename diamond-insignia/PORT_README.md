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
