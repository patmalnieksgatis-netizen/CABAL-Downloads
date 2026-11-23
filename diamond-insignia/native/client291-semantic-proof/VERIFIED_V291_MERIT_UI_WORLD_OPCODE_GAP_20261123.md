# CABAL v291 — verified Merit-adjacent client C2S vs actual WorldSvr registry gap

**Date:** 2026-11-23. **Status: offline exact-binary proof; NOT a Diamond deployment and NOT proof that these are all Diamond commands.**

## Exact input provenance

- Owner's original client `CabalMain.exe`, SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`, 15,089,000 B.
- Owner's exact server `WorldSvr_FULLCHAIN_20261108`, SHA256 `caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3`, 10,596,184 B, ELF64 ET_EXEC.
- Local UI events are **NOT** network opcodes. The callback registration has been checked in the original client's code; separately, each callback contains the listed C2S opcode instruction.
- WorldSvr user procedure registry base is independently anchored at `0x235F8C0`, with stride 8. The verifier checks known code patterns that reference each computed slot through RIP-relative disp32. The existing registered Platinum `0x0B10` is a **positive control**.

## Cross-binary result

| Local UI event | Client callback RVA | Outgoing C2S | WorldSvr registry slot | Direct static RIP references |
| --- | --- | --- | --- | --- |
| `0x216` | `0x6E06F8` | `0x0B10` | `0x2365140` | **3** — existing Platinum grade-up |
| `0x21C` | `0x6DFD08` | `0x0BDA` | `0x2365790` | **0** |
| `0x21D` | `0x6DFFE8` | `0x0BDB` | `0x2365798` | **0** |
| `0x21E` | `0x6E03EC` | `0x0BDD` | `0x23657A8` | **0** |
| `0x21F` | `0x6DFF60` | `0x0BDF` | `0x23657B8` | **0** |
| `0x220` | `0x6E0464` | `0x0BE0` | `0x23657C0` | **0** |

Source of the above result: `verify_merit_client_server_gap.py`, run with the two original binaries, SHA-checked. It validates each client event registration and C2S opcode anchor, ELF section bounds and exact registry slots. Positive-control matching includes known WorldSvr instruction RVAs `0x8FBFC0`, `0x8FBFCE`, `0x9A48C5` for `0x0B10`.

**Important limitations:** no direct matching **static** RIP-relative references is strong evidence of a compatibility gap in this particular server build, **not** mathematical proof that a handler could not be dynamically or indirectly registered elsewhere. The semantic meaning of new Merit-adjacent codes and their exact packet fields/response formats have not yet been proven to represent Diamond Insignia, so do not reassign these opcodes speculatively. Existing `0x0B10` must retain its working Platinum functionality.

## Reproduce with owner-supplied private binaries

```sh
python3 diamond-insignia/native/client291-semantic-proof/verify_merit_client_server_gap.py \
  --client-zip /private/CABAL_v291_Diamond_Client_exact.zip \
  --world /private/WorldSvr_FULLCHAIN_20261108
```

The exact source binaries are **not** committed to this public GitHub repository. GitHub CI runs synthetic fixed-length/RIP-displacement tests and hash rejection; local SHA-pinned execution separately verified the real binary pair.

## Critical next engineering task — towards actually playable Diamond

1. Analyze exact callback flows of `0x0BDA/0x0BDB/0x0BDD/0x0BDF/0x0BE0`: field offsets, conditional send paths, relevant Merit UI state and matching S2C handlers. Prove which, if any, is the actual Diamond rank-up.
2. Reconstruct the corresponding server command ABI from the exact client or a compatible newer **reference** WorldSvr; compare owner-provided EP45 sources if compatible, and do not confuse opcode with local UI ID.
3. Only after ABI proof, bind handlers **in a disposable VM clone** to verified session identity, real GameData item `33554961` quantities, WExp deduction, atomic MSSQL progression/receipt and `cmd46/47` reconciliation.
4. Regression-test original Merit/Platinum, Costume, EventPass, dungeons, re-login and request retries. Never re-run previous live `lib.so`/sidecar deployer, which produced `exit 78`.

No active WorldSvr, SQL, Supervisor, game account, client installation or VM was modified.
