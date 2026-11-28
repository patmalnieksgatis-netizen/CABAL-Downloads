# Original B0 quantity and debit correction

The earlier conclusion that AE0E90 returns one for B0 metadata was incorrect.
AE0ECE loads the QWORD option into RAX before the type switch. The B0 path
returns that value at AE0F0D. Only stackField3C <= 1 returns the constant one
loaded at AE0EC0. The metadata-specific masked branches retain their existing
behavior.

The pinned original instructions were executed in Unicorn for every plain
quantity from 1 through 999 with B0 metadata and maximum stack 999 supplied
from the operator's recorded catalog observation. AE0E90 returned the quantity
in every case. AE0FD0 consumed min(quantity,100), wrote the remaining option,
and returned whether that stack was exhausted. This does not execute slot
removal, which the caller performs separately for exhausted stacks.

The native serializer instructions at 8BDE3B..8BDE74 copied kind, serial, option,
physical slot and duration into a 30-byte saved row. Tested slot indices
47, 50, 511 and 521 were preserved without an index adjustment. This proves
that serializer slice. Authentication of a client's selected slots and
concurrent native memory ownership still belong to the runtime host.

## Source change

DiamondWorld48TicketUnits now accepts a plain B0/999 numeric option in 1..999
using trusted native catalog metadata. It rejects high option bits, zero,
values above 999 and unsupported B0 stack limits. The ticket planner uses this
same branch. The redundant UI-observation requirement was removed from that
native path. Existing persisted-record decoding continues to require its own
layout and owner evidence.

The native count, ticket planner, action and authenticated ingress tests pass
with AddressSanitizer and UndefinedBehaviorSanitizer. Original binary checks
also pass for 999 native count/debit cases and four saved slot values. SQL and
native lease services remain substituted in the C++ action tests.

## Remaining runtime boundary

AcquireSession has no native implementation in the available project source.
The account lookup returns after unlocking, and character uninitialization
resets native state. The current callback covers opcode 143. Transport close,
forced removal and save publication must participate in a complete lifetime
and save fence before a native provider may be enabled.

The server's 18-byte save ACK carries character and flags without a transaction
identity. Its native pending fields are reset by exchange with zero. Existing
binary tests demonstrate that a repeated ACK can clear newly pending state.
A real provider therefore needs verified routing/exclusion of native saves
and owner queue events. The opcode-143 wrapper alone cannot establish this.

Direct SSH from this environment to 192.168.56.101:22 returned Connection refused
on 2026-11-28. The supplied trace exercises character-selection transitions,
with no unlink/removal breakpoint hits. It provides no target evidence for
transport close or forced removal. No complete game transaction can be tested
from this environment with the currently available connection.

The source candidate and its compiled modules are for review and offline
verification. No complete native provider is present in them. They cannot be
advertised as an operational Diamond server installation.
