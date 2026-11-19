# Stage history — CABAL v291 EP39 Warp 485

| Stage | Purpose | Outcome |
|---|---|---|
| B/C | Initial server opcode/packet evidence, diagnostics and offline gates | Analysis only; no live fix |
| E | Reference-only mapinfo Warp675 candidate | Not authenticated v291; no actual ENC encoder |
| F | Reference world consistency | Static comparison only |
| G | Client reference / server registry triple-join | Registry mismatch identified; source reference-only |
| H | Read original decoded mapinfo from client's cache | Reader developed; no authenticated capture |
| I | Authentic capture audit and validation | No gameplay fix |
| J | Dual-mode cache capture (attach/start) | Attach returned `MAPINFO_NOT_CACHED`; index 28 pointer 0, size 49102 |
| ClientPatch | Offline XML candidate and validation tests | 16/16 offline PASS; no verified `.enc` |
| K | Independent offline reconciliation | 12/12 new static checks; original hashes matched |
| L | Cache lifecycle + codec collection | Confirms cache release mechanism; XOR guess failed |
| M | Full EXE static analysis / early capture attempt | Pinned EXE hash; direct loader did not decode authentic ENC |
| N | Attempt codec/capture + lab installer | 17/17 offline PASS, but no authentic ENC or gameplay test |
| O | Read runtime key and DLLs | 18/18 offline PASS; no verified Windows capture |
| P | Single callback binary guard on `qdIdx==4380` | 20/20 offline PASS, **real LAB startup failed** |
| Q | Full LAB clone and Stage P installation | 27/27 offline PASS; copied 57,764 files, 14.67 GB; **startup failed** |
| LAB recovery | Restore original LAB EXE, check startup | Original EXE survived 12-second check. No Windows Application Error events in report |
| R | Correct PE checksum + extend `.pdata` unwind range | 21/21 offline PASS; **real Windows quick exit again**; automatic rollback succeeded |

## Exact observed Windows outcomes — do not misreport

**Stage Q:** Original EXE SHA `52e7956d...79885d9`; patched LAB SHA `ef4fd980...7869d1`. User observed window appeared and vanished. Stage Q report had `LAB_CLIENT_LAUNCHED_NOT_GAMEPLAY_VERIFIED`: it checked launch, **not** process survival.

**Recovery:** `ORIGINAL_LAB_PROCESS_ALIVE_AFTER_12S`, original restored SHA `52e7956d...79885d9`, empty application error events list. This proves original can launch in the LAB directory but not overall gameplay success.

**Stage R:** patched EXE SHA `02f51bb...23daf`, checksum `0xe73456`, `.pdata` function new exclusive end `0x6c9f7f`, changed 59 bytes. User's exact output: `LAB client exited quickly; restoring original LAB EXE automatically.` Then `LAB_ORIGINAL_RESTORED`, original EXE SHA verified, no patched EXE remains active. Stage R did **not** solve startup. No runtime exit code or error origin proven.

## Server/client mapping warnings

- `MainCmd(485)` sent `qdIdx=4380`, rejected in `OnCSCQDungeonLimitCheck`, followed by `UsrMap Fail` disconnect. There is no verified full mission-dungeon definition for 4380 in audited `[MD]` sections.
- 4380 in a `[MMap]` section is a **mob index** not `QDungeonIdx`. Avoid using it as evidence that dungeon 4380 exists.
- `World 8 / Warp 675` reference data includes IDs 4378–4383, but that XML **is unverified for v291**.
- 4352 is an existing mission dungeon in world 138 and is not a safe substitute for 4380.

## Test counting principle

Offline PASS counts only test scripts/static checks. **Do not claim** that 20/20 or 27/27 offline passes establish a successful Windows client startup or corrected Warp behavior. Windows testing **invalidated** the Stage P/Q/R candidates.