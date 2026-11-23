# CABAL v291 Diamond — x64 klienta UI un īstā WorldSvr C2S savietojamības pierādījums

**Datums:** 2026-11-22. **Tikai statiska analīze — NAV spēles labojums.**

## Divi neatkarīgi oriģinālie binārie avoti

- v291 klients `CabalMain.exe`, 15 089 000 baiti, SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9` (no īpašnieka `CABAL_v291_Diamond_Client_exact.zip`).
- v291 serveris `WorldSvr_FULLCHAIN_20261108`, 10 596 184 baiti, SHA256 `caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3` (no īpašnieka saglabātās bibliotēkas).

Abu failu SHA256 ir neatkarīgi pārbaudīti. Netika palaista spēle vai VM, mainīti faili, nosūtītas paketes vai rakstīts SQL.

## Kopā pārbaudītā komandu karte

| Lokālais klienta UI ID | Klienta callback | C2S | WorldSvr reģistra slots | Īstā WorldSvr handler adrese | Īstais handler loga nosaukums |
|---|---:|---:|---:|---:|---|
| `0x1A1` | `0x6FF14C` | `0x09F3` | `0x2364858` | `0xA40D90` | `OnCSCMeritMasteryLvUp` |
| `0x1A2` | `0x6FCD44` | `0x09FD` | `0x23648A8` | `0x78E5D0` | `OnCSCDimensionInventoryMoveProcess` |
| `0x1A3` | `0x6FCD00` | `0x09FB` | `0x2364898` | `0x78D270` | `OnCSCDimensionInventoryExpend` |
| `0x1A4` | `0x6FCF44` | `0x09F9` | `0x2364888` | `0x78C130` | `OnCSCDimensionInventoryList` |

## Precīzie WorldSvr x64 reģistrācijas pierādījumi

`g_sUsrProcedureMap` bāze `0x235F8C0`, pointers `8` baiti: `slot = base + opcode*8`. Neatkarīgs paraugs: `0x09F3 -> 0x2364858`.

- Merit: `0x8FBF6D` `cmp qword [rip+...],0` pret slotu `0x2364858`; `0x8FBFA8` ieraksta pointeri `0xA40D90`; `0x8FBFB4` ieraksta teksta pointeri uz `CSC_MERIT_MASTERY_LV_UP: OnCSCMeritMasteryLvUp`.
- Dimension List: `0x8FC1B2` slots `0x2364888`; `0x8FC1ED` handler `0x78C130`; `0x8FC1F9` nosaukums `CSC_DIMENSION_INVENTORY_LIST: OnCSCDimensionInventoryList`.
- Dimension Expend: `0x8FC258` slots `0x2364898`; `0x8FC293` handler `0x78D270`; `0x8FC29F` nosaukums `CSC_DIMENSION_INVENTORY_EXPEND: OnCSCDimensionInventoryExpend`.
- Dimension Move Process: `0x8FC2FE` slots `0x23648A8`; `0x8FC339` handler `0x78E5D0`; `0x8FC345` nosaukums `CSC_DIMENSION_INVENTORY_MOVE_PROCESS: OnCSCDimensionInventoryMoveProcess`.

Katram pārbaudīts konkrēts ELF RIP-relative slots, handler immediāts un NUL terminēts servera nosaukums. `verify_worldsvr_adjacent_c2s.py` reproducē analīzi no īstā servera faila, `test_worldsvr_adjacent_c2s.py` pārbauda izmainītu slotu/handler/nosaukumu noraidīšanu. Precīzs klienta UI notikumu verifikators `verify_ui_event_binding.py` koriģē agrāko `0x1A2` nobīdes kļūdu.

## Secinājums ieviešanai

Komandas **`0x09F9`, `0x09FB` un `0x09FD` NAV Diamond rank-up**: šajā reālajā WorldSvr tās ir esošās Dimension Inventory apstrādes komandas. Tās nedrīkst piesaistīt jaunam Diamond handlerim. `0x09F3` ir verificēts kā Merit Mastery Level Up, **bet ne Diamond-exclusive**. Pareizais Diamond grade-up UI klikšķis, C2S/S2C semantika un faktiskās spēles WExp/inventāra/MSSQL atomiskā saglabāšana joprojām nav pierādīti.

Iepriekšējais `lib.so` / Sidecar izvietošanas mēģinājums izraisīja WorldSvr `exit 78`; aktīvajā serverī nedrīkst veikt jaunus eksperimentus. Šajā posmā produkcijas WorldSvr, SQL, klientu un Supervisor neviens nav mainījis.
