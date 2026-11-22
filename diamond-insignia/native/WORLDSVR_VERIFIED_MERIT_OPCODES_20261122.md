# Exact running WorldSvr registry evidence (2026-11-22)

## Provenance

Offline analysis of the user-provided `WorldSvr_FULLCHAIN_20261108` (ELF x86_64, ET_EXEC, 10,596,184 bytes, stripped), SHA256 **`caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3`**. The same hash was independently captured from the owner's running CABAL WorldSvr in earlier project logs. No server memory reads, container changes or packet injections occurred in this analysis.

The archived **WorldSvrRealm** extension (`CABAL_EXTRA_SOURCE.tar.gz`) provides a reference to `g_sUsrProcedureMap` at **`0x235F8C0`** in this ELF, with a pointer-size stride of 8 bytes per C2S main command. This base is independently corroborated in the actual ELF: the `CSC_WARPCOMMAND` handler's registry slot is **`0x2360060`**, i.e. `(0x2360060-0x235F8C0)/8 = 244`, matching the archived command enumeration `CSC_WARPCOMMAND=244`.

## Verified legacy Merit opcode and handler registration pairs

The current ELF's registration routine stores function pointers and their adjacent log-name strings. From the exact instruction addresses, table slot and checked 8-byte stride:

| C2S main command | Opcode decimal / hex | User-procedure slot | Registered handler pointer |
|---|---:|---|---|
| `CSC_MERIT_MASTERY_LV_UP` | **2547 / `0x09F3`** | `0x2364858` | `0xA40D90` |
| `CSC_MERIT_PLATINUM_BADGE_GRADE_UP` | **2832 / `0x0B10`** | `0x2365140` | `0xA40F00` |
| `CSC_MERIT_PLATINUM_MASTERY_SLOT_OPEN` | 2833 / `0x0B11` | `0x2365148` | `0xA41870` |
| `CSC_MERIT_PLATINUM_MASTERY_SLOT_OPEN_CANCEL` | 2835 / `0x0B13` | `0x2365158` | `0xA42A80` |
| `CSC_MERIT_PLATINUM_PAGE_CHANGE` | 2838 / `0x0B16` | `0x2365170` | `0xA42D70` |
| `CSC_MERIT_PLATIUNM_SPECIAL_MASTERY` (source spelling) | 2839 / `0x0B17` | `0x2365178` | `0xA43600` |
| `CSC_MERIT_PLATINUM_SPECIAL_MASTERY_SEAL` | 2840 / `0x0B18` | `0x2365180` | `0xA44B20` |

This is a **breakthrough in real game packet registration**, not merely a symbol-string match. Specific corroboration: at `0xA40FF2`, the actual Platinum grade-up handler writes `ESI=0xB10` (its command code) into a reply header, directly confirming `0x0B10`. The same handler checks packet size as `0xC + 2*count` using the 16-bit word at packet offset `+0xA` and total length at `+2` (`0xA40FD2..0xA40FE4`). This size check concerns *existing Platinum*, not an inferred Diamond packet.

**Important:** None of the above is a confirmed Diamond-exclusive opcode. Existing Platinum grade-up `0x0B10` must not be overwritten or hooked under the assumption that it is a Diamond rank-up request. The exact new client request/response ABI for grade 2 remains unverified; attaching an always-on intercept to this command would risk Platinum.

## What can be connected today

`diamond_world_bridge.h/.cpp` and `diamond_mssql_shadow_bridge.h/.cpp` are real compiled entrypoints to native C++ Diamond rules and to SQL Server ODBC **shadow test transactions**. The shadow adapter explicitly checks `DB_NAME()='Server01_DiamondLab'` and performs serializable lock/revision updates in shadow wallet/mastery tables. The staging scripts `sql-lab/08_install_odbc_shadow_wallet_TEST_CLONE_ONLY.sql` and `sql-lab/09_seed_odbc_shadow_user_TEST_CLONE_ONLY.sql` do not modify live Platinum or CABAL inventory.

**Still required to make actual game playable:** a *verified Diamond-specific* incoming action/response packet on this client, the correct host-side user-context and inventory/WExp commit ABI, and MSSQL writes to real authorized inventory/merit storage under one transaction. The supplied archived extension has a generic `CSC_CUSTOM_PACKET=421` route, but its compatibility with this exact binary and with original client Merit actions has not been proven. Do not guess a Diamond opcode from the gap in the Platinum command table.

No live DB/WorldSvr/client changes performed.
