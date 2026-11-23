# CABAL v291 — 0BDA WorldSvr process-context ingress and durable S2C gate

**2026-11-23. Tested native integration boundary; NOT a deployable game handler.**

## What was implemented

New source files:

- `Diamond0BDAWorldContext.h/.cpp` — source-compatible x64
  `PROCESSDATACONTEXT` field layout, type/offset/size assertions,
  verified transport-frame length, exact opcode parsing, and
  WorldSvr-session-bound host proof callback. Non-0BDA traffic,
  including Platinum 0B10/0B13 and the 0BDD cancel candidate,
  passes to the original handler. All unknown, malformed,
  mismatched-size or unauthenticated traffic is rejected without
  resource mutation.
- `test_0bda_world_context.cpp` — two C++17 test modes:
  default-fail-closed and explicit in-memory clone macro. Tests
  transport integrity, callback availability, foreign session,
  client-list mismatch, incorrect length, original command
  pass-through (including **350-byte original frames**), synthetic
  100-ticket/30,000-WExp debit, injected storage failure and
  revision replay.
- `Diamond0BDASaveReplyGate.h/.cpp` — physically separate
  **candidate S2C encoder** that cannot stage success before a
  reconciled `DiamondWorldSaveBarrier` and independent flags
  for exact runtime client response ABI.
  Even in isolated clone tests it sets `canSendToClient=false`.
  Normal builds never serialize success.
- `test_0bda_save_reply_gate.cpp` — verifies cmd47 foreign-ack
  rejection, that cmd47 by itself is **not sufficient**, exact
  persisted GameData inventory/WExp/receipt snapshot reconciliation,
  mismatched inventory as recovery and success never being sent.
- `DiamondWorldProcRegistryPreflight.h` and
  `test_world_registry_preflight.cpp` — **read-only**
  collision/precondition checks for original `g_sUsrProcedureMap`
  at exact-ELF address `0x0235F8C0`. The owner archive confirms
  source registry capacity `MAX_MAINCMDNUMBER=3999` and
  `PROCEDUREMAP**` slot table. Tests require original Platinum
  `0x0B10` and `0x0B13` entries, an empty 0BDA slot,
  attested exact WorldSvr and exclusive registration lock.
  **Even an apparently empty slot does not permit installation**;
  host C++ `PROCEDUREMAP` allocation and ABI are unverified.
  The code never reads the guest's absolute memory address.

## Owner-binary and source evidence

Original WorldSvr ELF, 10,596,184 B, SHA256
`caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3`.
In its Platinum handler `0xA40F00`, instruction
`0xA40F14: mov r12,[rsi]` uses the user-context pointer and
`0xA40F31: mov r14,[rsi+8]` uses its request-buffer pointer.
The owner's archived WorldSvrRealm source
`PacketManager/PacketManager.h` defines
`PROCESSDATACONTEXT` with first three fields
`pUserCtx, cpPacket, WORD iLen`, matching those disassembly offsets.
That archived source was **not** copied into the public repo.

The S2C `0x0BDA` real v291 client handler `0x6DA920`
checks its `BYTE [packet+6]` status. A *candidate* synthetic
7-byte ACK is therefore staged with `E2 B7 07 00 DA 0B 01`.
**The exact server-emitted 0BDA wire ABI is not observed.**
The module must not be used to transmit this unverified ACK.

## Test safety boundary

GitHub CI compiles and tests the passive/default C++17 path as well
as synthetic clone trial builds. The host-provided runtime attestation
callback is deliberately not implemented because real
WorldSvr session, live inventory slot-quantity and crash-safe
MSSQL/GameData integration are not proven. Mocked callbacks and
in-memory balances are **not** real character data.

- No `LD_PRELOAD`, live `lib.so` patch, or direct procedure-map write
- No SQL writes or game launches
- No client file changes
- No actual S2C packets sent

## Exact next tasks to achieve first playable rank-up

1. Verify the 0BDA UI selection and S2C reply length on an **isolated
   VM clone** with rollback before actual handler activation.
2. Verify the **actual 48-byte WorldSvr slot record inventory ABI** for
   0BDA, especially item `33554961` stack quantities, duplicate
   selected slots and real Resource/WExp ownership. Do not assume
   0B10 item's option encoding is suitable for grade 2.
3. Provide exact host-owned `PROCEDUREMAP` initialization and ABI
   registration with a protected empty 0BDA slot without disturbing
   0B10/0B13, reproducing the known-good server startup.
4. Bind authenticated WorldSvr user/character locks, durable
   receipt and cmd46/47 GameData saves to existing
   `DiamondWorldSaveBarrier`; demonstrate relogin/rollback/replay.
5. Only after clone proof, enable the actual response and install.
   Existing `exit 78` failure from old sidecar is a strict stop gate.

**Current status: native ingress + persistence-check contracts tested
offline; real WorldSvr registration, resource debit and gameplay
remain incomplete.**
