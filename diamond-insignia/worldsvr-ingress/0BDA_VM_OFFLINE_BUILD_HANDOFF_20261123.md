# CABAL v291 — 0x0BDA WorldSvr hookup: offline build handoff

Date: 2026-11-23. Target: EP36_291_TEST. Actual installation: NOT DONE.

## Known baseline

- On 2026-11-23 WorldSvr_01_01 was running as PID 438, WorldSvr
  SHA256 caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3.
- Current game extension baseline hash of /usr/lib/cabal/lib.so:
  6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab.
- Known separately verified backup:
  /root/cabal_diamond_backup/lib.so_before_diamond_20261122.
- Prior Nov 22 sidecar/LD_PRELOAD and original module replacement
  attempts caused exit 78, and at least one automatic rollback initially
  failed because Supervisor stored command and running plugin chain differed.
  The user subsequently manually restored WorldSvr and checked game OK.
- No VM snapshots. Do NOT retry a direct live lib.so swap or
  supervisorctl reread/update without a new verified recovery mechanism.

## Source code prepared

- Apply-DiamondV14Real0BDAClone.py adds the candidate 0x0BDA branch
  to the original v14 ProcSystem::DoProcessDataCtx SOURCE COPY only,
  based on pinned 64-source-file manifest and critical source SHA.
- DiamondReal0BDAIngressPort.h defaults to original dispatcher pass-through.
  Original Platinum 0x0B10 and Merit 0x09F3 remain unchanged.
- Build-DiamondV14Real0BDAOffline.py performs the actual C++ compiler
  and linker step in a new /tmp tree. It checks the source manifest,
  exact baseline original lib.so SHA, 100+ original dynamic exports,
  preserved exported-symbol set, and offline-only SONAME.
  It reports how many original exported C++ function RVAs shifted.
  This matters to other hardcoded WorldSvr hooks and can account for
  incompatibilities; it does NOT itself prove the root cause of exit 78.
- Stage-DiamondV14-0BDA-Windows.ps1 runs all those OFFLINE steps from
  Windows against EP36_291_TEST with verified source and baseline paths:
  it downloads pinned GitHub code, sends code to /tmp over SSH,
  then runs the offline builder. No game service control, SQL,
  LD_PRELOAD or live WorldSvr changes.

## Verification

GitHub Actions run 45253275857: Diamond v291 passive WorldSvr
ingress safety PASS. The source hook, non-consuming behavior,
offline builder validation and PowerShell wrapper syntax are tested.
This is NOT a build against private v14 sources in CI.

## What is needed for the first playable test

The user can execute the offline Windows staging wrapper once, and
share /tmp/cabal_diamond_v291_0bda_offline_build_20261123/OFFLINE_BUILD_RESULT.json
for actual ABI/RVA comparison.

Even if the offline shared object builds, the game rank-up is still
BLOCKED by:
(1) exact live 0x0BDA selection proof and authoritative owner lock;
(2) verified same-stack B0/999 displayed count;
(3) WorldSvr native inventory + WExp update synchronized with
    DBAgent cmd46/47 durable save and the actual rank state;
(4) confirmed v291 S2C success/error reply ABI and relog/restart;
(5) a restorable isolated test VM for any mutating integration experiment.

NO VM, MSSQL, active lib.so or client file has been modified.
