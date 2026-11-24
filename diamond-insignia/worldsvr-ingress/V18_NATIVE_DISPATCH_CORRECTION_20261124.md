# V18 native dispatch correction, 2026-11-24

Owner's active WorldSvr /proc/1455/exe SHA256:
caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3.

V17/V18 and CallProc owner outputs establish:
- Context user pointer +0, packet pointer +8, length +0x10 (64-bit).
- At b2e808, mov r14,QWORD PTR [r12+0x10]; b2e81a passes
  that value as the memcpy length. At b2e87b the same qword is copied
  to the next process context. At b497fe, CallProc reads the same qword
  and adds it to its byte counter at map+0x28.
- Supersede V16's WORD-width change; the V14 GCC14 build remains the
  correct-width offline candidate. Archived source and active binary differ.
- b2e440 loads original user map 0x235f8c0; b2ea10 tries a second map
  0x2357bc0 when user slot is null. Collision check must consider both.
- b2e494 checks map+0x20; the mutex 0x23685e0 is acquired conditionally
  at b2e930 and released at b2e918. This is not proof of a per-character
  save/disconnect lease. Do not use as substitute.
- b49750 CallProc(map, layer, context): vector start/end at +0/+8,
  invokes each function with layer/context at b497c6, stops on nonzero,
  default result -1. Map accesses also +0x24 count, +0x28 bytes,
  +0x30 ACE timer, +0x40 elapsed, +0x48 start timestamp.
  An opaque tail is not necessarily safely zero-initialized.
- The existing V14 compatibility registrations use calloc and custom
  AddProc; do not assume this is native constructor/destructor proof.

Next: inspect native AddProc 0x8ed930 and actual 0B10 registration
cross-reference to identify original map initialization. Keep Platinum
unchanged. No active module, SQL, client, or network changes. Rank-up
remains unverified. Source and compiler availability are no longer blockers.
