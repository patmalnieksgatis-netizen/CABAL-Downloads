# CABAL v291 Diamond — owner's actual Merit candidate archive (2026-11-22)

## Source
Uploaded `CABAL_v291_Merit_Actual_Path_Candidates_20261122.zip`, SHA256
`5fb0ac8829542244ba9425691f372e0bed6a4d9d360b70fa96e967ac7b19e830`.
Manifest pins v291 x64 CabalMain SHA256
`52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`.
This inventory is read-only; it does NOT prove which file is actually opened at runtime.

## Verified manifest / contents

14/14 member SHA256 and byte lengths match the manifest; no extra ZIP members.
Exactly ONE `Data/meritsystem.enc` of 41368 bytes (SHA256
`3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a`).
Exactly THIRTEEN `Data/Language/<locale>/meritsystem_msg.enc` files:
Chinese(twn), English, German, Indonesian, Japanese, Korean, Portuguese,
Russian(new), Russian, Spanish, Thai, Turkish, Vietnamese.
No alternate language-path `meritsystem.enc` was present under collector's client root.

## Actual codec trial result

The independently verified client-side hypothesis for *one* path
(xor only first 4 bytes of compressed content with `92 65 67 57`,
then raw DEFLATE) yields **0/14 complete decodes**.
10/14 first decoded bytes have reserved DEFLATE BTYPE=3.
Other four enter invalid Huffman-code-length / symbol decoding.
For the primary `Data/meritsystem.enc` the stored prefix is
`26 1f 0a 00 0d 46 ef 53`, declared 663334 bytes, and XOR'd
compressed prefix `9f 23 88 04`, reserved BTYPE 3.

This rejection is specific to the tested XOR4/raw-DEFLATE interpretation.
**Do not claim any file is corrupt.** The game may use other processing stages,
transformations, key sources, or a distinct format branch.

## Next evidence / implementation gates

1. Trace the real execution path after the `flag[52]/flag[53]` routing and confirm what reaches the decompressor (including intermediate transforms). Match against the exact original EXE; don't invent encryption keys.
2. Establish actual runtime-opened file path using verified client path construction/runtime evidence (inventory alone does not establish it).
3. Trace actual Diamond UI click to C2S handler; existing `0x09F3` is verified Merit protocol, not yet proven Diamond-exclusive.
4. Keep the WorldSvr authenticated session / durable inventory+WExp+SQL integration in an isolated clone until true Diamond request/response semantics are proven. No live `lib.so`, Supervisor or SQL writes.

No source binaries, player data or full ENC assets are committed to GitHub.
