# Diamond integration — 27 November 2026

This checkpoint supersedes claims that loading V28/V29 enables Diamond.
No game installation, SQL change, core replacement, service restart or VM
networking change was performed during this checkpoint.

## Actual operator evidence

The operator's SSH relay reported CH1 `RUNNING`, PID 432, uptime 6m33s.
`/usr/lib/cabal/lib.so` remains SHA-256
`6679e46aa2ee915d97de9501ba027cae3eec153f1cd82e7c16ed47221c63ecab`.
The mapped `/usr/lib/cabal/Diamond291_Startup_V28.so` remains SHA-256
`ec5810489581e7bc10ac17ab96c1c5ff4752e4d53a403e972aca3920ae652857`.
Its message is `DIAMOND_V28_OPEN=BLOCKED_STARTUP_CALLSITE`.

This is **expected forwarding-only V29 behavior**:
`worldsvr-ingress/Activate-DiamondV29-ForwardingOnly.py` explicitly writes
`CABAL_DIAMOND_V28_STARTUP_RETURN=0`. Changing that value would only enable
V28's observer, which neither implements Rank-up nor saves data. Do not
present that change as a Diamond fix or overwrite the pinned original core.

Direct Cloud access to the private VM is unavailable; operator PowerShell
SSH is the execution relay. The evidence above is operator-supplied, not a
direct Cloud inspection of that process.

## Supplied v14 source

Operator supplied `CABAL_V282_SOURCE_v14.tar.gz`, 60,122 bytes, SHA-256
`55336c336cca5e7fff6b34a52300c52172d7b02d063d54aef7f251781b405053`.
It contains `source_tree/src` and `source_overlay`, including existing
ProcSystem, EventPass owner, inventory, persistence and recovery components.
It does not contain a native Diamond implementation or the EP45 Merit XMLs.

The supplied EventPassOwnerV282 header and implementation have identical
non-comment tokens to the dependencies already used in
`native/world-session-bridge/deps/`. Their different file hashes are due to
comments/formatting. Their owner offsets remain UserNum `0x890` and
CharacterIdx `0xA24`; this does not establish native lifetime/locking.
The archive is retained privately, not committed as a public source dump.

## Implemented material decoder correction

`native/grade2-ingress/DiamondWorld48TicketUnits.cpp` previously passed only
the low DWORD of the live 64-bit ItemOption to the B0 proof validator.
Consequently, unknown high option bits could be erased before validation,
allowing a live debit plan which the persisted 30-byte decoder rejected.

The B0 path now passes all eight bytes at slot `+0x18`. The regression checks
each of the 32 high bits under all three supported proof profiles (96
flagged cases) and rejects them before debit planning. Plain 999 remains
accepted only with the existing independent proof. No capability flags were
automatically enabled. Legacy item-class extraction branches are unchanged.

Verification passed: strict C++17 decoder build, ticket selection planner,
gameplay-action fixture, and four static native-helper checks. The helper's
23 anchors were also checked against original WorldSvr SHA-256
`caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3`.
These are local code checks, not an in-game debit.

## New exact client evidence

`native/client291-semantic-proof/verify_rankup_response_contract.py` exercises
the original client instructions in Unicorn, pinned to client SHA-256
`52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`.
No client code bytes are committed. Result:
`native/client291-semantic-proof/rankup_response_contract_20261127.json`.

The response reader at RVA `0x6DA920` reads a status byte at packet `+6`.
Six cases exercise zero, 1, 2, 255, full-stack consumption and absent UI.
The seven-byte packet is placed immediately before an unmapped guard page.
Only the single-byte packet read at `+6` is observed in these paths.

With UI and nonzero status, the actual client instructions:

- subtract cached consumed material units (999 becomes 899 for a 100 debit),
  or call the inventory removal service when the whole stack is consumed;
- subtract the current grade's configured WExp cost from `global+0x7958`;
- write grade 2 at `global+0xAB88`, zero `global+0xAB74`, set the grade-2
  category limit at `global+0xABA4` to 3, and request three category resets.

Zero status or absent UI clears pending state without those state changes.
The packet carries no operation identifier; it depends on pending local
selection/costs. A backend must not replay success or use the response as
proof that its own mutation was saved.

The material getter at RVA `0x7FAE98` follows the actual B0 metadata path
through `0x7FFF5C`/`0x82F8F8`: stack limit >=2 means it reads the DWORD at
client item `+0x80`. Cases 1024 and 65536 distinguish this from low10 and
low16 masking. The actual setter at `0x802664` writes the full QWORD at
`+0x80`; high option bits are not retained by that B0 count update.

The GUI, inventory container and catalog services in this harness are
fixtures. The actual quantity getter/setter, WExp getter/setter, grade
write and category-limit instructions execute unchanged. Success cases stop
before final GUI rendering. This proves the exercised client reader
contract; it does not prove original EP45 server serialization, live
session authority, saved ItemOption mapping, SQL commit, relog persistence,
mastery effects or complete gameplay. Production reply gates remain closed.

Reproduce using `unicorn==2.1.2` and the private exact client:

```sh
python3 native/client291-semantic-proof/verify_rankup_response_contract.py \
  /private/CabalMain.exe --output /tmp/rankup-contract.json
```

## Remaining concrete integration dependencies

1. Bind a real native session authority and per-owner save fence to
   `DiamondNativeRankUpV20`, retaining ownership through asynchronous cmd47
   and persisted reconciliation. Existing `begin`/`finish` callbacks and
   `readLockedState` have no real host provider in this branch.
2. Implement native mutation/reload and durable Diamond state together:
   inventory, WarExp and account progress cannot disagree with ordinary
   WorldSvr/DBAgent saves. The SQL prototype alone does not provide this.
3. Obtain the previously prepared Diamond/EP45 inputs, then implement their
   actual effects. The uploaded v14 extension tree is not those inputs.
   A bounded operator search of `/root` and `/tmp` found only the v14 source
   archive. A Windows Downloads/Desktop search for the already prepared
   Diamond ZIPs and `EP45_meritsystem*.xml` has been requested. Do not repeat
   the completed V35–V37 audit instead of using the recovered inputs.

No functional Diamond deployment package is ready. Current loaded module
is still forwarding-only; retain all original working systems.
