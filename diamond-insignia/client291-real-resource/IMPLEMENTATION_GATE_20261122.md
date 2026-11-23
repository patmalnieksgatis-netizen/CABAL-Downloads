# Diamond Insignia v291 — actual client/resource/runtime integration gate (2026-11-22)

## Completed, independently tested

- Existing client evidence proves Merit resource IDs 52/53 and C2S 0x09F3, exactly 18 bytes.
- Existing client evidence does NOT identify Diamond UI rank-up as C2S 0x09F3. The first/second 32-bit request values are client singleton fields +0x118/+0x11C, not trusted server IDs.
- Existing archived WorldSvr demonstrates 7-byte success/failure in some 0x09F3 flows; conditional client success paths may read 4 bytes at reply+7. Never synthesize an 11-byte success.
- The observed client codec XORs the first four compressed bytes with `92 65 67 57` and then takes a raw DEFLATE stream. The known `Data/meritsystem.enc` does not pass this path. Real runtime filename/path selection has not been observed.
- Added `audit_merit_candidates.py`: bounded offline inspection of every candidate gathered by `Collect-CABAL291-Merit-Resolved-Candidates.ps1`. It verifies the exact client SHA and source manifests, ZIP member integrity, SHA256 of each candidate, declared decoded size, codec match (or exact rejection reason), and never writes to client files.
- Synthetic archive, codec, invalid-size, wrong-SHA, path-traversal and extra-member cases run in `test_audit_merit_candidates.py`. GitHub CI runs both these tests and the strict v291 0x09F3 wire tests.

## Next factual evidence from the owner's Windows machine (no game files modified)

Run existing repository `Collect-CABAL291-Merit-Resolved-Candidates.ps1` against `F:\CABAL_291_TEST`. The script reads the exact EXE hash, inventories resources under client root, and creates `CABAL_v291_Merit_Actual_Path_Candidates_20261122.zip` in Downloads. Run the offline analyzer:

```sh
python3 audit_merit_candidates.py CABAL_v291_Merit_Actual_Path_Candidates_20261122.zip --report merit_candidate_audit.json
```

Even a valid candidate is only a file-format match, NOT evidence of the actual runtime opened file. True runtime file-open evidence or verified route globals are needed to establish it.

## Remaining hard gates before gameplay

1. Diamond UI click-to-C2S handler and packet contents must be proven on the exact v291 client. No guessing that 0x09F3 or Platinum grade-up 0x0B10 is a Diamond rank-up message.
2. Match exact WorldSvr authenticated-session authority and Diamond-specific request/response. Existing `world-session-bridge`, `commit-gate`, `world-save-barrier` and `odbc-backend` are source/offline-test components, not live game hooks.
3. Actual item 33554961 inventory, WExp and Merit progression must be tied to a durable game save and SQL transaction with crash/replay recovery. Synthetic shadow-wallet SQL is not actual gameplay persistence.
4. Perform functional testing ONLY on an isolated VM clone with verified rollback and known-good Supervisor configuration. Prior `lib.so`/sidecar deployment caused exit 78 and restoration, so neither must be reused blindly.

**Live user VM, WorldSvr, lib.so, Supervisor, account rows and game client remain unchanged. Diamond NOT playable.**
