# 2026-11-21 +17 to +20 and Safeguard evidence

## What is confirmed
- The prior opcode 951 RAM-only length-base fix is working in-game. **Clarified by user: ordinary Upgrade Core works all the way to +20; Perfect Core stops at +17; Safeguard does not work.** These are separate feature-specific failures.
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


## 2026-11-21 follow-up: Exact live Safeguard packet and server mismatch

User reproduced two requests with the live 951 hardware breakpoint:
- base: declared length 259, escapeSlotCount 0, coreSlotCount 1, first core slot 42 at offset \`0x13\`.
- with Safeguard: declared length 261, escapeSlotCount 1, first core slot 42 still at offset \`0x13\`, **Safeguard slot 132 at trailing \`0x103\`** (the last two bytes \`84 00\`). The earlier comparator failed to show these trailing bytes because it compared only common length.
- The two requests have correct wire length for the existing RAM length-base change \`259+2*escapeSlotCount\`. **DO NOT revise 951 length again.**

Static verified exact WorldSvr (SHA \`caec7772...\`) at \`0x7AC574\` in the 951 normal-core handler:
\`41 0f b7 47 13\` -> \`movzx eax, WORD PTR [r15+0x13]\`. This is the legacy safeguard slot extraction path and points to the **core slot 42**, not the newer trailing Safeguard slot 132. Next instruction \`cmp ax,0x209\` still performs inventory index range validation.

A **one-request RAM register redirect** test helper exists as conversation artifact
\`CABAL_951_SAFEGUARD_ONE_SHOT.ps1\` (and source bundle zip).
It requires the working prior opcode 951 259-base RAM compatibility patch to already be active. It sets a hardware breakpoint at \`0x7AC574\` on all WorldSvr threads, verifies exact native code and the active 259-length instruction, checks 261-byte one-Safeguard packet layout, reads the real Safeguard slot from \`packet+259\`, replaces **only stopped thread RAX and RIP** to skip the stale slot-read instruction, and lets all subsequent server validation run. No code/data file writes or restart. It applies **once**, not persistently. It passed 3 synthetic ptrace tests (valid one-shot, malformed packet stops without change, missing 259 RAM patch stops without change).

This is an **unverified CABAL gameplay compatibility trial**; do not claim Safeguard works until the user confirms actual protection behavior. No item permission/binding checks are removed.

## 2026-11-21: Actual one-shot safeguard run and logging-only crash

User's runtime log confirms `REGISTER_REDIRECT_APPLIED_ONCE`, actual core slot **133** (not prior example 42), Safeguard slot **132**, and replacement `EAX=132`, next RIP `0x7AC579`. The WorldSvr process was still the same PID afterwards. This proves the register redirect occurred, **not** that Safeguard protected an item.

Then Python log-redaction postprocessing failed with `re.error: invalid group reference 1`. Specifically `re.sub(r'\\b(?:userNum|CharIdx|Addr)\\([^)]*\\)',r'\\1([redacted])',line)` references capturing group 1 in replacement but used a **noncapturing group** in pattern. Correct to `r'\\b(userNum|CharIdx|Addr)\\([^)]*\\)'` (the user-facing script `CABAL_951_SAFEGUARD_ONE_SHOT_V2.ps1` implements this). No need to rerun the one-shot merely to fix logging.

Also created separate read-only `CABAL_951_SAFEGUARD_RESULT_CHECK.ps1` to query latest WorldSvr stderr and supervisor state via SSH, *without any new in-game action, breakpoint, RAM change, or restart*. In-game Safeguard protection result still requires player confirmation.


## 2026-11-21: Correction — ONE_SHOT patched the WRONG core-slot lookup; correct Safeguard array base now found

**User confirmed the previous one-shot 0x7AC574 experiment did NOT make Safeguard work.** That instruction reads the first **Upgrade Core** slot at \`packet+0x13\` and the earlier redirect to slot 132 was conceptually wrong. Do not run that helper again; it did not leave a persistent modification.

The **verified actual safeguard processing** is later in the exact original WorldSvr 951 handler:
\`\`\`
7ad73c  45 0f b7 47 11        movzx r8d, WORD PTR [r15+0x11]    ; escape count
7ad741  48 8b 95 40 fc ff ff  mov rdx, QWORD PTR [rbp-0x3c0]
7ad748  49 8d 8f 8b 00 00 00  lea rcx, [r15+0x8b]                ; WRONG old array address
7ad74f  89 c6                 mov esi,eax
7ad751  4c 89 e7              mov rdi,r12
7ad754  e8 07 e5 ff ff        call 7abc60                         ; normal existing checks
7ad759  84 c0                 test al,al
\`\`\`
Live client sent \`escapeSlotCount=1\` with Safeguard inventory slot **132**
at **packet+0x103**, rather than the old server \`packet+0x8b\`.
The exact packet extension delta is **120 bytes**, so the correct narrow
compatible pointer is \`lea rcx,[r15+0x103]\` with machine-code bytes
\`49 8d 8f 03 01 00 00\`. Modify ONLY displacement bytes at
\`0x7AD74B\` and \`0x7AD74C\` (0x8B00 → 0x0301).
This pointer is passed directly with the escape slot count to
the existing server validation function, so **do not bypass its checks**.

Source disassembly from archived SHA-matched native WorldSvr in
https://github.com/patmalnieksgatis-netizen/cabal-ep36/actions/runs/44910711871

Conversation-delivered test-VM-only artifact:
- \`CABAL_951_SAFEGUARD_OFFSET_RAM.ps1\` (single PowerShell 5.1 file)
- \`CABAL_951_SAFEGUARD_OFFSET_RAM_BUNDLE.zip\` (C helper, Python loader, test target/source, notes)

This tool has \`-Action check|apply|rollback\`, uses ptrace to stop all
WorldSvr threads, verifies SHA and **31 original code bytes** around the
exact patch site, **requires the existing 259-byte 951 length RAM patch** to
remain active before applying, changes exactly 2 bytes in memory only,
revalidates, detaches and leaves the already working +20 length patch
unchanged. No on-disk changes, no SQL changes and no service restart.

**Nine synthetic ptrace operations passed** against a 9-thread Linux process:
read-only check, apply, readback, idempotent apply, rollback, readback,
idempotent rollback, reject when the first 951 RAM patch is missing,
and verify code unchanged after that rejection.
Static signature also byte-for-byte matches original GitHub Actions
disassembly. **Not yet applied on the real WorldSvr and not yet confirmed
in-game**. A normal WorldSvr restart will erase all RAM patches.

**Perfect Core +17 remains separate/unfixed.**
