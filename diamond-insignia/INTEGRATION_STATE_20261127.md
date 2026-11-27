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
3. The donor-input dependency is now resolved by the uploads below. Do not
   request the XMLs or repeat a Windows file search. Implement actual native
   effects and point/slot synchronization using the recovered definitions.

No functional Diamond deployment package is ready. Current loaded module
is still forwarding-only; retain all original working systems.

## Continued after the sources and codec ZIP uploads

Received `CABAL-DIAMOND-SOURCES-1bec4d3ce4.zip` (SHA-256
`4b9f6b38098a49ea18e0c4db11f942fe27ef9732beee705f07adffcdb12de99e`)
and the original static client codec report ZIP (SHA-256
`603c70de796fb627b173c9de30bc271695cfbdd3f98a1ba9fac6c0f35df0923d`).
The source manifest is a **21 November snapshot**, not a fresh live server
inspection. The codec ZIP contains a report, not another native module.

`native/mastery/recover_donor_catalog.py` validates archive paths, source
manifest hashes and exact donor profiles. Bounded raw-DEFLATE decoding after
the known first-four-byte XOR recovers both original EP45 XMLs:

- definitions: `297078e4cff0918280c824252c4b46e5b17e15a4c57b941b75e8d9f3081c1b9e`;
- messages: `cd627645e7c4d7aa7d5fff66d8dbcf0faa4c8c95dc776fe152778fd8d004cb50`.

These match the existing donor evidence. v291 ENC was not overwritten or
claimed compatible with that EP45 decode route. Private XMLs and generated
SCP remain outside the Git repository.

The recovery builds the 2,442 added rows needed by the existing readers,
retaining all 19 original sections, headings and Gold/Platinum rows. Its
staged SCP SHA is `b8dda5e7bfc366ea9d0b3b6936b48fe76cb7c98d9771acfa521fa65310b81909`.
It has **not** reproduced the old stage file's byte hash `26c9c4...`;
semantic row preservation was checked separately. Do not replace the old
deployment hash or install this file as native `MeritSystem.scp`.

The C++ `NativeCatalog` reader now retains all mastery types and 1,096 full
level definitions, including force IDs, values and value types, rather than
discarding them while reading costs. It additionally reads 308 slot opening
definitions with 616 materials and timers, 100 Special Mastery effects and
the separate Special Mastery cost (1,500 WExp + three tickets). These data
structures expose definitions to a future native provider; no force effect
is automatically applied or guessed from an EP45 integer.

The compiled reader's **all 1,096 level records** were independently compared
with the original XML, including every cost/type/base/bonus field. They match.
Its complete-slot catalog check passed on the actual recovered input. New
tests reject malformed forces and incomplete slot/special catalogs. Existing
V35 and slot input readers accept the recovered bundle. Native/catalog and
recovery tests pass locally; no online gameplay test is implied.

### Exact next integration boundary

The known v14 tree and cached legacy SDK do not supply a verified exclusive
owner/save API. The cached SDK declares a 266-slot inventory and mostly
padding fields; its wrappers even assign two different pointer return types
to the same address `0xADD2C0`. It is not evidence permitting a live native
mutation or publishing a map while dispatch is running.

The operator has now run `Collect-Diamond-NativeSources.ps1` and supplied the
95-file export from both named source roots. Do not request it again. The
upload SHA-256 is
`c6267d6f41f01fec5c71ca20d297d5ccb58328ce914d49ece2c07f3c4d9dbf49`.
All 95 source members passed manifest length/hash checks. There are 33 unique
file contents, including repeated copies of the same old SDK. The primary
GameStructs.h/.cpp and Proc.h/.cpp exactly match the cached legacy copies.
The additional Costume refresh sources do not implement a native owner/save
lease and are not substitutes for one. Source files stay private.

## Native host investigation and WExp correction

`worldsvr-ingress/verify_native_host_contract.py` executes pinned original
instruction blocks from the exact WorldSvr and DBAgent. It verifies:

- native spending decreases userdata `+0x16E0` and increases `+0x16F0`;
- native save packing copies those fields and `+0x16E8` to body offsets
  `0x99`, `0xA1`, `0xA9`;
- DBAgent binds these values to named parameters 64–66, `WarExpStatus`,
  `warExpEarn`, `warExpUsed`, in its `set_cabal_character` call;
- the original dispatcher takes mutex `0x23685E0` around CallProc only when
  its layer `+0x38` is greater than 1 AND the map locking byte is nonzero.

Three original-code accounting/packing/binding cases and 16 dispatch branch
cases pass. Clock, SQL/network functions and mutex operations in this
harness are substituted; there is no live server test. This global,
conditional dispatch mutex **does not prove a per-character lifetime and
asynchronous-save fence**. Do not enable host readiness flags from this alone.

The atomic SQL draft previously left WarExpUsed unchanged. It now adds
30,000 to used while subtracting 30,000 from current, preserves earned,
rejects bigint overflow before mutation and keeps replay above the update.
`DiamondWarExpAccounting.h` supplies the checked ledger transition to the
ODBC bridge. Its committed-receipt query now also requires the actual saved
inventory and all three WExp counters to match. An old receipt by itself is
insufficient when ordinary saves could have overwritten game rows.

The C++ ledger/bounds checks, SQL static checks, original-code fixtures,
ODBC preflight and complete dispatch-to-ODBC link tests pass locally.
unixODBC development headers were extracted under the Cloud workspace; the
VM and its packages were not changed. No connection to the real SQL Server
was made by these local tests, and all online write/response gates remain off.

### Next real SQL engine check, without game rows or persistent installation

`native/real-gamedata-transaction/test_rankup_in_temp_tables.py` builds a test
from the **actual procedure body**, replacing its targets with connection-local
`#` tables and a `#` procedure. The application-lock namespace is also unique
to the test. It checks commit, replay without a second debit, rollback after
a deliberately failed final receipt, used-counter overflow and stale-counter
rejection. It refuses non-temporary schema/table references.

The operator wrapper `Test-Diamond-TemporarySql.ps1` transfers the pinned
runner and SQL source over SSH. The SQL password remains inside sql_main's
existing environment. No game rows, persistent tables/procedures, services or
network settings are changed. Temporary objects disappear with the test
connection. The real SQL engine execution is pending operator relay; this
test still cannot prove online WorldSvr locking, Mastery stat application,
relogin initialization or working Diamond gameplay.
