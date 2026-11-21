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
