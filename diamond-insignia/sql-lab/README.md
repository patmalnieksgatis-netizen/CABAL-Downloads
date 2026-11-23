# Diamond Insignia — Server01_DiamondLab, TEST CLONE ONLY

**Not deployable to live CABAL v291 yet.** Do NOT run installer against \`Server01\`, and do NOT overwrite existing \`MeritSystem.scp\`. The user has confirmed Platinum for account \`wolverine\`; preserve its user data.

### Verified actual live catalog (user's read-only report 2026-11-21)

- \`Server01\`: 5 relevant tables, 34 columns, 4 primary-key indexes, no FKs/triggers on those tables, 14 Merit/Platinum stored procedures and 50 procedure parameters.
- \`dbo.cabal_merit_table\`: \`UserNum INT PRIMARY KEY\` and Gold point/mastery fields.
- \`dbo.cabal_merit_platinum_table\`: \`UserNum INT PRIMARY KEY\`, score, mastery points, binary slot/page/SpecialMastery fields.
- \`dbo.cabal_merit_platinum_mastery_table\`: \`UserNum INT PRIMARY KEY\`, \`MeritPlatinumMastery VARBINARY(8000)\`.
- \`cabal_contents_control_etc_table\`: \`MeritUse\` and \`MeritPlatinumUse\`.
- \`dbo.cabal_tool_merit_platinum_get/set\` and \`dbo.cabal_tool_merit_platinum_mastery_get/set\` exist.
- No **named** Diamond table, column or stored procedure returned by the filtered catalog audit. No Diamond runtime handler evidenced.

### LAB V1 files

1. \`01_install_TEST_CLONE_ONLY.sql\`: guarded \`USE [Server01_DiamondLab]\`, refusal unless clone's Gold/Platinum tables and \`UserNum\` PK exist, and only then creates *one new* \`dbo.cabal_merit_diamond_lab_v1\`. Uses transaction rollback on failure, checks \`DB_NAME()\`, rejects existing object. No changes to existing tables or player data.
2. \`02_verify_TEST_CLONE_ONLY.sql\`: read-only lab object metadata validation, no user rows.
3. \`03_rollback_TEST_CLONE_ONLY.sql\`: refuses incorrect DB, changed schema, or any existing lab rows. Drops only empty lab table.
4. \`04_get_set_contract_TEST_CLONE_ONLY.sql\`: non-executable specification of a future versioned Diamond get/set bridge, not game protocol implementation.

The lab table includes \`UserNum INT PK\`, \`BadgeGrade=2\`, Diamond unlock flag, score, mastery points, active Diamond category (11–26), **uninterpreted** \`VARBINARY(MAX)\` placeholders and \`RowRevision\`. Blob format cannot be inferred from the Platinum column sizes. Do not populate production character data until actual server/client serializer and packet ABI are verified.

### Offline tests and artifact

\`CABAL_DIAMOND_SQL_LAB_V1_TEST_ONLY.zip\` is a conversation artifact that also contains sanitized schema-only evidence, an offline verifier and 6 unit tests. ZIP SHA256:
\`2f949adac9969f9164a0bd846c58aca823208d9c25353ae6cd002be5d0004dd0\`.
All **6/6** offline tests passed. **No SQL Server execution was done**, so the T-SQL is still untested at runtime.

### Next implementation

- Clone SQL \`Server01\` to isolated \`Server01_DiamondLab\` (do not make huge clones or back up active data without deliberate resource check).
- Evaluate lab persistence API against observed \`UserNum\` PK and confirmed Platinum procedures; validate optimistic version handling.
- Decode target v291 \`meritsystem.enc\` format; confirm Diamond client HUD/packet opcodes and WorldSvr Merit handler.
- Implement server-authoritative Diamond grant/points, SQL get/set, login/logout persistence in a test WorldSvr. Prove Platinum and Gold unchanged; preserve Upgrade Core +20 and Safeguard.
- Only after Diamond works proceed to Anima Mastery.

Avoid telling the user Diamond is installed. It remains offline/staged.


## V2: stored procedures and deterministic rollback smoke (2026-11-21)

Additional files committed here:
- \`05_create_diamond_lab_procedures_TEST_CLONE_ONLY.sql\` creates
  \`cabal_diamond_lab_init_v1\`, \`cabal_diamond_lab_get_v1\`,
  \`cabal_diamond_lab_commit_v1\`.
- \`06_transaction_smoke_TEST_CLONE_ONLY.sql\` tests a synthetic
  \`UserNum=2147483600\` *inside a transaction*, then **ROLLBACKs**.
  Requires the LAB schema and procedures; does not touch real user records.
- \`07_remove_diamond_lab_procedures_TEST_CLONE_ONLY.sql\` removes only those
  three uniquely LAB-named procedures; use before V1's table rollback.
- \`test_lab_v2_static.py\` / \`.github/workflows/diamond-sql-lab-static.yml\`
  perform **10 CI static guard tests** (passed:
  https://github.com/patmalnieksgatis-netizen/CABAL-Downloads/actions/runs/44933080128).
  Separate conversation ZIP performed **17 additional local static/model tests**.

**Boundaries:** no SQL Server execution performed and no actual C2S packet
handler or WorldSvr integration exists. \`init\` only checks Platinum badge
and inserts a *locked* Diamond row. \`commit\` requires an already unlocked
row, matching \`RowRevision\`, valid category and bounded payload.
It does **not** authenticate client packets, deduct WExp/items or validate
mastery points against the game configuration; only a future
server-authoritative adapter may call it after such validations.
There is no GRANT, live account update or game restart.

Exact execution order in an isolated clone:
1. V1 \`01_install...\` (creates lab table)
2. V2 \`05_create...\` (three procedures)
3. V1 \`02_verify...\` (schema checks)
4. V2 \`06_transaction_smoke...\` (synthetic ID, complete rollback)
5. V2 \`07_remove...\` (procedures)
6. V1 \`03_rollback...\` (only if table empty)

The full offline tested package with graph validator is a conversation
artifact \`CABAL_DIAMOND_ENGINE_PREP_V3.zip\` (21,678 bytes, SHA256
\`4460dfc0af73b5b82b1692da4a370d927edc3572f136e7889e246d9313806dd2\`).
It is **NOT FOR LIVE INSTALLATION**.
