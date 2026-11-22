# CABAL v291 Diamond — actual Merit ENC structural comparison (2026-11-22)

## Source provenance and scope

Based exclusively on owner-uploaded `CABAL_v291_Merit_Actual_Path_Candidates_20261122.zip` and its 14 individually SHA-verified resource entries. Source archive SHA256:
`5fb0ac8829542244ba9425691f372e0bed6a4d9d360b70fa96e967ac7b19e830`.
The manifest pins the exact client SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`.

**This is a structural data audit, NOT a decoded ENC, runtime trace, Diamond packet handler, or deployed patch.**

## Confirmed observations

- 14 resource members: **1** main `Data/meritsystem.enc` and **13** localized `Data/Language/<locale>/meritsystem_msg.enc`; no locale-specific `meritsystem.enc` member.
- The first four bytes of each file form a little-endian length-looking word. Examples:
  - Main: 41,368 bytes on disk, prefix `26 1f 0a 00` = 663,334 (if interpreted as uncompressed length).
  - English message: 9,328 bytes on disk, prefix `49 84 01 00` = 99,401.
  - Korean message: 7,658 bytes on disk, prefix `5c 66 01 00` = 91,740.
- Byte entropy across encrypted/compressed candidate payloads (all bytes after the 4-byte prefix) ranges **7.9467 to 7.9953 bits/byte**. Entropy indicates high variability but **does not distinguish encryption from compression**.
- Korean and Portuguese message resources have the *same* four content bytes after the length word: `3c 97 3c a1`, despite different file lengths and hashes. This is a reproducible pattern, **not proof of shared cipher, key, or decoded content**.
- Exact v291 client opcode evidence for one codec path: first four compressed bytes XOR `92 65 67 57` then raw DEFLATE. The complete previously measured **0/14 decoded candidates** remain inconsistent with this simple interpretation. This alone cannot establish the actual runtime pipeline; additional transformations, per-resource paths, or different wire/file layouts are possible.

## Engineering conclusion

**No supported basis exists yet to assign a new encryption key, change the game's ENC files, or declare the resource broken.** Prioritize a read-only verification of the 0x2178E0 -> 0x2B7FAC -> 0x2B8B08 -> 0x2B8004 -> 0x2B7A90 call chain with actual data-pointer/length provenance, especially whether 0x2B7A90 receives the raw file bytes or an intermediate buffer. Confirm real 52/53 file resolution before equating a path candidate with the opened file.

## Exact remaining runtime boundaries

- Diamond rank-up / mastery UI event -> C2S opcode and payload **NOT PROVEN**.
- Authenticated session and actual inventory 33554961/WExp + durable SQL transaction **NOT HOOKED INTO LIVE GAME**.
- VM clone regression (relogin, duplicate requests, rollback, Core/Platinum/Costume) **NOT EXECUTED**.
- Prior WorldSvr exit 78 means do not run archived lib.so, sidecar installers, or Supervisor changes without exact snapshot/source parity and rollback gates.

The full read-only structure inspection script and JSON report were produced as conversation artifacts; no proprietary resource bytes were committed to public GitHub. The active user VM, client files, and database were not touched.
