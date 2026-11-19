# CABAL v291 / EP39 — Warp 485 Codex handoff (2026-11-19)

**CURRENT STATUS: UNRESOLVED. LAB CLIENT RESTORED. DO NOT REINSTALL STAGES P, Q, R.**

This folder preserves technical work produced by ChatGPT for `MainCmd(485) -> invalid qdIdx(4380) -> UsrMap Fail -> disconnect` in the user's EP39/v291 CABAL test project. It is a historical investigation and source archive, **not** a tested gameplay fix.

## For Codex — start here

1. Read `STATUS.json` for machine-readable facts and current constraints.
2. Read `HISTORY.md` for stage chronology and previous Windows outcomes.
3. Browse `source/stage-*/` and `source/clientpatch/` for all recovered **text-only** scripts/tests/reports. Stages P/Q/R are a **failed startup approach**, not active patches.
4. Prefer original signed x64 `CabalMain.exe`, check its SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`. Original `mapinfo.enc`: `88f7694e476e1ebe5cf55014657194fcc2a4b61c2d83d8c908bf823e538b63fc`.
5. User has an existing v291 launcher/SDK integration in this repo (`Client291-LoginStart-v4_9_5.zip`, later profiles), but check their README/manifest: many were Windows-unverified or withdrawn. Do not blindly reuse or modify production without audit.

## Guardrails

- No modification of the active server/WorldSvr, SQL, or the working `F:\CABAL_291_TEST` client.
- `F:\CABAL_291_LAB` currently contains the **restored original EXE** after Stage R quick-exit rollback.
- Stage Q copied 57,764 client files (~14.67 GB); **do not copy the game a second time** for every test.
- Stage P and R modified signed PE. Stage Q and Stage R **both closed quickly during real Windows launch**. Stage R corrected checksum and `.pdata` but still failed.
- Client binary has Authenticode signature and imports `SecureEngineSDK64.dll`. Integrity rejection is *possible*, not proved by present logs.
- Offline static tests do not prove Windows startup or warp behavior.
- Reference-only XML may belong to a different CABAL client and is **not** authenticated v291 resource data.
- Never change `4380` into `4352` or `4378` without evidence of compatible dungeon semantics.

## Included / deliberately excluded

**Included:** original source files (`.py`, `.cs`, `.cpp`, `.ps1`, `.cmd`), test code, runbooks, selected offline test logs, manifests and static disassembly (`.txt`) from Stage B/C, E–R, ClientPatch and LAB startup recovery. `MANIFEST.json` records per-file SHA256 and original ZIP SHA256. Exact original binary snapshots are not included.

**Excluded:** full CABAL EXE, `*.enc` resource files, private server snapshots/archives, 3rd-party reference XML/DEC, nested ZIPs, compiled patch binaries and huge logs. This is intentional for public GitHub. Obtain exact authorized binaries privately as needed; do not commit them.

## Important addresses and evidence

- Client packet builder VA `0x1406C9F30` (RVA `0x6C9F30`) builds 14-byte `MainCmd(485)` packet, inserts 32-bit `qdIdx` at offset `+0x0A` from `0x14120CC68`; registration xref at `0x1406C7047`.
- Patch file offset `0x6C9330`, 80-byte function code block. Stage P/Q patched hash `ef4fd980520d52d6ede0785d5de42d7ed90045acfe56c2f86be89c6e317869d1`.
- Stage R hash `02f51bb0051243b9da3b4730fc030f6dda491cb691551999e1df0df0ac123daf`, PE checksum `0xe73456`, `.pdata` end RVA `0x6C9F7F`. **Windows quick exit persisted.**
- Runtime Stage J `mapinfo` cache entry 28: pointer `NULL`, size `49102`, read after load failed. Cache release function can clear pointer while size remains; do not chase pointer late in startup.
- `QuestDungeon.scp` occurrence `4380` corresponds to `MobIdx` under `[MMap]`, **not** proof of `[MD] QDungeonIdx=4380`. `MissionDungeon2.scp` has `[MD] QDungeonIdx=4352` on world 138. Warp 675 references world 8, not 138.

## Next engineering steps

1. Confirm the exact origin and semantics of invalid `qdIdx=4380` in an *authentic v291 client resource/runtime state*, not reference-only XML.
2. Reuse audited original-client/SDK launcher diagnostics *without changing signed EXE*; observe callback at `0x1406C9F30` in authorized isolated game session to see why 4380 was selected.
3. Prefer fixing the actual client mapping/protocol cause; alternatively build a **server-side bounded error response** in an isolated test server to avoid disconnect on unknown ID, while keeping validation intact. No unconditional silent guard is a full fix.
4. Validate startup, connection, warp action, no disconnect, and unaffected dungeons in a real game test. Maintain rollback and clear proof.

Prepared for Codex handoff; see `STATUS.json`, `HISTORY.md`, and `MANIFEST.json`.