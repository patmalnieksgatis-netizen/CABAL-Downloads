# Diamond Insignia v291 — exact client ENC loader audit (22 Nov 2026)

**Not deployable. Read-only source evidence**, not a Diamond gameplay patch.

The user's pinned v291 64-bit client \`CabalMain.exe\` (SHA256 \`52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9\`) contains a codec at RVA \`0x2B7A90\` that XORs exactly the first four bytes of a compressed stream with \`92 65 67 57\`. An \`.enc\` reader at \`0x2178E0\` reads the uncompressed size from bytes \`0..3\`, then passes input \`+4\` to the above inflate call chain. The proof checks five direct CALL edges, including \`0x217A17→0x2B7FAC\` and \`0x2B802A→0x2B7A90\`.

The user's \`Data/meritsystem.enc\` (SHA256 \`3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a\`) begins \`26 1F 0A 00 | 0D 46 EF 53\`. Raw DEFLATE after the proven client XOR would start \`9F 23 88 04\`. The first byte has DEFLATE block type 3 (reserved), so **this exact file is incompatible with this observed standard loader path as-is**. It might use a separate decoding route, or be an asset from a different packaging version; this is not yet proven to cause Diamond failure.

Run \`python3 verify_exact_enc.py /path/CabalMain.exe /path/meritsystem.enc\`. It is read-only and exits 2 on an incompatible file. The full standalone decoder with a bounded output buffer, synthetic positive tests, additional parser disassembly evidence and JSON report are in the conversation artifact \`CABAL_v291_Diamond_Exact_ENC_Codec_20261122.zip\`; no proprietary binaries are committed to GitHub.

More client findings:
- \`Badge_Grade\` string has a static RIP reference inside v291 Merit base parser function \`0x245B4C–0x2462C2\` (reference RVA \`0x245D1B\`).
- \`upgrade_badge\` and \`upgrade_wexp\` are read in Merit upgrade parser \`0x246CAC–0x2472E8\` (RVA \`0x246E84\`, \`0x246EC0\`).
- These are generic Merit parsers. There is **no proof** of Diamond UI/command/grade-3 support from these references alone.
- Separate \`0x09F3\` response evidence remains confined to legacy Merit, not proved Diamond Insignia.

No live WorldSvr, \`lib.so\`, Supervisor, MSSQL, client EXE or assets were changed. Do not deploy old patched lib.so/sidecar (prior exit 78). Next must identify exact v291 Diamond event or find a matching decoded \`meritsystem.enc\` before generating a client/server patch.
