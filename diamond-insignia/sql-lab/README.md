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
