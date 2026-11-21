# CABAL v291 / EP39 — Upgrade Core / Perfect Core disconnect diagnostic handoff

**Status (2026-11-21): DIAGNOSIS NOT VERIFIED; NO FIX DEPLOYED.**

## Confirmed by user

- v291 client + EP39/EP36 derived WorldSvr; Force Core, Chaos Upgrade and Divine Upgrade work.
- Upgrade Core and Perfect Core disconnect the client.
- This suggests (but **does not prove**) a common normal-upgrade request/response/handler issue.

## Grounded project setup and current limitations

- Test VM SSH: `root@192.168.56.101` (VirtualBox host-only; this assistant cannot connect to that private network).
- Docker container: `cabal_main`; World process `WorldSvr_01_01`.
- Previously reported active binary: `/etc/cabal/migration_tools/ep36-costume-trial-v1/native/WorldSvr_01_01` — verify actual running `/proc/PID/exe` before analyzing; **do not assume unchanged**.
- Client working tree: `F:\CABAL_291_TEST`, lab: `F:\CABAL_291_LAB`.
- Git repos: `patmalnieksgatis-netizen/cabal-ep36` (binary/source archives), `patmalnieksgatis-netizen/CABAL-EP45` (currently tracked **client inventory**, not verified EP45 runtime), `patmalnieksgatis-netizen/CABAL-Downloads` (scripts, prior Warp packet investigation).
- Warp 485 is **a separate unresolved issue**, with failed Stage P/Q/R signed-client patches. Read `WARP485_CODEX_HANDOFF.md`; don't confuse it with normal upgrade or repeat EXE patching.
- No verified normal-upgrade opcode, packet shape, disconnection reason, logs, or EP45 upgrade donor source has been retrieved yet. Do **not** invent values or claim a patch is tested.

## Repro and evidence (first priority)

The accompanying read-only Python collector runs **on the VM host**, with Docker and a running WorldSvr. It captures WorldSvr/Supervisor PID transitions, relevant appended logs, pre/post core-file metadata, and Docker logs. It **does not** alter server, databases, client or network.

```bash
python3 Diagnose-UpgradeCore-v291.py --case upgrade --seconds 60 --out /tmp/upgradecore-case.json
python3 Diagnose-UpgradeCore-v291.py --case perfect --seconds 60 --out /tmp/perfectcore-case.json
python3 Diagnose-UpgradeCore-v291.py --case force-control --seconds 60 --out /tmp/forcecore-control.json
```

During each window reproduce the corresponding game action once. Store outputs privately (may contain player identifiers); do not commit raw logs. Compare `world_observation`, PID transitions, new log lines and core dump metadata; stable PID alone cannot distinguish S2C mismatch vs server-side disconnect. If the container lacks Python 3, collector reports `CONTAINER_PYTHON_UNAVAILABLE`; solve only in the isolated test copy and avoid installing dependencies into live `cabal_main`.

## Investigation decision tree

1. **WorldSvr PID changed / crash dump:** inspect exact crash and call stack **offline**, identify handler + item path. Do not patch based on guessed opcode.
2. **WorldSvr stays running, logs explicit kick/validation failure:** identify item type, handler rejection, request length and invalid state. Verify expected validated error response vs intentional disconnect.
3. **WorldSvr stays running, client disconnects and no server reason:** capture authorized client and server packet tracing from existing debug infrastructure in LAB. First find real C2S handler by observing Upgrade Core request. Compare opcode, header format, declared size, payload, subcommand, item slot and target with Force Core control. Then inspect corresponding S2C response. Don't treat ciphertext/raw TCP bytes as decoded protocol.
4. **Only certain core grade or + level fails:** compare item kind and grade bounds, material classification and configuration. Item naming IDs from `items.xml` are **text IDs** and not proof of live item-kind records.
5. Use EP45 **only after** verifying its server-side implementation exists and matches the target semantics. The `CABAL-EP45` repo currently does not establish a complete running EP45 WorldSvr.

## Safe integration criteria

- Back up and hash candidate binaries/config/db before an isolated lab patch.
- Never disable packet validation, item/level checks or socket security to hide a disconnect.
- Never overwrite working signed `CabalMain.exe` or production WorldSvr as a shortcut.
- Real game acceptance: Upgrade Core success/failure result, Perfect Core, item +level persistence after reconnect, no disconnect, Force/Chaos/Divine regression, no WorldSvr restart.
- Commit text-only implementation changes/test evidence summaries after verified test; label any untested hypothesis as unverified.

## Automated private three-case comparison

After capturing one Upgrade Core, one Perfect Core and one successful Force Core
control during three **separate real client tests** (on the TEST VM), run:

```bash
python3 Analyze-UpgradeCore-v291.py   --upgrade /tmp/upgradecore-case.json   --perfect /tmp/perfectcore-case.json   --force /tmp/forcecore-control.json   --out /tmp/upgradecore-triage.json
```

The output gives a root-cause **category and next investigation step**, but
cannot recover missing packet opcodes or claim a fixed game. It does not print
raw log lines or upload any files. Keep even the redacted triage private if it
can disclose your setup. Available categories include crash/restart, server
log rejection, missing status, and stable-WorldSvr client disconnect.

**Review note (2026-11-21):** Source archaeology on linked GitHub found no
confirmed EP45 server-side Normal Upgrade donor source: CABAL-EP45 contains
client inventory and baseline metadata, not a confirmed EP45 WorldSvr runtime.
No real Upgrade Core case logs are available through these connected tools.
Do not conflate the unrelated Warp 485 disconnect with this incident.

**No tested fix:** The collector and analyzer are diagnostic utilities only.
Do not merge an inferred WorldSvr patch without isolated gameplay regression
and an observed root cause.

## 2026-11-21: Verified static protocol-name evidence (not a runtime root cause)

A read-only GitHub Actions archive scan of `patmalnieksgatis-netizen/cabal-ep36`:
https://github.com/patmalnieksgatis-netizen/cabal-ep36/actions/runs/44897997600
scanned 58 text files in `CABAL_EXTRA_SOURCE.tar.gz` and 135 in
`CABAL_V282_LIVE_MERGE_CANDIDATE_v14.zip`.

The archived `WorldSvrRealm/WorldSvr/PacketManager/Protodefs.h` contains:

- `CSC_ENCHANTCORE = 280` — an old server startup log registers this as
  `OnCSCEnchantCore`; public game logs show it can handle **Force Core option
  grants**, so do **not** blindly route Normal Upgrade traffic to 280.
- `CSC_UPPERGRADECOREENCHANT = 950`
- `CSC_REQ_UPPERGRADECOREENCHANT2 = 951`

These are historic names only. Their direct relationship to the active v291
client's Normal Upgrade request or Perfect Core is **not verified**. No complete
Normal Upgrade handler was found in the archived extender sources; `EventAlert.cpp`
uses the `SHF_UPGRADECORE` bitshift for **item drop/creation event matching**, not
as proof of an item-upgrade request handler.

**Critical next step (actual game integration):** Observe an Upgrade Core C2S
request in the active v291 client, then inspect the corresponding live WorldSvr
opcode registration/handler and reply, with exact packet sizes. If the server
logs an unregistered command, register a correctly validated implementation;
if native handler returns error, trace grade/slot/item validation; if reply is
misparsed, adapt only the proven S2C fields. Avoid an unverified numeric
remapping of `280`, `950` or `951`.

The local test VM `192.168.56.101` is host-only and not reachable by ChatGPT
or GitHub Actions runners. No live disconnect trace has been retrieved, so there
is still **no verified functional patch**.

## 2026-11-21 archived LFS cross-check — do not blindly restore the SCPs

Static audit (GitHub Actions): https://github.com/patmalnieksgatis-netizen/cabal-ep36/actions/runs/44898529634

- The original LFS `CABAL_FOR_CHATGPT.zip` has matching baseline `Core.scp`
  (12,984 bytes) and `Limit_Upgrade.scp` (6,762 bytes) files. The WorldSvr
  settings show `MaxUpperGradeCoreEnchantLv=12` consistently.
- The separately archived `CABAL_VPS_FULL.tar.gz` has a modified
  `home/data_main/cabal/Data/Core.scp` (13,753 bytes) and
  `Limit_Upgrade.scp` (8,016 bytes), versus backup copies of 12,984 and
  6,762 bytes. Detailed diff proves `Core.scp` adjustments are chiefly
  Normal Upgrade success odds for +3 to +7 (900 versus original 800–440
  in server-scale units); the column schema did **not** change.
- `Limit_Upgrade.scp` modifications concern extra levels/costs and should
  not be conflated with Normal Upgrade. Old SCP changes are not proof
  of the user's November v291 client disconnect.
- The archive contains a separate old client executable, not the active
  v291 signed `CabalMain.exe`; there is no verified v291 live WorldSvr crash
  trace or proven packet ABI for Normal Upgrade here.
- **Action:** do not revert these SCP files or remap packet opcodes blindly.
  Fix requires correlating the current client action with its active WorldSvr
  handler/response in the isolated VM first. No game fix was deployed.

## 2026-11-21 archived WorldSvr log scan (new verified result)

Github Actions native-server archive log audit:
https://github.com/patmalnieksgatis-netizen/cabal-ep36/actions/runs/44899777807

The historical VPS archive contained **50 archived WorldSvr_01_01 / _01_16 log files** in the bounded scan. **156** log lines matched broad upgrade-related terms across **3** files; **zero** of those lines matched error/disconnect categories. No exact `OnCSC...` normal-upgrade handler trace or actionable crash signature was recovered. These are **historical October logs, not the active November v291 disconnect**. They do not justify an opcode remap or binary patch.

The only missing decisive evidence is a reproduced request/reply trace or current WorldSvr error log from the reachable Windows-hosted VM. The ChatGPT connector environment has **no TCP/SSH route** to VirtualBox host-only `192.168.56.101` or to `F:\\CABAL_291_TEST`. GitHub-hosted Actions cannot reach those private hosts either. Use the existing read-only collector on the local VM and do not deploy any speculative binary patch.

## 2026-11-21 LIVE ROOT-CAUSE EVIDENCE — OPCODE 951

User supplied an authentic WorldSvr_01_01 stderr trace at 11:38:01:
\`OnCSCUpgradeCoreEnchant(): Invalid recvPacket->wPayLoadLen or recvPacket->escapeSlotCount\`,
\`'OnCSCUpgradeCoreEnchant' fail (Proc/Enchant.cpp:1664)\`,
\`UsrMap Fail : MainCmd(951)\`, followed by explicit \`close()\`.
This proves the server receives the 951 packet and aborts that client session at its
**input packet shape validator**, not at success odds or upgrade item effects.

The archived native \`home/data_main/cabal_bin/WorldSvr\` has SHA256
\`caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3\`,
matching the previously observed WorldSvr binary identity. Static disassembly:
https://github.com/patmalnieksgatis-netizen/cabal-ep36/actions/runs/44900466989

The error string VA is \`0xC17798\`, exact line-1664 branch is around
\`0x7AC0F0..0x7AC215\`. **Proven validator input contract**:

- \`WORD [C2S_packet + 0x02]\` is declared packet length.
- \`WORD [C2S_packet + 0x11]\` is \`escapeSlotCount\`.
- Declared length **must equal** \`0x8B + 2 * escapeSlotCount\` (139 + 2N).
- \`escapeSlotCount <= 0x209\` (521).
- \`BYTE [C2S_packet + 0x10]\` (coreSlotCount) is constrained to 1..60.
- \`WORD [C2S_packet + 0x0E]\` main inventory slot is constrained to <=521.
- A closely related second handler at 0x7ADA70 uses the same length formula,
  but its main-slot upper bound differs (0x2E = 46).

The user-observed error is specifically the first length/count check, **before**
the later core-slot and item-grade logic.

**Concrete next step to fix**: capture only the live numeric packet shape once
at breakpoint \`0x7AC0F0\` on an exact SHA-matched test WorldSvr, using
\`Probe-Opcode951-Live.py\`. It prints **actual declared length**, **escape count**,
**expected length**, **core count**, **main slot**; it detaches immediately.
This is enough to tell whether the v291 client emits a different 951 body
shape or has a shifted count/length field. Then apply a narrow **verified**
normalizer to the LAB client's outbound packet or server's C2S handler,
preserving item/slot validation and all working upgrade paths. Do not just
remove the server's rejection branch or fake upgrade success.

No game patch deployed yet: the connected ChatGPT environment cannot reach the
VM's host-only network. An exact source-safe packet guard with eight synthetic
test cases was saved as \`Opcode951-Contract.py\` and
\`tests/test_opcode951_contract.py\`; these are *not* functional upgrade patches.

## 2026-11-21: Exact live 951 packet CAPTURED; two-byte candidate proved against archived WorldSvr

The user's **real hardware breakpoint capture** on the TEST VM:
- Native running WorldSvr SHA256: \`caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3\`.
- MainCmd 951 declared packet length **259**; legacy server expected **139**;
  delta **120 bytes**.
- \`escapeSlotCount\` at old offset \`0x11\`: **0**; \`coreSlotCount\`: **1**;
  main slot **129**; first core entry at offset \`0x13\`: **42**.
- First 192 captured bytes contain one nonzero 2-byte core entry, the rest of
  the following array bytes are zero. The **last 67 packet bytes were NOT
  captured**, so the whole extended layout is not verified.

**Reversible LAB-only compatibility hypothesis**: change the *single* old
WorldSvr opcode-951 validation length-base immediate from **139** to **259**
while retaining \`2 * escapeSlotCount\` and the entire item/slot validation
path. At virtual address \`0x7AC0FD\` opcode \`48 8d 94 12 8b 00 00 00\`
becomes \`48 8d 94 12 03 01 00 00\` (changed bytes file offsets
\`0x3AC101\` and \`0x3AC102\`).

This was verified **against the archived, SHA-matched actual 10,596,184-byte
WorldSvr ELF**, without executing or writing the candidate:
https://github.com/patmalnieksgatis-netizen/cabal-ep36/actions/runs/44904164461

Candidate SHA256:
\`08b3316be18d1ffe57d7a88d35ea99e0e4e4b2c3687b5b1a1829512f53a5052f\`.

Local isolated deployment wrapper was packaged as
\`CABAL_951_PATCH_TEST.ps1\` plus its embedded Linux Python patcher.
It verifies original SHA, checks exact disassembly bytes, backs up before
the mutation, installs exactly two changed bytes, restarts **only**
\`WorldSvr_01_01\`, checks the process running SHA and has explicit rollback.
No \`gdb\`, \`apt\` or VM internet required. This package was created as
a conversation download artifact, not a committed WorldSvr binary.

**Not applied on the actual user's VM by this assistant** because it is
VirtualBox host-only. No successful normal upgrade has been tested yet.
If any in-game upgrade or persistence test fails, revert using the rollback
action. Because the old length-base is replaced, old 139-byte opcode-951
clients may no longer work on this LAB WorldSvr. Force/Chaos/Divine use
distinct handler code and remain unmodified, but require smoke tests.
