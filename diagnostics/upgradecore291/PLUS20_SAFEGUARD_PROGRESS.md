# CABAL v291 +20 and Safeguard follow-up — 2026-11-21

## User acceptance report
After applying the isolated opcode-951 **RAM-only length compatibility patch** (139->259), normal Upgrade Core now works but only up to **+17**, while the desired maximum is **+20**. Safeguard option still fails.

## Facts verified from archived SHA-matched native WorldSvr
- Native binary SHA256: `caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3`.
- Legacy 951 packet length `139+2*escapeSlotCount`; the captured v291 request length is **259**; delta **120**.
- 259 bytes = 19-byte prefix + 2 * 60 * 2 bytes; the additional 120-byte fixed-sized block may affect Safeguard, but this structure is **not yet verified** by a capture with Safeguard selected.
- Archived `Core.scp` **[EnchantRate] ends at level 14** (source rows 0..14). Rows beginning with 17-20 in the same file are **different tables**: `[EpicConvert]` and `[dSTAT]`. Do not misidentify them as +20 normal upgrade rates.
- Native WorldSvr includes `EnchantExtendLimit`, `EnchantExtendRate`, `EnchantExtend_Core`, `PerfectCoreNeeds`, `MaxEnchantLevel` and `ChinaScrollSafeguard`. Their presence does **not establish** complete compatibility with v291.
- Archived WorldSvr_01_01.ini has `MaxUpperGradeCoreEnchantLv=12`. This does not match observed +17 as an obvious direct cap; **do not blindly change the setting to 20**.
- Source read-only archive audit: https://github.com/patmalnieksgatis-netizen/cabal-ep36/actions/runs/44905920359
- Deep native config and string-xref audit: https://github.com/patmalnieksgatis-netizen/cabal-ep36/actions/runs/44906141618

## Next exact evidence
One read-only hardware-breakpoint collector was built/tested with complete **259-byte** packets (previous collection truncated at 192 bytes). `CABAL_951_CAPTURE_FULL_SAFEGUARD.ps1 -Case base` versus `-Case safeguard` records both private cases and prints changed offsets. The optional `-Case plus18` detects whether a +17 -> +18 attempt sends opcode 951 at all.
The script and native tracer are delivered as conversation download artifacts; **not yet tested in this user's VM**. It does not modify the already-working RAM patch, server executable, or DB.

## Do not merge speculative patch
Need distinguish +17 client UI cap, server extension rate/load cap, or invalid core grade/material; Safeguard packet body and server semantics must be mapped before changing parser. Preserve working +0..+17 and Force/Chaos/Divine. Final functional fix **not yet achieved**.
