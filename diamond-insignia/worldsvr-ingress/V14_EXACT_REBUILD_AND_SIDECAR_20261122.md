# v291 Diamond: source-exact v14 reconstruction and ABI-preserving ELF interposition (2026-11-22)

## Deterministic reproduction of running v14 lib.so

**Breakthrough:** From user's `CABAL_V282_SOURCE_v14.tar.gz`, building the **unchanged** `source_tree/src` in the correct explicit ordered list with:

```sh
g++ -std=c++17 -O2 -fPIC -shared -Wl,-soname,lib.so -Wl,-rpath,/usr/lib/cabal -o lib.so ${ordered_cpp_files[@]} -ldl -lpthread -lodbc
```

produces an exact **bit-for-bit SHA256 match** to the actual running `/usr/lib/cabal/lib.so`:

```
EXPECTED=6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab
ACTUAL=6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab
ORIGINAL_V14_EXACT=PASS
```

The ordered source-file list / reproducible build script are in the user's conversation artifact `CABAL_V291_Diamond_Sidecar_ReadOnly_20261122.zip`, file `rebuild-original-v14-exact.sh`. The private original v14 sources are **not uploaded to GitHub**.

Older rebuilt candidates did **not** preserve internal function RVAs. Unpatched rebuild with a different source linker order gave original `ProcSystem::DoProcessDataCtx` RVA `0x68e0` vs rebuilt `0x5f10`. Even after exact source file order, adding Diamond directly to ProcSystem changes at least 109 exported function RVAs, because of the increased function size and optimizer reordering. This may upset existing plugins or ABI / hardcoded pointers; **not a proven root cause of Supervisor exit 78**. Both prior plugin replacement attempts failed and correctly rolled back.

## Read-only sidecar instead of replacing original lib.so

ELF static disassembly of original `ProcSystem::Attach` reveals `mov rdx,[rip+...] ` reading **R_X86_64_GLOB_DAT** GOT relocation at original `lib.so` RVA **0x16f78**, symbol:

`_ZN10ProcSystem16DoProcessDataCtxEPvP18PROCESSDATACONTEXT`.

Therefore a separate `libdiamond_v291_sidecar.so` loaded **before** original `lib.so` can symbol-interpose the handler while preserving the *entire* original active binary and its layout. Sidecar exported same symbol and delegates by `dlsym(RTLD_NEXT,...) `. In this first passive stage, records only sanitized C2S packet opcode 0x09F3/0x0B10 and length/Mastery ID, limited to first 32, behind environment `CABAL_DIAMOND_SIDECAR_LOG=1`, then calls original handler unchanged. No account/inventory/SQL/WExp changes.

**Offline tests performed and PASS:**

1. Real original v14 `lib.so` `dlopen` with sidecar `LD_PRELOAD`: GOT RVA `0x16f78` resolves to sidecar function, **not** original: `LIBSO_SYMBOL_PREEMPTION=PASS`.
2. Synthetic mock-WorldSvr dispatch: 0x09F3, 0x0B10 and malformed packet all forwarded, original return 12345 preserved. Log captured only 0x09F3 Mastery id=159 and 0x0B10 packet length, with `passthrough=YES`.
3. New library only 16,296B, `libdiamond_v291_sidecar.so` SHA256 `2118cebb63de7a88f1eb666dc2d379d602fd66625f706e2298f36339ceb6115e`. Package ZIP `CABAL_V291_Diamond_Sidecar_ReadOnly_20261122.zip` SHA256 `861f67d42107363de2cfdf36f37ad2c7237bdb0d7b80e4cd3eada95a234e5277`.

**Not yet installed/tested** on owner's VM. Actual VM `LD_PRELOAD`/supervisor env and plugin ordering must be inspected first. No install instructions should modify live `lib.so`. A full rollback script for the service launch configuration and isolated snapshot is needed before a VM test.

**Still NOT complete Diamond gameplay** — authoritative item 33554961/WExp debit, real SQL transaction, S2C serialization and client state remain unimplemented.


## Live Supervisor launch configuration mismatch — 2026-11-22 12:xx

User showed \`ps -p 3414 -o args=\` = \`/usr/bin/python3 /usr/bin/supervisord\`. Found on-disk \`/etc/cabal_scripts/cabal_services/cabal_server1.conf:73\` program \`WorldSvr_01_01\`; line 75 command uses:
\`CABAL_EVENTPASS_CATALOG=1 LD_PRELOAD="/usr/lib/cabal/lib.so /usr/lib/cabal/libchilkat-9.5.0.so /usr/lib/cabal/libPolyHook_2.so /usr/lib/cabal/libZycore.so.1.4 /usr/lib/cabal/libZydis.so.4.0 /usr/lib/cabal/EP36CostumeCore_v1_5_3020fix.so" exec /usr/bin/WorldSvr_01_01 -c\`.

**But actual live WorldSvr host PID 129045** (Supervisor reports inside-container PID 41752) has environment:
\`LD_PRELOAD=/etc/cabal/migration_tools/ep36-costume-trial-v1/mileage-v1/EP36CostumeMileage.so /usr/lib/cabal/lib.so /usr/lib/cabal/libchilkat-9.5.0.so /usr/lib/cabal/libPolyHook_2.so /usr/lib/cabal/libZycore.so.1.4 /usr/lib/cabal/libZydis.so.4.0 /usr/lib/cabal/guardian-v1/GuardianArcana-v1.so /usr/lib/cabal/skillbook291/SkillBook291.so /usr/lib/cabal/cashshop291/CashShop291.so\`.

**Important deployment blocker:** disk \`cabal_server1.conf\` and running process environment differ materially. It may be an unsaved or alternate Supervisor program configuration, a runtime change, or a launcher override. No evidence yet that this file is the actual loaded definition. Do not blindly \`sed\` or \`supervisorctl reread/update\`; that could remove CostumeMileage, GuardianArcana, SkillBook291 and CashShop291 on next restart. Need identify Supervisor's actual included configuration, environment= overrides, command, and ensure proper backup. The correct sidecar LD_PRELOAD place is directly before \`/usr/lib/cabal/lib.so\` and after \`EP36CostumeMileage.so\` if applicable; do not change rest of order.

Another found file \`/etc/cabal/migration_tools/ep36-costume-trial-v1/build.sh\` references exit code 78 in a test tuple, but it is **not evidence** that this test script executed or generated previously observed WorldSvr exit status 78. Diagnose separately.

Live status in that query: WorldSvr_01_01 RUNNING pid 41752 and WorldSvr_01_16 RUNNING pid 35626. Original \`lib.so\` was rolled back after failed v14 SONAME candidate. No sidecar deployed.

Next: read-only inspect main \`/etc/supervisord.conf\` [include] stanza and full live program block, as well as paths containing \`EP36CostumeMileage.so\`, then build minimal reversible override. Continue with original \`lib.so\` unchanged.


## Guarded VM sidecar installer artifact (prepared, not yet run), 2026-11-22

The user confirmed that the running process \`WorldSvr_01_01\` uses the full Mileage/lib.so/Chilkat/PolyHook/Zycore/Zydis/Guardian/SkillBook/CashShop chain, while the persisted \`/etc/cabal_scripts/cabal_services/cabal_server1.conf:75\` is **stale**, currently pointing to original lib.so/Chilkat/.../\`EP36CostumeCore_v1_5_3020fix.so\`. User also confirmed \`/etc/supervisord.conf\` includes both \`/etc/supervisor/conf.d/*.conf\` and \`/etc/cabal_scripts/cabal_services/*.conf\`. Actual active config source remains unproven until \`supervisorctl reread\` returns \`WorldSvr_01_01: changed\`.

A self-contained user-facing, VM-host-only archive was created locally:

- \`CABAL_v291_Diamond_Sidecar_VM_Guarded_20261122.tar.gz\` SHA256 \`6c442345606d22940e9a76cd2cede86cc50cabc2bb0c944633ae37fed1c40a9c\`.
- Contains \`diamond-sidecar-deploy-v1/deploy_sidecar.py\`, read-only ELF \`libdiamond_v291_sidecar.so\`, \`DiamondSidecarProbe.cpp\`, and Latvian README.
- \`preflight\`: NO changes; checks VM host PID 3414, live original \`lib.so\` SHA, sidecar SHA, 01/16 RUNNING, actual host PID and \`LD_PRELOAD\`, current plugin path existence, stale on-disk command structure, preservation of additional critical runtime feature flags.
- \`activate\`: backup exact stale disk conf, preserve actual live preload, install a NEW sidecar .so without touching lib.so, reconstruct only \`WorldSvr_01_01\`'s stored \`LD_PRELOAD\` from actual running process (insert sidecar immediately before original lib.so; keep Mileage and the other plugins), check sidecar can load via target chroot Python, call \`supervisorctl reread\` and require 01 change, perform \`supervisorctl update WorldSvr_01_01\` only, start if autostart=false, verify new PID RUNNING and sidecar present in env/maps, original lib.so SHA unchanged, and all old preload entries preserved.
- Any deployment failure after mutation captures \`/root/cabal_diamond_sidecar_v291_attempt_diagnostic.txt\` and immediately attempts target-only rollback to the previously **running** preload chain. Original historical on-disk config backup preserved at \`/root/cabal_diamond_sidecar_v291_state_20261122.disk-original.conf.bak\`; rollback reconciles disk to original *running* version, rather than reintroducing stale stored command.
- \`status\` and \`rollback\` supported.
- Script syntax and exact-config transformation unit tests PASS locally. **The script has NOT been run on the owner's VM**, so expect possible environment errors; do not assert installed success.
- This is only passive C2S observation for 0x09F3/0x0B10 (client packet identity and length); no real Diamond UI, inventory, WExp, MSSQL, payment, S2C data implemented.
