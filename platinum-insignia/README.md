# CABAL v291/EP39 — Platinum Insignia guarded activation

**Status:** A complete PowerShell 5.1 installer is built and tested offline. It has **not yet executed against the user's private VM**. No claim of in-game Platinum working.

## Verified existing source data
- v291 client root \`F:\CABAL_291_TEST\` with \`Data\meritsystem.enc\` SHA-256 \`3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a\`.
- Original native WorldSvr SHA-256 \`caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3\`.
- Active server \`/etc/cabal/Data/MeritSystem.scp\` SHA-256 \`307fc981ec3efe66f6cc1b0606ed7d86cd9e5a6e46205769a9bb34b012464295\`.
- Exactly 64 Gold and 94 Platinum \`MeritMastery_Base\` definitions; 840 original \`MeritMastery_Value\` records.
- Original WorldSvr includes \`OnCSCMeritPlatinumBadgeGradeUp\`, \`OnCSCMeritPlatinumPageChange\`, \`OnCSCMeritPlatinumSpecialMastery\`.
- Active SQL \`Server01.dbo.cabal_contents_control_etc_table\` has \`MeritUse\` and \`MeritPlatinumUse\` global controls, and all three Merit/Platinum persistence tables exist.

## Delivered standalone artifact
Full PowerShell5.1 script: \`CABAL_PLATINUM_SAFE_ACTIVATE.ps1\`, SHA-256
\`5f7f49779b7178f38f1c4dd5fe17062c2235cf7c63732665a23fef900cdbf8b4\`.
Conversation bundle \`CABAL_PLATINUM_SAFE_ACTIVATE_BUNDLE.zip\`, SHA-256
\`af378eb86f75846c7beceec0c4246f78939546f3880f24321c103d0d6c8360b6\`.
Includes \`README_PLATINUM_LV.txt\` and simulated remote integration tests (\`test_remote.py\`).

**Script is linked as a conversation artifact; do not invent a GitHub path to the full binary/script until separately committed.**

### User Windows commands

\`\`\`powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\CABAL_PLATINUM_SAFE_ACTIVATE.ps1" -Action Inspect
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\CABAL_PLATINUM_SAFE_ACTIVATE.ps1" -Action Activate
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\CABAL_PLATINUM_SAFE_ACTIVATE.ps1" -Action Rollback
\`\`\`

## Strict activation logic

1. Before SSH: verify v291 client's **exact** pinned \`meritsystem.enc\` SHA.
2. Inside \`cabal_main\` without modifications: verify supervisor's running WorldSvr PID; hash \`/proc/PID/exe\` and active SCP; verify all expected Platinum Merit handler strings and exact Gold/Platinum definitions, \`Common.ini\` Merit path.
3. Inside \`sql_main\`: use existing environment-based SQL credentials only inside the container, query **aggregate global flag values only**, never player rows or serialized Mastery blobs. Require \`Server01.dbo.cabal_contents_control_etc_table\` has **exactly one row**, \`MeritUse=1\`, \`MeritPlatinumUse\` in {0,1}, and all Gold/Platinum persistence tables exist.
4. \`-Action Inspect\`: read-only, no modifications.
5. \`-Action Activate\`: if Platinum flag already **1**, report \`ALREADY_ENABLED_NO_CHANGE\`; if flag **0**, issue a SQL transaction with \`XACT_ABORT\`, 5-second lock timeout, \`WITH (UPDLOCK,HOLDLOCK)\`, guarded WHERE, \`@@ROWCOUNT=1\`, and commit/automatic rollback on SQL error. Update **only global** \`MeritPlatinumUse\` to 1.
6. After the change, re-query and validate the flag; store \`CABAL_PLATINUM_RESULT_*.json\` and \`CABAL_PLATINUM_ACTIVATION_STATE.json\` local rollback anchor.
7. \`-Action Rollback\`: accepted **only when the anchor proves** original flag was 0 and was changed to 1. Under same guards, revert **only** this flag 1→0, no other data.
8. **No restart** of WorldSvr or Docker; no game binary/client SCP modifications; Preserve Upgrade Core +20 and Safeguard RAM fixes.

**Safety**: Refuses operation on changed client, changed server hashes, disabled Gold Merit, multirow/empty flag table, absent Platinum handlers, missing persistence tables, missing SQL connectivity. This ensures no guessed row-wide update.

**Limited claim:** enabling \`MeritPlatinumUse\` alone may not activate the feature until a controlled server restart or client reconnection. Gameplay, points, bonuses, actual account progress and persistence still need verification in-game; don't report full installation before that.

## Testing
9 offline mocked simulations pass:
- inspect flag0 / flag1
- activate flag0→1 / flag1 noop
- rollback flag1→0
- refuse multirow table, disabled Gold, WorldSHA mismatch and rollback when flag0.

Next: user runs the script on their local Windows PC (SSH to VM), reports \`PLATINUM_STATUS\` and \`PLATINUM_RESULT\`. Depending on result, no-op if already enabled, guarded flag activate, or targeted fix rather than an unsafe broad patch.

After Platinum gameplay verified, continue Diamond Insignia native adapter and SQL persistence work from draft PR #2, and only then Anima Mastery.
