# Exact live v14 WorldSvr source integration — 2026-11-22

The user supplied `CABAL_V282_SOURCE_v14.tar.gz`, extracted from `/root/CABAL_V282_LIVE_MERGE_CANDIDATE_v14/source_tree/src` on running `EP36_291_TEST`. This is the **currently matching** library source, unlike February's older `CABAL_FOR_CHATGPT.zip`.

## Proven baseline parity to user's running `/usr/lib/cabal/lib.so`

Active SHA256: `6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab`. Build the source with `g++ -std=c++17 -O2 -fPIC -shared -Wl,--no-undefined -Wl,-rpath,/usr/lib/cabal -ldl -lpthread -lodbc` over all `*.cpp`, except **`hooks/Handlers/C2SHandler.cpp`** and **`hooks/Packets/EventPassInventoryPersistV282.cpp`** (these two aren't linked into active `lib.so`).

The rebuilt unpatched source yields exactly **193,496 bytes**, same as live; **144 identical exported symbol names**, and all **136 ELF-exported symbols with recorded sizes have identical sizes**. Live and rebuilt files aren't byte-identical (compiler/toolchain/link ordering may differ); never claim identical SHA or proven runtime behavior. This is a much stronger baseline than the earlier archived version.

Verified original source input SHA256:
- `source_tree/src/hooks/Handlers/ProcSystem.cpp`: `59b44f522a8cfd189516b1f7c6e2434a1c7e5249c6d563b91178c3a2cc95bc19`
- `source_tree/src/include/Types.h`: `32ae9931ac8e779c9de58a25b6e903f03ecfdd46324c334f3a417f8a4be0fa3c`

`source_overlay/ProcSystem.cpp` has the **same exact SHA** as `source_tree/src/hooks/Handlers/ProcSystem.cpp`. Other files in the overlay, including OnEventPass.cpp, differ from current source_tree and **must not be blindly copied**.

## Patch applied, full plugin built

Using the existing `worldsvr-ingress/DiamondIngress.h` and `DiamondBoundIngress.h`, the source copy was patched in exactly two existing files plus added native ABI headers:

1. Add `size_t iLen` to `PROCESSDATACONTEXT` after `cpPacket` in Types.h; enforce `offsetof(...,iLen)==16`, matching the user-archived C2SHandler.cpp.
2. Inside `ProcSystem::DoProcessDataCtx`, after reading the main command, look for opcode **0x09F3** (Merit Mastery), 18-byte classic packet and Mastery ID 159–474; call the already-built **DiamondBoundIngress::Process** with exact server-owned `pUserCtx`, packet pointer, and trusted input length.
3. Also observe the existing Platinum grade-up **0x0B10** packet length and count, without logging contents. Never intercept/consume 0x0B10 and never claim it is Diamond-exclusive.
4. Preserve **all original WorldSvr fallback dispatch** and existing EventPass, Costumes, Dungeon, and other code. The optional log gate is `CABAL_DIAMOND_PASSIVE_OBSERVE=1` with a cap of 16 messages. No game WExp/SQL/inventory changes.
5. The compiled **default** source explicitly excludes `DIAMOND_ENABLE_SHADOW_TRIAL`, and therefore cannot apply synthetic or real Diamond purchases. The alternative lab-only build, never for active VM, depends on libDiamondNative.so and exports `cabal_diamond_proc_bind_shadow_clone_v1`, requiring a trusted test-host binding restricted to synthetic UserNum=900001.

Result of standalone actual-source builds:

- `lib.so_diamond_v14_probe`, SHA256 **`a64eea7bf50881dbbdd08ecd1d74b7bde5b072fb65b55859c120dd863ba77ffe`**, compiled and linked. All original 144 exported symbols preserved, and all 136 original sized symbols preserved apart from **ProcSystem::DoProcessDataCtx**, whose body now contains the Diamond branch. No new library dependencies; maximum GLIBC requirement 2.38 (same as current).
- **Lab-only shadow build** compiles and exports the native C bridge, but needs a verified host resolver and **should not be installed into the active server**.
- Existing owner's real private staged 116,812-byte Diamond SCP native integration test PASS for synthetic account grade2, replay/failure rollback, and Platinum passthrough. This does **not** test production accounts or SQL.
- A non-WorldSvr process can load the default candidate with `LD_PRELOAD=... /bin/true`; its constructor correctly skips game hooks when process isn't named WorldSvr.

The user-facing conversation archive `CABAL_V291_Diamond_v14_Bridge_20261122.zip` contains the compiled default candidate, complete privately patched v14 source, precise diffs, and a verifier. It must **not** be characterized as a finished playable Diamond feature. The private active extension source archive was **not uploaded to GitHub**.

## Remaining required actual-game integration

The current binding processes only **read-only observation** and the synthetic lab C world-bridge: authoritative actual-user inventory item 33554961 deduction, 30,000 WExp, database persistence, Diamond rank-up response and reply replay/idempotency are not yet implemented; real request opcodes must be confirmed in the current v291 client. Do not install a test shadow backend into the real game or claim gameplay activation.

Run the default candidate **only on a snapshotted VM clone**, after verifying the backup SHA. Docker CLI can hang on that host, so use the host's `/proc/<WorldSvrPID>/root` and supervisor control once its availability is verified. Atomic renaming, not writing into a memory-mapped inode, is required. Both WorldSvr_01_01 and WorldSvr_01_16 use the same active `/usr/lib/cabal/lib.so`.

Next tasks for Codex/local execution: compile and install the source-matched candidate in isolated clone; observe exact on-wire C2S Merit packet when clicking grade-up or Mastery; implement trusted full account/char and real DB+inventory atomic commit and correct S2C reply; only after tests add explicit production opt-in.


## Updated isolated-VM installable passive probe build

A second compile of the **same source tree** with flag \`-DDIAMOND_V14_PROBE_AUTO_OBSERVE\` produces the **isolated test-VM probe** as \`lib.so_diamond_v14_probe\`. This compile flag logs **at most the first 16** C2S Diamond Mastery 0x09F3 candidates and original Platinum grade-up 0x0B10 packet lengths/counts, without requiring edits to supervisord environment. It still performs **no Diamond game purchase, inventory, SQL, WExp, response or item changes**.

- Probe SHA256: **\`49e8cbaecb5e723ca20d4af3ac31eca887da3cac6432b4b1560b99075a49379f\`**
- Actual baseline active SHA256: **\`6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab\`**
- ELF symbol size check: all **136** original sized exported names retained; the **only** size change is \`ProcSystem::DoProcessDataCtx\` (326→624 bytes), exactly the function containing the new ingress logic.
- No new ELF dependencies or GLIBC beyond 2.38. A standard non-WorldSvr LD_PRELOAD load test passed.
- Conversation artifact \`CABAL_V291_Diamond_v14_VM_Probe_20261122.tar.gz\`, SHA256 \`18f4176be5baf5fd86beeef08c7cfd1c0447465a7d2c42601f83f8c1ffa67f7b\`. It has the probe plus a **VM-host no-Docker** SSH helper \`deploy_probe_VM_ONLY.sh\` with preflight, activate-probe, logs and rollback commands. The helper refuses unknown hostnames, wrong hashes, missing backup, missing supervisorctl or unsatisfied shared-library dependencies before any live replacement. It uses atomic rename into the container filesystem via \`/proc/<supervisord PID>/root/usr/lib/cabal/lib.so\` and only then supervisorctl restarts both WorldSvr instances. This helper was shell-syntax-checked locally but **not executed against the owner's VM**, so its environment assumptions must be validated in the preflight stage.
- The full patched private v14 source plus diffs and test code is in conversation artifact \`CABAL_V291_Diamond_v14_Bridge_20261122.zip\`; private source itself was not put in public GitHub.

**Deployment truth:** This is **not Diamond/Mandarat gameplay activation**. The probe is for confirming whether the client's real commands actually reach the installed C2S path before building a real host-authenticated item 33554961/WExp/SQL commit and S2C serializer. Never describe it as finished live Diamond.


## Actual VM outcome, 2026-11-22 11:46 UTC: probe start FAILURE and successful rollback

The user ran \`preflight\`, PASS (active original 6679e46a... and probe 49e8cb...), followed by \`activate-probe\` on EP36_291_TEST. \`WorldSvr_01_01\` stopped; Supervisor spawned PID 31747 at 11:46:38.684; **process exited status 78** at 11:46:38.731 (~47 ms). The deploy helper automatically restored original \`lib.so\` and restarted WorldSvr instances. After rollback:

- SHA256 of active \`/usr/lib/cabal/lib.so\` again **6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab**
- \`WorldSvr_01_01\` RUNNING PID 31748; \`WorldSvr_01_16\` RUNNING PID 31809; log shows \`Complete Loading Data\`
- Boot log at UNIX epoch 1795347999 = 2026-11-22 11:46:39 UTC includes \`python3.12\` and \`WorldSvr_01_01\` entries; do NOT assume these correspond to failed PID 31747 because that process exited at 11:46:38. Logs do not yet identify why the failed process returned 78.
- Source search found NO explicit \`exit(78)\` / \`_exit(78)\` / \`return 78\` in the patched extension. \`exit status 78\` often conventionally denotes config error but **not proven** here.
- **ELF discrepancy discovered after failure:** running original library's DT_SONAME is \`lib.so\`, while compiled probe's dynamic section lacks SONAME. This is not proof of failure since the ELF loader does not generally require SONAME for LD_PRELOAD. Need verify runtime entrypoint/preload setup and failed-process stderr before creating or deploying revised library.
- A different \`SIGSEGV\` from previous day 2026-11-21 14:21 is unrelated to this attempt. Some earlier broad grep commands missed failure due to \`grep -m 3\` or shell quoting; future diagnostics should target supervisor config \`[program:WorldSvr_01_01]\`, stderr/stdout around 11:46:38 with \`grep -a\`.
- **Do not retry the same probe** pending root cause. No Diamond gameplay features enabled; original server restored.
