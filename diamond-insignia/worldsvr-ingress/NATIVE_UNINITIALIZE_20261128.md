# Diamond character uninitialization boundary

## Received target trace

The operator report `Diamond-NativeLifecycle-20261128-200552-d2f93f.txt`
recorded two calls to native world transition B0ACD0 and successful debugger
detachment. The first stack includes 7DF83C, A49A72 and A4A20A. The second
includes 8327EA. Neither the B0AFD0 nor B0B260 breakpoint fired during this
capture. The capture does not establish their role in other exit paths.

Disassembly of the pinned WorldSvr shows the first chain reaches character
uninitialization. At 7DF69E it calls AD6060 with USERDATACONTEXT. The reset
prefix clears the character identity at data+A24. Keeping the account registry
entry or a raw address alone cannot preserve the previous character state.

## Implemented source connection

`DiamondNativeUninitializeIngress.h` binds the original user procedure 143.
Original executable instructions at 8EF259..8EF285 register A4A130 at table
slot 235FD38, which equals 235F8C0 + 143*8. The wrapper informs the adapter
before forwarding to that original handler. It preserves the procedure object,
locking byte, arguments and native return value. Installation requires an
exclusive startup boundary, the expected original handler and a single handler
vector. An unexpected existing route is rejected before any publication.

The adapter records the native USERCONTEXT address and authenticated identity
when a pending operation is created. Uninitialization compares the recorded
address without dereferencing the native character data. It interrupts the
active completion even while the request still owns that completion during SQL.
After Finish moves ownership into pending storage, the same completion remains
reachable by lifecycle events. Events must use the account executor required by
the existing adapter contract.

## Regression corrected

Previously an interruption during SQL only set Pending.interrupted. The request
then called AcceptCommitted and mutated native character data before Finish
noticed the interruption. The added regression reproduced that mutation before
the fix. It now returns the SQL commit image into recovery storage and performs
zero native mutations, saves or success replies after interruption. Retained
recovery evidence cannot be replaced by a subsequent result.

## Verification

- Registered-handler regression passes with character uninitialization invoked
  during the substituted SQL call. The original handler runs after invalidation
  and its return value is preserved.
- Completion regression retains a returned commit record after interruption,
  performs zero native actions and rejects duplicate completion.
- Clone tests pass with AddressSanitizer and UndefinedBehaviorSanitizer.
- The default build still rejects activation.
- The original registration slice and reset prefix execute in Unicorn against
  the pinned WorldSvr. The handler address and identity clearing are verified.
  The complete native reset routine is not executed by this check.

## Deployment boundary

This source connection is not installed on the test VM. AcquireSession still
requires a verified native lifetime/save provider. The opcode 143 route covers
return to character selection. Socket close, forced removal, other AD6060
callers and native save publication/ACK interception require their own verified
routes before the production binding can claim complete lifecycle coverage.
The new callback does not establish a native memory lease or save exclusion.
