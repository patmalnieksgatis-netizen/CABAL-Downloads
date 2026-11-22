# CABAL v291 x64 Merit — independently verified V7 bytes (2026-11-22)

## Provenance
The two conversation V7 uploads of CABAL_DIAMOND_MERIT_X64_V7_20261122-093656.zip are byte-for-byte identical (SHA256 d3e2223506b482f9a6883a21c74b15147ddefd4914cdd2e454e3a9b1767f4220). Report schema 7 and pinned source checks match the V5/V6 source executable (SHA256 52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9) and Merit ENC (SHA256 3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a). All eleven PDATA-backed function bodies were supplied in full, with exact length checks. The single no-PDATA entry at 0x21A718 was exported only as a 2048-byte diagnostic window. Source code bytes were independently disassembled with GNU objdump x86-64, using original RVAs as base. NO game, server, SQL, or VM modifications.

## Finding 1: precise Merit resource ID

V7's raw filename pool at 0xB5EB00 contains ASCII meritsystem.enc at **0xB5EE68** and meritsystem_msg.enc at **0xB5EE78**. Cross-check with the V6 export of filename selector 0x21BB98 shows an unambiguous ID-to-name branch:

    0x21C21E cmp r8d, 0x34
    0x21C222 jg  0x21C4B1
    0x21C228 je  0x21C494
    ...
    0x21C4A5 lea rdx,[rip+0x9429bc]  ; 0xB5EE68 = meritsystem.enc
    0x21C4AC jmp 0x21C20A             ; 15-byte assignment

**Resource ID 0x34 (decimal 52) is meritsystem.enc.** It is included in the first startup loading loop at 0x21CE38 (IDs 0 to 132 inclusive), calling the wrapper at 0x21CDA4. V5's separate resource-type classifier entry 52 equals 1 (takes the file-existence check path). This is grounded in actual assembly, not guessed by filename ordering. The adjacent message-file branch is also now cross-checked: 0x21C4C1 subtracts 0x35 from the incoming resource ID and 0x21C4C5 jumps to 0x21C564 on equality; 0x21C564 loads 0xB5EE78. Therefore **resource ID 0x35 (decimal 53) is meritsystem_msg.enc**. V5's resource-type table returns 0 for ID 53 (the resolver's non-existence-check branch), unlike 52.

## Finding 2: 0x2B7FAC is a processing/cleanup wrapper, not the codec

Full PDATA function 0x2B7FAC–0x2B8001:

    0x2B7FB6 cmp qword ptr [rcx+0x40],0
    0x2B7FC0 mov eax,3       ; early return when pointer absent
    0x2B7FC7 call 0x2B8B08   ; next worker to inspect
    0x2B7FCC mov rcx,[rbx+0x30]
    0x2B7FD7 call 0x2B7F84   ; cleanup if nonzero
    0x2B7FDC and qword ptr [rbx+0x30],0
    0x2B7FE1 mov rcx,[rbx+0x28]
    0x2B7FEA call 0x2B7F84   ; cleanup if nonzero
    0x2B7FEF and qword ptr [rbx+0x28],0
    0x2B7FF4 mov eax,edi     ; returns worker status

Thus the real next processing target is **0x2B8B08**; its code bytes are NOT present in V7. Its actual decoding/decompression behavior remains unproven. Do not call 0x2B7FAC a decoder or name an algorithm.

## Finding 3: IMPORTANT correction of original V6 footer/header interpretation

V6's loader 0x2178E0, with the now confirmed V7 kernel32 IAT mappings, does the following:

    0x21793F SetFilePointer(offset 0, FILE_END) 
    0x21794B subtract 4 from returned file length
    0x217957 SetFilePointer(length-4, FILE_BEGIN)
    0x217975 ReadFile(4 bytes into output length variable)
    0x217987 SetFilePointer(offset 4, FILE_BEGIN)
    0x2179A3 CreateFileMappingA
    0x2179BE MapViewOfFile
    0x2179C7 pass mapped pointer + 4
    0x2179D7 allocate buffer using the 4-byte trailer value + 1
    0x217A17 call the 0x2B7FAC processing wrapper

The **4-byte length is from the file TRAILER, not a 4-byte header**. The mapped input starts at offset 4. Exact purpose of prefix and trailer is not independently decoded, and no format conversion should yet be attempted.

## Other bounded contexts

0x21A718 is a tiny 10-byte compare/setne/ret leaf without PDATA, followed by int3 padding then 0x21A724 PDATA function. It is NOT a 2048-byte function. 0x21D9F8 calls 0x9D3E6C and 0x21E358 with status 0/0x12 branches, but its analyst label "codec" is not proof of an ENC decoder. The separate resource ID 0x89 follows the 0x1F5914 object creation path and is not established to be Diamond.

Confirmed imports: KERNEL32.dll CreateFileA (IAT 0xB32558), SetFilePointer (0xB325D8), ReadFile (0xB32570), CreateFileMappingA (0xB325F8), MapViewOfFile (0xB325E8), UnmapViewOfFile (0xB325F0), CloseHandle (0xB32420); SHLWAPI.dll PathFileExistsA (0xB329F8); USER32.dll MessageBoxA (0xB32C28).

## Next

V8 should extract SHA-pinned PDATA-bounded function bytes at 0x2B8B08 and 0x2B7F84 (bounded fallback where necessary). Then independently disassemble the worker before moving to any patch, EP45 ENC transplantation, live SQL, or server work. Actual ENC codec, Diamond packets, and persistence remain unproven.
