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

## Require a native inventory save for ticket-funded rank-up

The pinned DBAgent calls `dbo.set_cabal_character` with inventory at
parameter 31 and the three WExp counters at 64–66. Its success ACK echoes
the requested flags. The archived SQL contract for the 242-parameter
procedure (UTF-16LE SHA-256
`e802d1f4054b978c636203b237ad61a423302844a010353bae4721fe8550fab1`)
uses mask 2 for inventory. The saved Pet implementation independently uses
the same mask. The subsequent active export confirms the SQL behavior below.

A ticket-funded rank-up now checks for the inventory bit before publishing
the reserved save. A later SQL readback alone could see the debit from the
earlier Diamond transaction even if ordinary inventory saving was skipped.
Other flag bits are preserved and the ACK must still echo the exact mask.
The constraint applies to rank-up; a point-funded mastery has no ticket debit.

Local regressions cover a save omitting inventory, an extra flag with
inventory present, and loss of the session before a delayed ACK. Losing the
session retains the transaction record for recovery and sends no success.
The barrier suite also passed ASan/UBSan. Actual reconnect, reconciliation
of pending work, and gameplay remain unverified.

`Read-Diamond-CharacterSave.ps1` exports only the active SQL procedure
definition through system metadata. The file in Downloads uses UTF-8; the
reported digest covers the original SQL UTF-16LE bytes. The reader was
tested locally with Unicode, multiple chunks and a missing chunk using a
substituted transport. The metadata query passed SQL Server ScriptDom parsing.

## Active character save on the v291 test VM

The uploaded procedure matches the historical UTF-16LE digest above.
ScriptDom parsed 242 parameters. A zero save mask returns before the
transaction. For a nonzero mask, the following statements run within the
same transaction, subject to successful execution and commit.

| Data | Condition | Operation |
| --- | --- | --- |
| Inventory | Mask includes 2, line 335 | Update the existing character's inventory from the supplied blob |
| Bike inventory and sold items | Same bit, lines 342 and 348 | Update their respective blobs |
| Current, earned and used WExp | Unconditional update, line 446 | Assign all three supplied counters by character ID |
| Missing WExp row | Previous update affected zero rows, line 449 | Insert all three supplied counters |

An inventory-free save can therefore replace the Diamond WExp values.
The WExp update has no revision or session comparison. An ACK for another
save within the same character's exclusive window contradicts the assumed
save ordering, even if the caller reports one outstanding save.

The completion now retains the record for recovery when a fresh ACK for the
same session and character has different flags, or the host associates it
with a different intent. Stale ACKs and ACKs for unrelated sessions are
ignored. A subsequent matching ACK cannot send success for the conflicted
operation. A clone regression reproduced the old behavior, then passed
with both kinds of conflicting ACK and the expected late ACK. The completion
and barrier tests also passed ASan/UBSan. The host still needs to supply
an exclusive save window and deliver overlapping native saves to the
coordinator. Two ACKs with identical fields cannot be distinguished from
the wire alone. The active SQL procedure was inspected without executing it.

## Owner-thread save result entry

The original IPC handler copies an 18-byte result and changes opcode 47
to internal command 2032 before enqueueing it on the character's owner
layer. It also copies the current USERCONTEXT generation DWORD into the
queued process context. The generation copy occurs when the ACK is
received, rather than when its corresponding save was sent.

The new `OnItcSaveAck` entry accepts internal command 2032 and forwards an
owned, normalized 18-byte copy to the existing completion checks. The
original queued frame is preserved for the original handler. Internal and
IPC entries reject the other stage's command. Both require the trusted
host to resolve the queued generation under the held session lease.

The native instruction verifier now executes this conversion for three
generation values, with successful and failed allocation. The allocator,
copy service and queue service are substituted. All six cases passed and
the original source packet remained unchanged. The completion test checks
a valid internal response, wrong-stage/truncated responses, another
generation and duplicate completion. Normal and ASan/UBSan tests passed.
The default build still refuses rank-up completion.

This supplies the correct completion entry for the owner-thread callback.
The callback is not installed in the active WorldSvr. The exact native
session lifetime/save exclusion provider, event ownership and recovery
still need implementation before this entry can be used in gameplay.
A queued generation by itself cannot distinguish a delayed old ACK from a
new session that currently owns the same character.
