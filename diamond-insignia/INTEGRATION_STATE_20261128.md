# Diamond integration — 28 November 2026

Continues `INTEGRATION_STATE_20261127.md`. No game installation, persistent
SQL change, service restart, core replacement or VM network change was made.

## Actual SQL Server result received

The operator executed the helper at commit
`041f5009627f746168898d86dd9ebda554b5167e` over the existing SSH relay.
All five SQL Server engine cases passed: commit, replay without a second
debit, atomic rollback on the deliberately failed final receipt, bigint
overflow rejection, and stale WExp counter rejection.

The procedure source SHA-256 was
`1dc000673da9e5e53af7192061b8ba5d7adef8b4b7dc405758e5550f15e46d45`.
The test substitutes connection-local temporary targets in the actual
procedure body. This is a real SQL engine test, not the prior transport
fixture. No game rows were read or written, no persistent schema was
changed, and WorldSvr integration was not tested. The sanitized operator
result is recorded in
`native/real-gamedata-transaction/temp_sql_operator_receipt_20261128.json`.
Do not ask the operator to repeat it for the same source.

## Fixed post-save WExp reconciliation

The existing save barrier checked current WExp only. Thus an ordinary
native save could restore an old `WarExpUsed` value while leaving the
balance, inventory and receipt correct; reconciliation would incorrectly
permit the next success gate.

`Operation` now requires complete before/after ledgers: current, earned,
and used. Missing host reads default to -1 and fail validation. Rank-up
must follow the checked native transition (current -30,000, earned
unchanged, used +30,000), including bigint bounds. A point-funded mastery
level preserves all three counters; separate Special Mastery activation
is not implemented by that command.

After cmd47, all three independently read saved counters must match the
expected ledger. A correct balance plus stale earned/used values now
requires recovery and cannot permit success. This extends the earlier
ODBC immediate readback check to the later native-save reconciliation.

Verification passed locally:

- strict C++17 save-barrier tests and ASan/UBSan;
- stale used, changed earned and missing-counter post-ACK regressions;
- incomplete, incorrect, insufficient and overflowing debit rejection;
- point-funded mastery preservation;
- inventory reconciliation and default/clone 0BDA reply gates.

These use synthetic operation/snapshot inputs. No live owner provider was
created by passing them, and the actual reply emission remains disabled.

## Exact native ACK constraint

The original WorldSvr SHA-256
`caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3`
has three native pending QWORDs at userdata `+0x2B7B8`, `+0x2B7C0`,
`+0x2B7C8`, and corresponding status DWORDs at `+0x2B7E0`, `+0x2B7E4`,
`+0x2B7E8`. The original cmd47 handler `0x7DED30` selects them using
flags `0x2000`, `0x200`, and `0x2` respectively. It clears selected
QWORDs with `xchg` to zero and zeros their status; it does not decrement
an operation-specific outstanding counter.

`worldsvr-ingress/verify_native_host_contract.py` now executes all eight
flag combinations in the unmodified handler, followed by an identical
repeated ACK after newly setting pending state. The repeated ACK clears
the newer state too. The native session lookup is substituted; this
proves the exercised clear semantics, not native session lifetime or
network delivery. The result extends
`worldsvr-ingress/native_host_contract_20261127.json`.

Three original accounting/packing/binding cases, 16 conditional dispatcher
mutex cases, all eight native ACK flag combinations and the repeated-ACK
case passed. The native flags have not been assigned guessed subsystem
names. No machine code or private source is published.

## Concrete remaining integration blocker

Neither the global conditional dispatcher mutex nor these native pending
words establish the required per-character lifetime and save fence. The
WorldSvr provider still must connect native mutation, all competing save
paths, disconnect/relogin and asynchronous completion to one durable
operation before passing `Binding::independentOwnerFenceAndSaveCompletionVerified`
in `DiamondNativeRankUpV20.h`. Its `begin`/`finish` and `readLockedState`
providers remain unbound. Do not substitute a raw user pointer across an
asynchronous wait, hold the dispatch thread waiting for its own ACK, or
enable readiness flags merely because the SQL test passed.

There is no functional Diamond installer ready at this checkpoint. No
additional operator command is needed for the tests already received.
Next implementation is the native host provider and recovery path, then
actual rank-up/save/relogin checks. Full mastery effects/slot initialization
also remain unverified in gameplay. Preserve forwarding-only V29 and the
original working core until those dependencies are implemented.
