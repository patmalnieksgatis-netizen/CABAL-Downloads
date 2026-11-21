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

