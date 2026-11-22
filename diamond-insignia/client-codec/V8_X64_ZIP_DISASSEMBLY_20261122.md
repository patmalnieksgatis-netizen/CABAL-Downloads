# CABAL v291 x64 Merit — V8 independent static disassembly (2026-11-22)

## Archive and integrity

Owner-uploaded `CABAL_DIAMOND_MERIT_X64_V8_20261122-094521.zip`, SHA256 `9be302254f3b4c3c021cbf82a43842353776f57eb0f01bcee9edd3da817f3b26`; contains `MERIT_X64_V8_REPORT.json` (schema 8, mode `READ_ONLY_X64_MERIT_MAPPED_BUFFER_WORKER`, 8887 bytes) and `README.txt`. Report pins `CabalMain.exe` SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`, `meritsystem.enc` SHA256 `3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a`. Each function's exported code bytes exactly match its PDATA-derived range: 105 bytes at `0x2B8B08..0x2B8B71`, 40 bytes at `0x2B7F84..0x2B7FAC`, and `code_complete=true`. Disassembled locally using GNU objdump x86-64 with correct RVA bases. No original client binaries in this archive.

## Main finding: 0x2B8B08 is a buffer-processing loop, not a demonstrated primitive decoder

```asm
0x2B8B12  and qword ptr [rcx+0x28],0
0x2B8B1A  and dword ptr [rcx+0x48],0
0x2B8B1E  and dword ptr [rcx+0x1C],0
0x2B8B22  and dword ptr [rcx+0x18],0
0x2B8B28  and dword ptr [rbx+0x20],0
0x2B8B2C  lea rdx,[rsp+0x30]
0x2B8B31  mov rcx,rbx
0x2B8B36  call 0x2B8004
0x2B8B3B  test eax,eax
0x2B8B3D  jne 0x2B8B66                ; nonzero status exit
0x2B8B3F  mov eax,[rbx+0x20]
0x2B8B42  cmp eax,edi
0x2B8B44  cmovbe eax,edi
0x2B8B47  cmp dword ptr [rsp+0x30],0
0x2B8B4C  je 0x2B8B28                 ; loop/retry
0x2B8B4E  mov r8d,[rbx+0x48]         ; copy size
0x2B8B52  mov rdx,[rbx+0x40]         ; source pointer
0x2B8B56  mov rcx,[rbx]              ; destination pointer
0x2B8B59  call 0xA37890              ; copy-like call, exact semantics unknown
0x2B8B5E  mov eax,[rbx+0x48]
0x2B8B61  add qword ptr [rbx],rax   ; advance destination by copied length
0x2B8B64  xor eax,eax
0x2B8B70  ret
```

`0x2B8004` is the next required function body to analyze. Although the loop is compatible with block-oriented decompression or transformation, **no compression format, encryption, decoder key, or completed Merit codec is yet demonstrated**. The `cmovbe` and return status flow can be described only after the helper's exact behavior is inspected.

## Secondary finding: 0x2B7F84 releases a linked buffer chain

```asm
0x2B7F8A test rcx,rcx
0x2B7F8F mov rbx,[rcx-8]        ; previous/next linkage
0x2B7F93 sub rcx,0x10
0x2B7F97 call 0xA6BE2C        ; deallocation-like
0x2B7F9C mov rcx,rbx
0x2B7F9F test rbx,rbx
0x2B7FA2 jne 0x2B7F8F
0x2B7FA4 xor eax,eax
0x2B7FAB ret
```

It loops over linked allocations, freeing each node. Actual allocator ABI and layout are not yet proven, so the `0xA6BE2C` label is provisional.

## Confirmed client imports (V8 report, V7 cross-check)

- `KERNEL32.dll!CreateFileA` `0xB32558`
- `KERNEL32.dll!SetFilePointer` `0xB325D8`
- `KERNEL32.dll!ReadFile` `0xB32570`
- `KERNEL32.dll!CreateFileMappingA` `0xB325F8`
- `KERNEL32.dll!MapViewOfFile` `0xB325E8`
- `KERNEL32.dll!UnmapViewOfFile` `0xB325F0`
- `KERNEL32.dll!CloseHandle` `0xB32420`
- `SHLWAPI.dll!PathFileExistsA` `0xB329F8`
- `USER32.dll!MessageBoxA` `0xB32C28`

## Next, V9 read-only gate

Collect PDATA-bounded code for `0x2B8004`, `0xA37890`, and `0xA6BE2C`; verify their anchored direct-call instructions before capturing, and use bounded no-PDATA fallback if needed. Continue following actual callee logic before assigning a cryptographic/compression algorithm. Resource IDs `52 = meritsystem.enc` and `53 = meritsystem_msg.enc` remain confirmed by V6/V7 branch/data matching. **Do not modify active client/server/SQL or transplant EP45 ENC yet.**
