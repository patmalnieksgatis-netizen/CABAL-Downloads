# CABAL v291 Diamond 0x0BDA — exact v14 WorldSvr source hook integration

## What the user asked

Connect the existing Diamond grade-up to their actual
\`EP36_291_TEST\` WorldSvr and make it work in game.

**Actual server deployment: NOT DONE. In-game Diamond rank-up: NOT WORKING.**
The GitHub connector can edit the source repository but cannot access the
user's Windows host-only VirtualBox SSH network \`192.168.56.101\`.

## Source work now completed

- Added \`DiamondReal0BDAIngressPort.h\`, a safe exact C2S recognition
  gate for candidate opcode \`0x0BDA\` with a strict packet length/count.
  No C2S fields are treated as account identity, ticket counts or proof.
- Added \`Apply-DiamondV14Real0BDAClone.py\` to inject a \`0x0BDA\`
  branch into real v14 \`ProcSystem::DoProcessDataCtx\` **on a source
  copy**. It reuses the previously validated 64-file v14 hash manifest
  and exact \`ProcSystem.cpp\` / \`Types.h\` SHA256 pins.
- The hook invokes \`DiamondReal0BDAIngressPort::Process\`, then
  passes the packet unchanged to the original WorldSvr dispatcher.
  No original \`0x0B10\` Platinum or \`0x09F3\` Merit behavior is changed.
- Until the complete original WorldSvr GameData memory-save barrier,
  rank-grade client data and v291 S2C reply are verified, \`Process\`
  is deliberately **non-installable as a writing handler**; default
  returns \`false\`. This prevents a real inventory/WarExp debit
  followed by original dispatcher double debit or missing UI response.
- Test \`tests/test_real0bda_v14_port.cpp\` and GitHub Actions workflow
  \`diamond-worldsvr-ingress.yml\` compile the source port and assert
  the candidate detection, disabled binding, Platinum/Merit original
  pass-through and source-hash mismatch rejection.
- CI \`Diamond v291 passive WorldSvr ingress safety\` run
  \`45250437281\` passed the new hook port and source-check tests.
  This is not a live WorldSvr compile against private v14 sources.

## One-command source staging (NOT installation)

On a machine with the owner's exact archived v14 source extracted,
run the new patcher from the repo:

\`\`\`sh
python3 diamond-insignia/worldsvr-ingress/Apply-DiamondV14Real0BDAClone.py \
  --source /root/CABAL_V282_LIVE_MERGE_CANDIDATE_v14/source_tree/src \
  --output /tmp/cabal_v291_diamond0bda_v14_source_clone
\`\`\`

This only produces a *separate source tree*. It does not compile
a replacement \`lib.so\`, install it, restart WorldSvr or make Diamond
playable. The source path is from the owner's last v14 archive.
The patcher refuses any source not matching the pinned manifest.

## Critical blockers that make live installation unsafe right now

1. Prior source-matched \`lib.so\` probe replacement caused
   \`WorldSvr_01_01\` to exit with status **78**, then rollback succeeded.
   Root cause remains **unproven**. Repeating the same or another
   \`lib.so\` replacement before resolving the startup difference risks
   breaking Costume, EventPass, dungeons and other working features.
2. The \`0x0BDA\` client C2S packet is an offline candidate. Server
   selection-slot meaning must be independently matched to real
   WorldSvr 48B inventory and 30B GameData row identity.
3. Owner's observed real ticket \`33554961\` has WorldSvr
   \`kind=0xB0\` and max stack \`999\`; two anonymous saved
   \`ItemOption\` entries each equal 999. They do not prove
   the client's displayed count for the SAME selected stack.
4. The real SQL transaction prototype is source-integrated and
   offline-compiled, but it has NOT been deployed, tested for native
   \`WarExpEarn/WarExpUsed\` semantics, or reconciled with
   live WorldSvr / DBAgent \`cmd46/47\` saves. A later online
   save could overwrite an out-of-band SQL debit.
5. New Grade2 SQL receipt/ledger has not been identified as
   native v291 client-visible Diamond rank state.
6. S2C success shape and status consequences for \`0x0BDA\`
   remain unproven; an invented seven-byte success reply is unsafe.
   Client \`0x09F3\` S2C path can read additional DWORD at +7.

**Do not instruct the user to overwrite active lib.so or
enable the real ODBC callback until these are resolved.**

## Next exact engineering task

Capture and verify an actual \`0x0BDA\` rank-up request and corresponding
response while preserving the original game's dispatcher, or reconstruct
the exact S2C and the original in-memory commit+save ABI from the pinned
WorldSvr/client binaries. Resolve previous \`exit 78\` by examining the
failed new process and extension integrity checks before attempting a
staged WorldSvr replacement.

All changes in this checkpoint are GitHub source-only.
