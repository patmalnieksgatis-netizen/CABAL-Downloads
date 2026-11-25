# Uploaded WorldSvr source review — 2026-11-25

Archive: CABAL_WorldSvr_SOURCE.tar.gz
SHA-256: 443c3b46e800de6b59e2cb8c87ddf0cb038df6e16738d4ad34ec5f2fb71ff503
Inspected 29 regular files; archive was not installed or executed.

## What is present
- Main.cpp exports Init and initializes Proc, Warp, EventAlert, MacroBM3 and WindowList. This is an extension project, not the original server implementation.
- Proc/Proc.h and Proc.cpp provide extension-local packet and IPC callback registration.
- Game/Structs/GameStructs.h contains 54,130 lines of partial layout declarations; GameStructs.cpp contains lookup wrappers. The existence of a lookup wrapper is not proof of a session lifetime lease.
- PacketManager/PacketManager.h defines PROCESSDATACONTEXT and PROCEDUREMAP; PacketManager.cpp defines table pointers.

## Compatibility blockers
- PacketManager.h declares iLen as WORD, inconsistent with the previously documented v291 V18 64-bit length evidence.
- GameStructs.h declares INVENTORY_SLOTNUM as 266, inconsistent with the previously documented v291 522-slot layout.
- Procedure-map definition uses a different timer storage size from the previously documented native V19 layout.
- Native wrappers use absolute addresses and are not a portable or documented vendor extension SDK.
- No Diamond/Merit or WarExp implementation was located in these source files. PlatinumBuffGrade is a separate field used by MacroBM3; it is not proof of Platinum Merit state.
- No implemented exclusive owner lifetime/save synchronization contract was located. A mutex declaration or character lookup alone is insufficient.

Do not copy these layouts into the active v291 process or replace the original core. This review does not change any deployment gates. The uploaded archive supplies additional reference material, not the missing verified native Diamond implementation. No live server, VM networking, SQL or client changes were made.
