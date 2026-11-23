# CABAL v291 Diamond — V9 actual bytes: DEFLATE block dispatch proven (2026-11-22)

## Provenance

Recovered the owner's earlier uploaded `CABAL_DIAMOND_MERIT_X64_V9_20261122-095035.zip` from their file library; its `MERIT_X64_V9_REPORT.json` has schema 9, both SHA-pinned sources and explicit no-mutation markers:

- `Bin/x64/CabalMain.exe` SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`.
- `Data/meritsystem.enc` SHA256 `3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a`.

Disassembled V9 exported PDATA-bounded `buffer_processing_step` RVA `0x2B8004–0x2B80CE`, **202 exact bytes** with SHA256 `41b11c0d71c27c99771d27ac44ab6694b0225781d6439400567c3d1f73a4b3a3`. These are real reported client bytes, **not invented instructions**.

## New independently verifiable main finding: DEFLATE bit-block selection

The previously ambiguous routine `0x2B8004` has an unmistakable DEFLATE block-type dispatch:

- `0x2B802A` and `0x2B8059` call the same byte supplier `0x2B7A90` when fewer than 1 or 2 buffered bits remain, respectively.
- `0x2B8034–0x2B803A` and `0x2B8063–0x2B8069`: fill bit accumulator via shift/OR and increment available bit count by 8.
- `0x2B8042–0x2B804C`: extract one bit `esi & 1` to output pointer `[r14]` (DEFLATE BFINAL-compatible), then shift bit accumulator right by one.
- `0x2B8071–0x2B807F`: extract next two bits `esi & 3`, shift accumulator by two and persist bit state in context offsets `+0x18`/`+0x1C` (DEFLATE BTYPE-compatible).
- The two-bit value controls the exact direct calls:
  - BTYPE 2 -> `0x2B808A: call 0x2B83F0` (dynamic Huffman path candidate);
  - BTYPE 0 -> `0x2B809F: call 0x2B89F0` (stored/uncompressed block candidate);
  - BTYPE 1 -> `0x2B80AE: call 0x2B8898` (fixed Huffman path candidate);
  - BTYPE 3 -> `0x2B80B5: mov eax, 2` (reserved/error).
- An unavailable byte at the `0x2B7A90` callee returns `0xFFFFFFFF`; `0x2B8091` maps that to status 1.

The correspondence with standard DEFLATE BFINAL/BTYPE bit widths and 0/1/2/3 dispatch is strong. Precise behavior inside the three block-specific callees still requires extracting their instruction bodies. This does **not** prove which ENC file byte offset or pre-transform is fed into this bit reader.

## Other V9 function results

- `buffer_copy_like_callee` PDATA RVA `0xA37890–0xA37C65`, all **981 bytes**, SHA256 `e5f1faf544aa244619d12dd2f5faf56e90e53655a09946f7614f861807cce9ed`. Disassembly starts with dst `rcx`, src `rdx`, count `r8`; fast small-size paths use XMM/moves, and larger path handles overlap. This is a `memmove/memcpy`-style routine, not the ENC cipher.
- `linked_buffer_free_callee` at `0xA6BE2C` has **NO PDATA**. Its exported first bytes set stack local to zero and jump to `0xAA500C`; the next bytes contain INT3 separators and other distinct short functions. The 2048-byte window is **not one single function**. Do not infer full allocator/free semantics from the whole raw window.

## Cross-check against actual owner's 14 candidate ENC files

The original `Data/meritsystem.enc` starts `26 1f 0a 00 0d 46 ef 53`, and the tested XOR4 scheme `92 65 67 57` applied to bytes 4..7 gives `9f 23 88 04`. First byte `9f` has BTYPE 3, which this real dispatch would reject if the stream were fed directly as assumed. **Therefore the basic input-pointer / transform assumption is not yet proven for the real runtime file.**

The same source main file ends with `5b 2f f2 58`, not the plausible uncompressed-size-looking first DWORD. Earlier notes disagree about which 4-byte field is the decoder length; do not resolve this by guessing. Verify the actual file mapping, offset/length and `0x2B7A90` input pointer before modifying any file.

## Next exact extraction

Export PDATA-bounded byte bodies of `0x2B83F0`, `0x2B89F0`, `0x2B8898` plus the full byte-reader `0x2B7A90` and original loader `0x2178E0`; disassemble and derive the real input byte provenance and status flow. Hash-pin all originals, read-only. No client/VM/SQL mutation.

**Diamond UI->C2S, WorldSvr inventory/WExp/SQL and playable Diamond remain NOT PROVEN.**
