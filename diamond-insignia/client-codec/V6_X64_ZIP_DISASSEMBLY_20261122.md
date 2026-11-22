# CABAL v291 x64 Merit / Diamond — independent V6 ZIP disassembly (2026-11-22)

## Source, integrity and scope

Independent analysis of owner-uploaded `CABAL_DIAMOND_MERIT_X64_V6_20261122-092848.zip`, SHA256 `e3847417d3de7af9840caeb78858cd37a25d515aa815c6bd93121d263aa8fea3`, JSON `MERIT_X64_V6_REPORT.json`, schema 6. Pinned x64 source executable SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`; merit data SHA256 `3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a`. All ten PDATA code bodies are fully provided and correctly match the reported byte lengths; machine-code bytes were disassembled independently with GNU objdump `i386:x86-64` from their exact declared RVAs.

The export was generated read-only. No game run, process memory, server/VM or SQL modifications. Labels below are analyst names, **not original function symbols**. Original EXE and ENC bytes are not stored in the ZIP.

## Breakthrough: `0x2178E0–0x217A5C` is a genuine mapped-file resource loader

Verified direct machine-code sequence:

- `0x21791C: call [0xB32558]` with `EDX=0x80000000` (generic read) and creation disposition `3`, then checks handle for `-1`.
- `0x21793F`, `0x217957`, `0x217987: call [0xB325D8]` seeking through the file.
- `0x217975: call [0xB32570]` with requested byte count `4`, writes the apparent 4-byte length/header into pointer from `R8` of outer wrapper.
- `0x2179A3: call [0xB325F8]`; `0x2179BE: call [0xB325E8]`; strong argument-based indication of read-only file mapping and view.
- `0x2179D7: call 0x9F8F14` allocates a buffer with length based on first 4 bytes; `0x2179DC` stores pointer to output resource slot; `0x2179F1` increments stored size field.
- `0x217A17: call 0x2B7FAC` after `RCX=&[rsp+0x40]` pointing to output slot/buffer. **This is the next high-priority transformation/decoder candidate; behavior unknown until its body is inspected.**
- `0x217A24` frees auxiliary buffer, and `0x217A2C/0x217A35/0x217A3E` use indirect API calls for mapped view/handle cleanup.

The Win32 function names above are provisional from calling conventions; **V6 reports exact names only for `0xB329F8` and `0xB32C28`**, not these six loader IAT slots. Confirm these slots using the fixed per-descriptor parser before claiming exact names in code/release notes.

## Wrapper and startup

- `0x21CDA4..0x21CE36` calls path resolver `0x21CBD4` at `0x21CDC6`. Converts the returned string pointer according to SSO length (length >=16 uses heap pointer), computes resource slot as `base + id * 16 + 8`, and invokes `0x2178E0` at `0x21CDE6`. This establishes the real link **resource ID -> resolved file path -> mapped-file loader**.
- `0x21CE38..0x21D35B` calls this wrapper in a loop with indexes `0..0x84` (133 slots, `0x21CE6E..0x21CE80`), and then moves into a separate initialization/parsing path. It invokes the same loader at `0x21D19E` after constructing an additional filename with `0x21A724`.
- `0x21BB98..0x21CBD2` is an ID-indexed source filename selector, with a long comparison tree. Direct 64-bit literals include `data.enc` and `cont.enc`; many other names come from `RIP`-relative `.rdata` pointers around `0xB5EBxx..0xB5F4xx`, **not supplied as raw rodata by V6**.
- `0x273C8` is a short byte-string assign/copy helper; `0x27350` is a short append helper. Both have buffer-size/SSO paths.
- `0x6828A0` requests resource ID `0x89` using the filename resolver, then passes the path string to `0x1F5914` with subsequent data processing. This is distinct from the bulk loop, and its meaning cannot be named Diamond without actual file text. The prior classifier `0x21D938` returned false for ID `0x89` in the V5 report.

## Independently grounded imports

The corrected V6 parser confirmed:
- `0xB329F8 = SHLWAPI.dll!PathFileExistsA`
- `0xB32C28 = USER32.dll!MessageBoxA`

V5's earlier `DINPUT8.dll` owner label for those slots was a parser error and has been corrected in the V5 report.

## V7 priorities

1. Export the complete PDATA-bounded body containing **`0x2B7FAC`** and trace whether it is copying, decrypting, decompressing or parsing mapped bytes.
2. Verify actual IAT names at `0xB32558`, `0xB325D8`, `0xB32570`, `0xB325F8`, `0xB325E8`, `0xB325F0`, `0xB32420` using the corrected descriptor-aware import parser.
3. Extract only a small bounded `.rdata` region `0xB5EB00..0xB5F500` to identify resource names mapped by the selector. Do not claim which numeric ID is `meritsystem.enc` until exact branches and strings agree.
4. Inspect source callers/helpers `0x21A9CC`, `0x21A718`, `0x21A724`, `0x21DE30`, `0x21D9F8`, `0x21DBAC`, `0x2161B0`, `0x1F5914` as bounded static code samples.

**Not yet proven:** Merit `.enc` specific load ID, codec/cryptography, Diamond packet/opcode, server feature or SQL persistence. Do not patch binaries/SQL or copy EP45 ENC without stronger evidence.
