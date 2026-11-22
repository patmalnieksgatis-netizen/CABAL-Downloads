# CABAL v291 Diamond Insignia — verificēta servera Merit 0x09F3 protokola daļa

**Statuss:** precīza arhivētā / aktīvajam serverim atbilstošā WorldSvr `caec7772...` binārā faila analīze, C++ kods un testu komplekts. **NAV** uzstādīts serverī, **NAV** Diamond pirkuma pilnīga implementācija. Šis nav Mandarat.

## Kas pierādīts ar oriģinālā WorldSvr x64 disasemblēšanu

Fiksētais WorldSvr SHA256: `caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3`, iegūts no lietotāja agrāk dotā CABAL arhīva. Tas atbilst agrāk salīdzinātajam aktīvajam WorldSvr failam. `evidence/verify_worldsvr_merit.py` atsakās strādāt ar citu bināro versiju.

1. **0x09F3 (`a40d90`)**: pie `0xa40dc0` nolasa `DWORD [packet+0x0A]`, pie `0xa40dca` nolasa `DWORD [packet+0x0E]`; tātad 10-baitu CABAL C2S header un vismaz astoņi payload baiti. Šī disasemblēšana **nepierāda**, ko abi parametri nozīmē, vai Diamond rank-up izmanto tos pašus laukus, vai paketes precīzais garums vienmēr ir 18.
2. **Viena 0x09F3 atbildes plūsma (`a3b2d0`)**: pie `0xa3b544`, `0xa3b549`, `0xa3b551`, `0xa3b562` redzams S2C header `E2 B7 07 00 F3 09 01` (success). Pie `0xa3b5ca`, `0xa3b5dd`, `0xa3b5e2`, `0xa3b5ec` ir tā pati pakete ar statusu `00` (failure). Šī ir esošā Merit atbilde, **nevis verificēta v291 Diamond atbilde**.
3. **Cits Merit atjauninājums**: pirms šīs atbildes pie `0xa3b502` tiek sūtīta komanda `0x1030` ar astoņu argumentu kopu. Paketes baitu struktūra nav vēl noteikta, tādēļ šo datu atjauninājumu **nedrīkst izdomāt**.
4. **0x0B10 (`a40f00`)** ir atsevišķa esošā Platinum komanda. Neaizvietot vai neklausīt to kā Diamond ekskluzīvu pirkumu.

## Ko pievienojām

- `src/DiamondMeritWire.h/.cpp`: stingrs 18 baitu legacy pieprasījuma parseris (sākotnējā hipotēze; nelietot pret dzīvu klientu, kamēr tas nav validēts) un verificētās vienbaita statusa atbildes kodētājs.
- Abus `DWORD` atdod neitrāli kā `value0`/`value1`, **nevis kā nepamatoti nosauktu mastery ID/rank**.
- `evidence/verify_worldsvr_merit.py`: lasīšanas-only disasemblēšanas pierādījums ar SHA pinning, `objdump` un precīzām instrukciju adresēm.
- `tests/test_merit_wire.cpp`, `run-tests.sh`: parastā un AddressSanitizer/UBSan kompilācija, malformed, wrong-size, wrong-magic, wrong-opcode gadījumi.

## Darbība un drošība

**`0x09F3` statusa `01` nedrīkst sūtīt, kamēr nav droši saglabāts Diamond pirkums.** Esošajā jaunajā kodā nav klienta pakešu sūtīšanas vai konta datu rakstīšanas. Mūsu iepriekšējie moduli (`DiamondCommitGate`, `DiamondWorldSaveBarrier`, `DiamondWorldSessionBridge`) ir izolēti un nav pieslēgti īstajai WorldSvr sesiju reģistrācijai vai GameData/DBAgent ierakstiem.

**Būtiskākais trūkums:** vietējā arhīvā esošais `CabalMain.exe` SHA256 ir `b426a75abcfdd657f3d648a287fc3fbca7b3e58bddf1894a627899457e9c793a`, bet lietotāja aktīvā **v291 x64** klienta iepriekšējā V9 statiskajā atskaitē ir `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`. Tas NAV tas pats fails. Tādēļ nevar pierādīt v291 klienta Diamond C2S/S2C formātus, balstoties tikai uz arhīvu un agrākajiem read-only V9 skeneriem (kuros `diamond_opcode_proven=false`).

**Līdz uzstādāmam labojumam** vēl vajag precīzu v291 `CabalMain.exe`, Diamond vadības paketes, `0x1030` vai cita S2C atjauninājuma formātu un īstu, transakciju drošu servera inventāra/WExp/MSSQL sasaisti. **Neaizvietot oriģinālo `lib.so`, nemainīt Supervisor/LD_PRELOAD un nerestartēt WorldSvr.** Iepriekšējās šādas izmaiņas jau izraisīja `exit 78` un nepieciešamību atjaunot palaišanas konfigurāciju.

## Testēšana

```bash
./run-tests.sh
python3 evidence/verify_worldsvr_merit.py /path/to/exact/hash-pinned/WorldSvr
```

Verifikatora skripts tikai nolasa failu. Spēlē nekas nav mainīts.