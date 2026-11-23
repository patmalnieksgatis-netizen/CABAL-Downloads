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


## Additional exact client S2C registration proof

The same SHA-pinned client binary separately registers **incoming**
server-to-client opcodes via `0x16BB3C` and callback binder `0x2879E4`:

| Incoming S2C | Client handler RVA | Matching UI C2S |
| --- | --- | --- |
| `0x0BDA` | `0x6DA920` | `0x21C / 0x0BDA` |
| `0x0BDB` | `0x6DAED8` | `0x21D / 0x0BDB` |
| `0x0BDC` | `0x6DB154` | **no outgoing UI counterpart in this five-command neighborhood** |
| `0x0BDD` | `0x6DB0FC` | `0x21E / 0x0BDD` |
| `0x0BDF` | `0x6DAD14` | `0x21F / 0x0BDF` |
| `0x0BE0` | `0x6DB3B4` | `0x220 / 0x0BE0` |

Each mapping is checked using the actual `mov [rbp+0x10],opcode`
instruction, callback `lea rdx,[rip+disp32]` and the exact
callback-registration target `0x2879E4`. This proves the client contains
a receiving dispatch table for the same new Merit-adjacent family and one
additional `0x0BDC` S2C handler. It **does not** prove actual packet
payload layout, that the handler is exercised at runtime, or its
Diamond meaning. In particular, do not manufacture responses of guessed
length or fill missing DWORDs with zero.

## Critical next engineering task — towards actually playable Diamond

1. Analyze exact callback flows of `0x0BDA/0x0BDB/0x0BDD/0x0BDF/0x0BE0`: field offsets, conditional send paths, relevant Merit UI state and matching S2C handlers. Prove which, if any, is the actual Diamond rank-up.
2. Reconstruct the corresponding server command ABI from the exact client or a compatible newer **reference** WorldSvr; compare owner-provided EP45 sources if compatible, and do not confuse opcode with local UI ID.
3. Only after ABI proof, bind handlers **in a disposable VM clone** to verified session identity, real GameData item `33554961` quantities, WExp deduction, atomic MSSQL progression/receipt and `cmd46/47` reconciliation.
4. Regression-test original Merit/Platinum, Costume, EventPass, dungeons, re-login and request retries. Never re-run previous live `lib.so`/sidecar deployer, which produced `exit 78`.

No active WorldSvr, SQL, Supervisor, game account, client installation or VM was modified.

## EP45 server-file candidate was checked (negative finding)

The owner's archived `EP45_WorldSvr` (10,596,184 bytes) was
independently hashed and compared byte-for-byte with
`WorldSvr_FULLCHAIN_20261108`. Both are **identical**, SHA256
`caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3`.
Consequently this specific EP45-labeled server ELF is **not** a source of
new `0x0BDA..0x0BE0` implementations beyond the running candidate.
Do not infer that every other EP45 artifact or actual newer EP45 source is
identical; this result applies only to this exact file pair.

## Verified client S2C response read paths (no invented wire schema)

Byte-level verification against the SHA-pinned owner's real v291 client,
including concrete RIP/client-reader instruction anchors, now separates
these command handlers:

| S2C | Branch-sensitive client reads | Consequence |
| --- | --- | --- |
| `0x0BDB` | `[packet+6]` status `==1`, and `DWORD [packet+7]` checked against `0xFFFFFFFF` | A successful route accesses a 4-byte field beyond the 7-byte header |
| `0x0BDC` | first `DWORD [packet+6]` checked against `0xFFFFFFFF`; a three-iteration loop consumes DWORDs at `+6,+10,+14` | This route accesses at least 18 bytes, not a generic 7-byte status ACK |
| `0x0BDD` | `BYTE [packet+6]` compared with `1` in its short verified handler | Only status-byte use proved in this handler |
| `0x0BDF` | `BYTE [packet+6]` compared with `1`; successful branch reads `DWORD [packet+7]` | Success uses a field beyond the 7-byte header |

These are **conditional native reads**. They do not prove that the
transport buffer is exactly this length, how the server populates fields,
whether other handlers validate lengths elsewhere, or that the user has
invoked a Diamond action. Do **not** fabricate a response by padding it
with zeros. Verified anchors and C++-free Python test fixtures are kept
in `verify_merit_client_server_gap.py` and GitHub CI.

## Additional read-only proof: two S2C handlers update Merit state slot 2

The client's `0x0BDD` success response at `0x6DB102`
(`[packet+6]==1`) loads index `2` into `EDX` at `0x6DB10D`
and calls `0x242888` at `0x6DB115`. The wrapper
`0x242888` calls the common state writer `0x249730`.

Separately, the `0x0BDB` successful response uses `EBX=2`
at `0x6DB019`, moves it into `EDX` at `0x6DB01E`
and calls **the same** `0x249730` at `0x6DB023`.
The state writer stores index-selective values in several arrays
in the Merit singleton (at `+0x158`, `+0x164`, `+0x170`,
`+0x180`, `+0x198`).

All 12 sites are SHA-anchored in `verify_merit_client_server_gap.py`
and covered by CI fixtures. The index `2` may represent a newer
Merit state group, but **neither callback is established as a Diamond
rank-up purchase**. The state writer is not a trustworthy server
resource-debit primitive.

The owner's `server/active-v291/MeritSystem.scp` separately contains
no `Badge_Grade=2` rows; this is an independent real-config blocker,
documented in `../catalog-audit/README_LATVIAN.md`.
