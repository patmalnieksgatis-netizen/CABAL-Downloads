# CABAL v291 Diamond Insignia — V11 real-byte analysis (2026-11-22)

## Input integrity and scope
Owner-supplied `CABAL_DIAMOND_MERIT_X64_V11_20261122-194018.zip`, SHA256 `60c87b08f78fd5fb5993d9682f846399727084bf1cf13379c9cbeedb7bc1b493`. Contains `MERIT_X64_V11_REPORT.json` (schema 11) and README. Report EXE SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`, merit ENC SHA256 `3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a`. All five exported byte regions were disassembled with GNU objdump in 64-bit mode at original RVA. No process, VM, client or SQL edits.

## Verified V11 instruction bodies
- `0x2B7A90` = raw 2048-byte window with **NO PDATA**, so **not** one proven 2048-byte function. Its initial routine ends at `0x2B7B09 ret` and is followed by two INT3 bytes and unrelated `0x2B7B0C` code. Input context `[rcx+8]` byte pointer, `[rcx+0x14]` cursor, `[rcx+0x10]` upper-bound check. Cursor positions 0,1,2,3 each XOR the underlying byte with `0x92,0x65,0x67,0x57`, respectively; positions >=4 return byte unchanged. Out-of-range yields `0xFFFFFFFF`.
- `0x2B83F0..0x2B8897` = complete PDATA function, 1191 bytes (SHA256 `2c5d515d38db061f1201114a92c5287da2a41157617960a36aec682b862e81f2`), interprets 5-bit HLIT (+257), 5-bit HDIST (+1), 4-bit HCLEN (+4), validates HLIT <=286 / HDIST <=30, then constructs dynamic Huffman structures and calls byte reader. Matches DEFLATE BTYPE 2.
- `0x2B8898..0x2B89F0` = complete PDATA function, 344 bytes (SHA256 `d1c643915b373332ac0598bcc85b9e6e8197ebc881977e0b4a0789d58e14b723`), prepares fixed code-length tables: 144 eight-bit symbols, 112 nine-bit symbols, 24 seven-bit symbols, and distance-code lengths. Matches DEFLATE BTYPE 1.
- `0x2B89F0..0x2B8B07` = complete PDATA function, 279 bytes (SHA256 `6dd72bb1836b05248d6096e043bd0097141cc845f0d794458e2ead76860d0d62`): aligns to byte boundary, reads LEN/NLEN, validates `LEN == (~NLEN & 0xFFFF)`, copies stored bytes through 0x2B7A90. Matches DEFLATE BTYPE 0.
- `0x2178E0..0x217A5C` = complete PDATA loader, 380 bytes (SHA256 `66a3c8be159ffbc4e8d9ff9243fe0705a5764413e8ce146fff6a7eff7140d0af`). `0x21793F` calls `SetFilePointer(FILE_END)`; subtracts 4 at `0x21794B`, seeks at `0x217957`, reads four bytes via `ReadFile` at `0x217975` into pointer supplied in `rbp`, and seeks to offset 4 at `0x217987`. Later maps file via `CreateFileMappingA`/`MapViewOfFile`, creates input pointer `mapped+4` at `0x2179C7`, allocates output from the *trailer value* `[rbp]` at `0x2179D0` and calls wrapper `0x2B7FAC` at `0x217A17`. Import slots validated by V11 report, not inferred from nearest IAT address.

## Strong new distinction: available assets do NOT fit this loader as raw files
Owner's independently SHA-verified archive has one `Data/meritsystem.enc` and 13 localized `meritsystem_msg.enc` files. Example primary file (41368 bytes):
- First DWORD `26 1f 0a 00` = 663334.
- Following four bytes `0d 46 ef 53`; XOR4 yields `9f 23 88 04`, first DEFLATE block BTYPE=3 (reserved).
- Last DWORD `5b 2f f2 58` = 1492266843, not a plausible authenticated output size for this small static Merit resource.

A bounded offline test of all fourteen sources, taking `file[4:-4]` and XORing **only four bytes at its beginning** before standard raw DEFLATE, produced 0/14 successful streams. All fourteen trailer DWORD values are large and do not resemble credible decoded size bounds. This is specific to this presumed mapping and not proof of corrupted files.

**Crucial limitation:** the initial loader reading the 4-byte trailer and the file-search resolver may apply to a different resource format or path; a static CALL chain is not evidence that the exact user `Data/meritsystem.enc` is opened and fed into it during gameplay. Do NOT rewrite ENC, guess AES/XOR key, or call the present files unusable.

## Next required source evidence
1. Trace `0x21CDA4 -> 0x21CBD4 -> 0x2178E0` with resource ID 52/53 and actual path selection, including any switch between `\Language\` and `\Data`. Static code proves selection but not runtime opened path.
2. Before proposing a decoder: identify whether an intermediate buffer or additional transformation exists between file mapping and the byte-reader context at `[rcx+8]` and `[rcx+0x14]`, including `0x2B7FAC` wrapper setup. The available V7/V8 assembly and V11 can constrain the answer; do not label unknown fields.
3. Diamond UI button -> actual client C2S opcode/packet remains unproven. The `0x09F3` command is confirmed **Merit**, not Diamond-specific.
4. WorldSvr live integration and actual game item 33554961/WExp/MSSQL durable transaction, response ACK and VM clone regression remain unimplemented. Never repeat old `lib.so`/sidecar deployment after exit 78 without restoring/parity evidence.

**Status: static DEFLATE and loader evidence PASS; playable Diamond NOT READY.** No game, VM, SQL or account data modified.
