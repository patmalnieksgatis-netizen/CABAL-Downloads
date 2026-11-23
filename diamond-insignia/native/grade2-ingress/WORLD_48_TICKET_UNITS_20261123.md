# CABAL v291 — actual WorldSvr ticket quantity reader and runtime catalog blocker (2026-11-23)

## Substantive finding: real server stack codec found

This is **direct analysis of the exact owner's original WorldSvr ELF**,
10,596,184 bytes, SHA256
`caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3`.
It does NOT establish that the item type metadata for `33554961`
has yet been captured, or that game resources were debited.

The existing Platinum grade-up handler `0xA40F00`:

1. Reads the selected slot index from C2S `+0xC+2*i`.
2. Checks slot index `<=521`.
3. Resolves a **48-byte stride** inventory record via helper `0x587E30`.
4. Checks the record is in use and its `DWORD [slot+8]` item kind
   after mask `0x06000FFF` matches the server-selected target item.
5. Passes **`slot+8`** to WorldSvr function **`0xAE0E90`**
   at handler call `0xA413AF`, and adds the returned number into
   its selected total at `0xA413BB`.

## Exact count logic proved by real x64 instructions

Original `0xAE0E90` reads `QWORD [itemPointer+0]` for raw item kind,
`QWORD [itemPointer+0x10]` for the raw item option; since the
original caller passes `slot+8`, option starts at **`slot+0x18`**.

Runtime catalog record selection uses the item kind:
`itemIndex = kind & 0xFFF` and
`catalogVariant = (kind >> 25) & 3`.
It references a per-item metadata table based at `0x12E8E00`,
with stride/index arithmetic:
`metaVA = 0x12E8E00 + (variant*25 << 15) + (itemIndex*25*8)`.

If signed metadata field `+0x3C <=1`, function returns **one unit**.
Otherwise metadata field `+0x38` selects the following item-option
quantity extraction:

| Metadata kind +0x38 | Unit count from 32-bit item option at slot+0x18 |
| --- | --- |
| `0x43`, `0x46` | `option >> 22` (upper 10 bits) |
| `0xAF`, `0xB8` | `option & 0xFFFF` (lower 16 bits) |
| `0x10`, `0x1B`, `0x66` | `option & 0x7F` (lower 7 bits) |
| Other | 1 |

This is the **server's actual conditional unit-count reader**
for the selected Platinum inventory items, not a guessed generic
CABAL stacking convention.

## The unresolved ticket type

The owner's ticket is `33554961 = 0x02000211`, so:
- `itemIndex = 529`;
- `catalogVariant = 1`;
- resulting **runtime metadata virtual address = `0x13CAB48`**.

An independent ELF PT_LOAD check proves `0x13CAB48`
is in the **memory-only, not file-backed** part of the server
segment. Accordingly neither metadata field `+0x38` nor
`+0x3C` can be recovered from this exact ELF alone.
The actual data must come from the running server's
**verified runtime item catalog** (read-only snapshot on isolated
VM clone) or the authentic item catalog resource matched to
this exact server. Do not invent a class flag or treat any one
of the three bit layouts as the `33554961` codec.

The 514 MB owner `CABAL_VPS_FULL.tar.gz` archive is present
in the model's working runtime, but its index could not be
reliably inspected in this turn due a container-processing error.
No catalog assertion is based on it.

## Implemented original-code-based C++ component

`DiamondWorld48TicketUnits.h/.cpp` now provides:
- read-only 48-byte source slot parser with used-item and masked-item
  `33554961` checks,
- exact catalog key validation (`529,1`),
- all three actual type-specific option quantity modes,
- fail-closed zero quantity, wrong item, short/missing data, and
  **unverified metadata** rejection.
- No WorldSvr memory writes, item debit, SQL updates or packet transmission.

Its `test_world_48_ticket_units.cpp` covers every count
branch with **synthetic** ticket records, including 100-unit
positive tests, missing metadata and duplicate/invalid record
boundaries. `verify_world_48_ticket_helper.py` contains exact
ELF SHA-pinned machine-code anchors, the original count-helper
CALL and the runtime-only metadata proof; its static mock ELF
tests run in CI.

The actual original ELF was independently checked offline
against **21** instruction anchors in the native disassembly,
and its computed ticket metadata virtual address was confirmed
not to be file-backed. The repository verifier pins the more
complete anchor collection for reproducibility.

**Note:** the new reader is only for original 48-byte WorldSvr
slot snapshots; the independently studied persisted 30-byte
DB inventory rows are a different representation.
Do NOT conflate them or reuse the raw offsets for persistent
DB serialization before proving the game save mapping.

## Remaining requirements for first playable Diamond rank-up

1. Capture authentic `33554961` item metadata `+0x38` and
   `+0x3C` from **offline clone** item catalog, not from client.
2. Establish actual 0BDA selected-slot semantics and authoritative
   owner-locked 48-byte array; reject duplicate/replayed slot picks.
3. Implement durable GameData + WExp + grade-2 + receipt in actual
   DB/DBAgent with rollback and cmd46/47 save reconciliation.
4. Verify host `PROCEDUREMAP` binary/allocator ABI, register
   `0x0BDA` only in isolated VM clone, and preserve `0x0B10/0x0B13`.
5. Only after independent save/response ABI verification, transmit
   a real 0BDA successful reply. Clone mock candidate is not certifiable.

**Status:** actual server count algorithm recovered; specific ticket
classification and real persistence still unknown. No active
WorldSvr/SQL/client/VM changes performed.
