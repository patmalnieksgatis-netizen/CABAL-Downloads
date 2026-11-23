# CABAL v291 x64 Merit / Diamond — V5 verified disassembly (2026-11-22)

## Source and verification

Owner-uploaded read-only static collection `CABAL_DIAMOND_MERIT_X64_V5_20261122-092212.zip` (ZIP SHA256 `3257d057b8c847f1484b7db92ba0d2f178dc8f05c9b749b9d92d4a9dbbe484ce`), `MERIT_X64_V5_REPORT.json`, schema 5. Client `F:\CABAL_291_TEST\Bin\x64\CabalMain.exe` SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`. `Data\meritsystem.enc` SHA256 `3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a`.

`selector_wrapper` is a complete `.pdata` function at `0x21CBD4..0x21CDA4` (464 bytes). `selector_posthelper` call target is `0x21D938`, outside the previous `.pdata` entry `0x21D828..0x21D936` and before the next `0x21D9F8..0x21DA8D`. No function boundary was invented.

## VERIFIED: `0x21D938` is a switch/predicate dispatch, NOT a Merit .enc decoder

Disassembly (x86-64, aligned at the actual call target):

```asm
0x21D938  cmp edx, 0x89                    ; supported indices 0..137
0x21D93E  ja 0x21D961                     ; out of range -> false
0x21D940  movsxd rax, edx
0x21D943  lea rdx, [rip-0x21D94A]        ; module RVA base 0
0x21D94A  movzx eax, byte [rdx+rax+0x21D96C]
0x21D952  mov ecx, dword [rdx+rax*4+0x21D964]
0x21D959  add rcx, rdx
0x21D95C  jmp rcx
0x21D95E  mov al, 1
0x21D960  ret
0x21D961  xor al, al
0x21D963  ret
```

The two 32-bit jump destinations stored at `0x21D964` are `0x21D95E` and `0x21D961`, respectively. The selector bytes at `0x21D96C..0x21D9F5` are **138 entries of only 0 or 1**, counted from owner-provided bytes: 93 return `true`, 45 return `false`; index `0x89` returns false. This is a resource-type classifier / boolean policy (exact resource semantics not proven), not file reading or decoding. The byte table after `ret` is DATA, not x64 instructions.

## VERIFIED: wrapper behavior

`0x21CC08` calls `0x21BB98` (path/name selector). `0x21CC2A` calls the boolean classifier, branches on `AL` at `0x21CC34..0x21CC36`. The true branch assembles a candidate path (`0x17464`/`0x27350`) and calls via import slot `0xB329F8` at `0x21CC90`: **`SHLWAPI.dll!PathFileExistsA` (confirmed in the owner's V6 read-only run on 2026-11-22)**. V5's earlier `DINPUT8.dll` attribution was incorrect: its import-name parser did not enforce each descriptor's zero-terminated lookup thunk boundary. V6's corrected descriptor traversal resolved import slot `0xB329F8` to `SHLWAPI.dll!PathFileExistsA`. If path is absent, fallback at `0x217244`; false branch at `0x21CCF2` calls `0x216FAC`. Wrapper returns a string-like path object in `RAX`. The wrapper's surrounding path construction and existence/fallback branches indicate **resource path resolution**, not a demonstrated `meritsystem.enc` loader. The V6 validated import identity strengthens the path-existence interpretation; it still does not demonstrate an ENC decoder.

**V6 verified** import slot `0xB32C28` as `USER32.dll!MessageBoxA`; V5's prior `DINPUT8.dll` label for this slot was also an artifact of its unbounded descriptor heuristic.

## VERIFIED callers

- `0x21CDC6`, in `.pdata` `0x21CDA4..0x21CE36`, calls the path resolver, then invokes `0x2178E0` using the returned path pointer and a 16-byte-stride slot indexed by resource ID. This may be resource index insertion/registration; actual I/O not established.
- `0x6828E6`, in `.pdata` `0x6828A0..0x682DB5`, passes hardcoded `R8D=0x89` to the path resolver, then passes the returned pointer into `0x273C8`. Since the classifier returns false at 0x89, this call follows the false/fallback path.
- The `0x21CE38` function loops `0x21CDA4` over indices `0..0x84` (133 slots) from observed instructions at `0x21CE6E..0x21CE80`.

The V5 scanner reported 3 raw `E8/E9` target candidates; all three are verified as instruction-aligned within the supplied snippets and matching `.pdata` functions. We have NOT shown which named resource ID maps to which actual filename, or which code decodes ENC bytes.

## Next: V6 bounded read-only resource call-chain audit

Inspect the path selector `0x21BB98`, index dispatcher `0x21CDA4`, initialization loop `0x21CE38`, and immediate helper functions `0x2178E0`, `0x273C8`, `0x216FAC`, `0x217244`, `0x21B720`, plus caller at `0x6828A0`. Require the same binary hashes; include only limited code bytes and known boundaries, rather than guessing which function reads Merit. Don't mutate client/SQL/VM; do not transplant EP45 ENC. Diamond game feature/packet/persistence remains unproven.
