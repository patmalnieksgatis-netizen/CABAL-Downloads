# CABAL 951: automatic restoration of the two working RAM-only patches

## User request (2026-11-21)
The user confirms ordinary Upgrade Core works through **+20** and the Safeguard feature works after the **two** RAM patches, and requests that these survive WorldSvr/VM restarts without manual commands.

**Important:** Both original RAM changes *still disappear from process memory* on restart. This design does NOT modify the original WorldSvr ELF, because previous test-VM on-disk patch installations (V1 and V2) each produced \`supervisorctl ... ERROR (spawn error)\` and required automatic rollback. Instead, a persistent \`systemd\` service monitors for new WorldSvr PIDs and automatically reapplies both changes. This introduces a brief post-restart gap, normally a few seconds, before both patches are active.

## Standalone installer delivered in this conversation

- Windows PowerShell 5.1 launcher: \`CABAL_951_AUTO_RESTORE.ps1\`
- Full development bundle, native static helpers, source, tests and README: \`CABAL_951_AUTO_RESTORE_BUNDLE.zip\`
- SSH: \`root@192.168.56.101\` (VirtualBox host-only VM)
- Remote Docker: \`cabal_main\`
- Supervisor: \`WorldSvr_01_01\`
- Remote systemd unit: \`/etc/systemd/system/cabal-951-compat.service\`
- Remote root-owned directory: \`/opt/cabal-951-compat\`
- Actions: \`install\`, \`status\`, \`uninstall\`
- Startup: \`systemctl enable --now cabal-951-compat.service\`. Requires Docker, Python3 and systemd already installed; **not** \`gdb\`, \`apt\` or VM Internet.

Remote daemon \`watchdog.py\` discovers the active WorldSvr Docker PID by \`supervisorctl pid\`, resolves its host PID using \`/proc/*/status NSpid\`, verifies **running and on-disk** original WorldSvr SHA-256, and applies in sequence:

1. Base opcode 951 length: \`0x7AC101: 8B 00\` → \`03 01\` (139 → 259 byte base). Native helper \`runtime_patch_951_linux_amd64\`, static SHA-256 \`ce455a77e4fe19bbf560917056f59db2e183fedc59472e93a7b638c8ba4d18b7\`, invoked with \`apply HOST_PID 0x7ac0f0\`.
2. Safeguard array base: \`0x7AD74B: 8B 00\` → \`03 01\` (\`packet+0x8B\` → \`packet+0x103\`). Native helper \`safeguard_offset_patch_linux_amd64\`, static SHA-256 \`3edb966a80335823f70f08405e41500f1562f64c40f11215a3bead9d6a11d6de\`, invoked with \`apply HOST_PID 0x7ad73c\`. This helper **requires base patch active** before applying.
3. Verify unchanged Docker PID; print \`BOTH_PATCHES_ACTIVE host_pid=... inner_pid=...\` to \`journalctl\`. Check the same original SHA on every new process; retry after transient errors. Neither patcher alters SQL, files or supervisor state, and both are idempotent when already applied.

Original WorldSvr executable exact SHA:
\`caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3\`
Exact executable container path:
\`/etc/cabal/migration_tools/ep36-costume-trial-v1/native/WorldSvr_01_01\`.

PowerShell commands:

\`\`\`powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\CABAL_951_AUTO_RESTORE.ps1" -Action install
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\CABAL_951_AUTO_RESTORE.ps1" -Action status
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\CABAL_951_AUTO_RESTORE.ps1" -Action uninstall
\`\`\`

VM logs: \`journalctl -u cabal-951-compat.service -n 35 --no-pager -o cat\`.

### Safety and scope
- \`install\` is idempotent. SHA and file ownership checks; avoids overwriting unrecognized existing unit/files. No WorldSvr restarts.
- \`uninstall\` removes **only** managed unit/files; preserves current RAM patches until WorldSvr restarts.
- Systemd daemon runs as **root**, necessary for \`ptrace\`. Test VM only.
- Two native helpers were already used on user VM and the combination was user-confirmed to work. **The persistent watchdog installer itself has NOT been run by the assistant on the user's private host-only VM**; user must run the standalone PowerShell installer to actually make reapply automatic.
- Eight Python unit tests of daemon logic and four Python mocked installer tests passed. Native helper SHA and embedded bundle equality independently checked. This is not proof of systemd behavior on the private VM; review status and logs after install.
- The separate **Perfect Core +17** limitation remains outstanding; it is not addressed or changed by this service.

Source archive in conversation contains \`watchdog.py\`, \`installer.py\`, \`test_watchdog.py\`, \`test_installer.py\`, both static native tools and C sources. This is the full reproducible handoff for Codex. Do not repatch the on-disk WorldSvr again merely to persist 951.
