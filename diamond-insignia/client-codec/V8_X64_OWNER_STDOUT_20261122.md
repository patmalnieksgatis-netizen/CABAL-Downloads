# CABAL v291 / EP39 Diamond — V8 owner-run output (2026-11-22)

## Evidence level

Source: PowerShell stdout pasted by the owner from the pinned `Inspect-Cabal291-MeritWorker-V8.ps1` script (commit `cd78966800a7054bdabed4653d0664c8cfcd067b`). This is a console-only record. The generated V8 archive **has not been attached or independently inspected** yet, so no V8 worker semantics, codec, cipher or compression claims may be made from these function ranges alone.

The script reported:

```text
MERIT_X64_V8_WINDOWS_SELF_TEST=PASS
CABAL_DIAMOND_MERIT_X64_V8=READ_ONLY_STATIC
CLIENT_ROOT=F:\CABAL_291_TEST
ARCH=x64;GAME_LAUNCHED=NO;PROCESS_MEMORY=NO;SQL_OR_VM=NO;CLIENT_EDIT=NO
FUNCTION=mapped_buffer_worker;pdata=YES;range=0x2b8b08-0x2b8b71;exported=105
FUNCTION=temporary_buffer_release;pdata=YES;range=0x2b7f84-0x2b7fac;exported=40
IAT_iat_create_file_candidate=0xb32558::KERNEL32.dll!CreateFileA
IAT_iat_set_pointer_candidate=0xb325d8::KERNEL32.dll!SetFilePointer
IAT_iat_read_file_candidate=0xb32570::KERNEL32.dll!ReadFile
IAT_iat_create_mapping_candidate=0xb325f8::KERNEL32.dll!CreateFileMappingA
IAT_iat_map_view_candidate=0xb325e8::KERNEL32.dll!MapViewOfFile
IAT_iat_unmap_view_candidate=0xb325f0::KERNEL32.dll!UnmapViewOfFile
IAT_iat_close_handle_candidate=0xb32420::KERNEL32.dll!CloseHandle
IAT_iat_path_file_exists_confirmed=0xb329f8::SHLWAPI.dll!PathFileExistsA
IAT_iat_message_box_confirmed=0xb32c28::USER32.dll!MessageBoxA
TARGET_CONTEXTS=2
UPLOAD_THIS_ZIP=C:\Users\patma\Downloads\CABAL_DIAMOND_MERIT_X64_V8_20261122-094521.zip
CLIENT_AND_SERVER_UNMODIFIED=YES
```

Two `.pdata`-bounded function bodies were exported (105 and 40 bytes). Note `mapped_buffer_worker` and `temporary_buffer_release` are **analysis labels only**, not symbols from the binary. The 7 KERNEL32, SHLWAPI and USER32 imports agree with earlier V7 findings and the corrected V6 importer. This result confirms successful extraction but **not** what `0x2B8B08` does.

## Current verified chain from prior V5/V6/V7

Resource ID `0x34` (52) resolves to `meritsystem.enc`; ID `0x35` (53) resolves to `meritsystem_msg.enc`. The read-only mapped-file loader `0x2178E0` calls `0x2B7FAC`, which is an 85-byte processing/cleanup wrapper and calls `0x2B8B08`. The file-size/output-length value used by the mapped loader is read from the trailing four bytes of the source file, while mapped input starts at +4. See [V7 verified audit](./V7_X64_ZIP_VERIFIED_20261122.md). Do not assume the worker implements ENC decryption without its actual body.

## Required next gate

Use the **existing** owner's V8 ZIP `CABAL_DIAMOND_MERIT_X64_V8_20261122-094521.zip`; no repeat PowerShell execution is necessary. On receipt, verify schema 8 and SHA pins and independently disassemble the 105-byte worker and 40-byte helper. Trace actual worker calls/branches and pointer/size data flow, then decide whether an additional narrowly scoped static capture is necessary. Do not patch the executable, copy EP45 ENC, or touch SQL/server until the decoder and integration requirements are demonstrated.

No V9 inspector has been created as part of this stdout-only stage.
