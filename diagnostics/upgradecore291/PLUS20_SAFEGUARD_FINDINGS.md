# 2026-11-21 +17 to +20 and Safeguard evidence

## What is confirmed
- The prior opcode 951 RAM-only length-base fix is working in-game; Upgrade Core now works to +17. User says +18 to +20 and Safeguard still fail.
- Read-only inspection of the archived SHA-matched WorldSvr `caec7772...` and full VPS archive found the actual **extended** normal-upgrade config `home/data_main/cabal/Data/Enchant.scp` — **not** just `Core.scp`.
- `Enchant.scp` section `[EnchantExtendLimit]` has `MaxEnchant=20` across equipment grades (archived copy). `[EnchantExtend]` has `Apply_LV=16`. `[EnchantExtendRate]` begins with rows indexed 0..4 and includes `PerfectCoreNeeds`, `CoreNeeds`, `EnhancedNeeds`, `SuperiorNeeds`, outcomes and rates.
- The archived `Enchant.scp` sha256 is `7710a53ab9dc76ea392fd10e073ad0d6c1703a52a8894590ba0fca15515c0db6`, identical to a backup archived copy. This does **not** establish which actual copy the running VM loads.
- The archived `home/data_main/cabal/Common.ini` contains `ChinaScrollSafeguard=1`. This alone does **not** establish working Safeguard packet support.
- `Core.scp [EnchantRate]` covers 0..14; 16..20 are handled through `Enchant.scp` extensions, so no new `Core.scp` rows should be fabricated.
- WorldSvr contains native `EnchantExtendLimit`, `EnchantExtendRate`, `EnchantExtend_Core`, and `ChinaScrollSafeguard` string references. The old `WorldSvr_01_01.ini MaxUpperGradeCoreEnchantLv=12` is a *separate* setting, not evidence that normal enchanting is capped at 12 or 17.
- CI source: https://github.com/patmalnieksgatis-netizen/cabal-ep36/actions/runs/44906703170

## What remains unconfirmed and what to capture
- Whether +17 -> +18 is blocked client-side (no `MainCmd 951` emitted) or rejected server-side (a 951 request and subsequent stderr error). No +18 runtime trace yet.
- Whether Safeguard selection changes opcode 951 bytes (including the extended 120 bytes), or sends a different command entirely.
- To compare full 259-byte requests without gdb or VM internet, the conversation includes `CABAL_951_SAFEGUARD_COMPARE.ps1` and zip package with helper source. It does **read-only** ptrace hardware-breakpoint capture and a byte-offset diff between one normal test and one Safeguard-enabled test. For +18 use `-Case plus18`. It does not change server bytes, SQL or configuration; the in-game test itself can consume items.

Do not remove item/slot validation or patch arbitrary +20 checks without a decoded live failure. The success of 951 length-base patch is not proof of Safeguard semantics.
