# Rank-up completion connection — 28 November 2026

Status: source connected and linked; no active WorldSvr installation.
The exact-native lease/mutation/save provider is still missing. This is not
a usable game update and must not be installed by enabling readiness flags.

## Connected code path

`DiamondNativeRankUpV20::Handle` now requires a prepared
`RankUpCompletion` before attempting the actual Server01 bridge. Production
builds refuse registration. A verified clone build additionally needs the
existing session authority, exact owner loader and a real `NativePort`.

The actual ODBC transaction constructs owned completion storage **before**
attempting SQL. After commit and receipt/game-row readback it returns that
record in its request-local context. The record contains stable account,
character, intent and session generation, complete before/after inventory
images, the selected debit/mapping and all three WExp counters. It retains
no raw native user/data pointer. Before SQLExecute it is placed in recovery
storage; an uncertain execute result or failed readback retains those images
without claiming a commit. Only verified success moves it into commit storage.
The native handler transfers either kind into retained completion ownership.

The native handler moves this result into `RankUpCompletion` before its
ephemeral request is destroyed. Completion performs this sequence:

1. Match the exact leased account, character, session generation and intent.
2. Ask the native provider to compare/apply the committed change under its
   real fence. An unknown/partial result requires recovery.
3. Reserve an exclusive native save, establish cmd46 flags/event epoch and
   zero competing outstanding saves, then publish it.
4. Return to the dispatcher. Do not wait synchronously for its ACK. The host
   retains the completion and queues later native hook events on the owner
   executor using stable identity, not a retained unleased user pointer.
5. Validate cmd47, the session generation and save ordering.
6. Open a fresh ODBC connection and check the actual full saved inventory,
   every WExp counter, rank/revision and receipt together. Each table uses
   HOLDLOCK in the single SELECT to retain serializable read protection
   through that autocommit statement. Statements have a 30-second timeout.
7. Reconcile the save barrier; attempt the seven-byte success reply at most
   once; release the native fence only after successful reconciliation/send.

Lost/foreign/stale ACKs do not establish success. Ambiguous save counts,
failed native apply/publish, changed session, unavailable or mismatching SQL
readback, and uncertain transport result retain the fence for recovery.
`Binding::finish` must move the completion into host-owned pending/recovery
storage. The class deliberately does not unlock that fence on destruction.

The registered callback does not forward a rejected Diamond operation to
Platinum and does not retry SQL or the client debit on uncertain outcomes.
Binding/Request layout changed: builders now advertise host ABI `0x20261128`.
Rebuild both sides; do not mix an older compiled begin/finish provider.

## Reply ABI decision

The exact v291 reader proof already establishes a seven-byte B7E2 response,
opcode 0BDA, status at +6. The native proof now executes the original
Platinum success send call at `0xA41788..0xA417A5`: it passes
`(USERCONTEXT*, packet*, 7)` to `0x75D4E0` with original packet
`e2 b7 07 00 10 0b 01`. The sender is substituted for argument capture; no
socket is exercised. These two independently pinned contracts define our
custom Diamond response. We do not assert that an EP45 WorldSvr emits it.

The reply encoder now permits that seven-byte custom response only in a
clone build after reconciliation and both ABI attestations. Default builds
still block it. Completion respects the encoder's `canSendToClient` result.
This is explicit source behavior, not evidence that the active runtime has
the necessary native authority/provider or that a packet was sent in game.

## Validation completed locally

- Registered-handler fixture now retains the real completion object after
  returning. Pending commit evidence reaches its save state machine; an
  uncertain SQL result is retained for recovery. The registry and SQL/native
  actions in this fixture are substituted.
- Completion fixture checks apply/reserve/publish/ACK/fresh-read/send/release
  ordering, stale/foreign session and packet rejection, ten failure paths,
  exactly one send attempt, and no fence release on uncertainty. Native
  actions and the SQL readback function are explicitly substituted.
- Completion fixture passes ASan/UBSan. Default and clone encoding and
  persistence-denial regressions pass.
- Actual ODBC adapter and every combined source unit link in both default
  and clone standalone shared modules with `--no-undefined`. They load in a
  separate local test process, report the new ABI and refuse null host
  registration. No native address, active registry or SQL connection is
  exercised by that load test. These modules are not deployment artifacts.
- Original instruction proof passes three WExp/packing/binding cases,
  16 dispatcher cases, eight ACK flag combinations, repeated-ACK clearing,
  and the original seven-byte send-call argument check.

The operator's previously received five-case real temporary SQL engine
test remains valid for its unchanged procedure source. It did **not** test
this new ODBC completion readback or active WorldSvr integration. Do not
label the fixtures/module link as an in-game test.

## Concrete remaining native boundary

`NativePort` intentionally has no pretend implementation. The supplied
legacy USERCONTEXT SDK contains padding, raw pointers and sender wrappers;
it supplies no exclusive lifetime/save lease. The native global dispatcher
mutex is conditional, and cmd47 clears native state without an intent ID.

The original network queue copies the connection's DWORD `USERCONTEXT+0xE4`
into its queued context (`0xB3DE06..0xB3DE19`, disassembly inspected). This
is useful generation evidence; copying it alone does not pin an object.
The original USERCONTEXT vtable also leads to the close path
`0xB3CD90 -> 0xB3F6A0`; its removal/reactor/transport callbacks cannot safely
be replaced by an addon-only mutex. These are static observations, not a
verified hook/lifetime contract. No hook or vtable was changed.

Still required: a proven native provider that holds session lifetime and
account-wide ownership across normal dispatch, disconnect/character reuse,
all native pack/save paths, selected item mutation, queued save publication,
and asynchronous ACK/recovery. It must load current owner/rank/Platinum data
and reconcile native RAM before an ordinary save can overwrite committed
rows. `begin`/`readLockedState`, the low-level NativePort methods and pending
event storage are not implemented for the active binary at this checkpoint.

Direct SSH was retried and returned `Connection refused`. Operator relay
is the only available route; that is also a separate barrier to deployment
and gameplay verification. No new collection command is requested merely
to recheck already known SQL results. No installer is provided while the
native provider is missing. Keep V29 forwarding-only and all current game
systems unchanged.

## Binding the debit to the reserved request

The registered handler passes the completion's reserved intent to the SQL
bridge. Under the session lease, the owner reader must return that same
intent before the commit callback can run. This closes a window in which
a second request for the same character and session could supply a different
intent and reach SQL before completion detected the mismatch. The ODBC call
binds the before/after inventory images already allocated for recovery.

The authenticated ingress regression uses the same account, character and
session generation for all three cases. A missing or different intent
produces zero commit calls and releases the inner lease. A matching intent
reaches the commit callback once. The authenticated ingress test passed with
ASan and UBSan. Default and clone shared modules linked with unixODBC and
loaded locally. These checks used no running game server.

The active Mileage and Guardian file hashes reported from the test VM match
the archived Pet/Costume package. Its native dispatch lock lasts for a
synchronous request. It does not supply session ownership across disconnect
and asynchronous saves. The native-source ZIP contains the WorldSvr extension
and copies of its sources. It does not contain the core session lifecycle
and ordinary character save implementations needed to bind that ownership.
A runtime test of rank-up, mastery, slot opening and relog remains pending.
