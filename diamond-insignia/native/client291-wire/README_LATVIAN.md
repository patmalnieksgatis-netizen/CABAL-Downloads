# CABAL v291 Diamond Insignia — precīzā klienta 0x09F3 protokola revīzija

Datums: 2026-11-22. **STATUSS: KLIENTA BINĀRĀ IDENTITĀTE APSTIPRINĀTA; REĀLAS SPĒLES LABOJUMS VĒL NAV GATAVS.** Nav atļauts šo moduļu uztvert par Live WorldSvr patch, Diamond rank-up handleri vai gatavu klienta jauninājumu.

## Pārbaudītie oriģinālie faili

- Lietotāja aktuālais v291 x64 `Bin\\x64\\CabalMain.exe`: SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9` (15 089 000 B).
- Lietotāja aktuālais `Data\\meritsystem.enc`: SHA256 `3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a` (41 368 B). **Nav atkodēts**: augsta entropija, nav droši izsecināms šifrējums vai plaintext.
- Iepriekš arhivētais oriģinālais `WorldSvr` SHA256 `caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3`.

## Klienta C2S 0x09F3 — tagad pierādīts, nevis minēts

`CabalMain.exe` PE RVA `0x6FF14C–0x6FF1B2` (`.pdata` sākuma/beigu robežas):

- `0x6FF157`: `mov eax,0x9F3`.
- `0x6FF161`: `mov DWORD PTR [rsp+0x20],0x12B7E2`. Tātad galvene `E2 B7 12 00` un **precīzs 18 baitu sūtīšanas buferis**.
- `0x6FF17C`: saglabā pirmo DWORD pie paketes +`0x0A`.
- `0x6FF197`: saglabā otro DWORD pie +`0x0E`.
- Pirmā vērtība iegūta no singletons `+0x118` ar getteri `RVA 0x244D24`, otrā — `+0x11C` ar getteri `0x244D2C`.
- `0x6FF19B`: faktisks nosūtīšanas izsaukums `0x2B7A40`; galvenes `DWORD` pie `+4` sākotnēji nulles.

**Lauku spēles nozīme vēl nav pierādīta**: nevar tos pasludināt par Diamond mastery ID un līmeni. Nav pierādīts, ka šis izsaukums ir Diamond rank-up pirkums. Statiskais kods rāda esošu Merit komandu.

## Klienta S2C 0x09F3 — svarīga savietojamības robeža

`0x6EFED7` reģistrē komandu `0x09F3`, tai piesaistītais S2C apstrādātājs ir RVA `0x6F84FC`.

- `0x6F851C`: salīdzina atbildes byte `+6` ar `1`; citi statusi iet pa kļūdas atzaru.
- **Sekmīgas atbildes atzarā** noteiktos stāvokļos `0x6F8585` un `0x6F85B9` lasa 32 bitus, sākot no atbildes `+7`. Tātad šim atzaram vajag **vismaz 11 buferī esošus baitus**.
- Oriģinālais arhivētais `WorldSvr` pie `0xA3B544–0xA3B569` izveido 7 baitu `E2 B7 07 00 F3 09 01` atbildi, bet pie `0xA3B5CA–0xA3B5F3` — 7 baitu `E2 B7 07 00 F3 09 00`.
- Tās ir **konkrētas plūsmas**, nevis pierādījums, ka visi šī opcode servera S2C gadījumi ir 7 baiti. Nav pierādīts, ka baitu trūkums pašlaik izraisa spēles kļūmi — atkarīgs no atzara, klienta bufera un tā, kāds pieprasījums no spēles reāli tiek sūtīts.

### 2026-11-23: konkrētie S2C atzari pārbaudīti pret īsto klienta EXE

Neatkarīgi pārbaudīts SHA-piesietais `CabalMain.exe`, tā `.pdata`
funkcijas robežas `0x6F84FC..0x6F86AA`, trīs izsaukumi uz
`0x24375C` un abi `[response+7]` DWORD nolasīšanas atzari:

- Ja **pirmā** `0x24375C` meklējuma rezultāts ir `0`,
  klienta `0x6F8585` nolasa `+7` DWORD un izsauc `0x37FA34`,
  kas to ieraksta klienta stāvoklī pie `+0xAB6C`.
- Ja pirmais rezultāts nav `0`, klients meklē **otrreiz**. Rezultāts
  `1` ved uz `0x6F85B9` DWORD lasījumu. Pretējā gadījumā notiek
  **trešais** meklējums, un rezultāts `2` ved uz to pašu lasījumu.
  Lasītā vērtība nonāk `r9d`, pēc tam funkcijā `0x37F9D8`,
  kas to glabā vienā no klienta datu struktūras ierakstiem pie `+0x14`.
- Ja šie atzari nenostrādā, **šis konkrētais apstrādātājs** neprasa
  papildu DWORD. Tādēļ nevar apgalvot, ka oriģinālā 7B success
  atbilde visos gadījumos ir saīsināta/nepareiza.
- Trīs izsaukumi tiek veikti atsevišķi: nepamatoti pieņemt, ka
  starp tiem klienta stāvoklis nevar mainīties.

Pārbaudes kods: `evidence/verify_09f3_response_branch.py` un
`tests/test_client291_s2c_branches.cpp`. 
`CheckServerResponseForClient291` tagad 7B success bez zināma
klienta atzara atgriež `ResponseRouteUnobserved`, nevis nepamatoti
apgalvo universālu truncation. Papildfunkcija
`CheckServerResponseForObservedClientRoute` palīdz **tikai offline
diagnostikā** atšķirt stāvokļus, kuros trūkst 4 baitu, no stāvokļiem,
kuros minētais DWORD netiek lasīts. **Neviens no šiem statusiem nav
Diamond transakcijas sekmīguma apliecinājums.**

Laika ziņā svarīgi: līdz šim joprojām nav zināma šo divu klienta
saglabāšanas lauku spēles nozīme, kā arī nav pierādīts, ka `0x09F3`
ir Diamond rank-up vai konkrētais Diamond Mastery pirkums.

**Nedrīkst vienkārši pielikt četras nulles un sūtīt 11 baitu success**: vērtības semantika nav zināma, un tās lieto dažādas klienta sistēmas. Nelietot šo kā gatavu patch.

## Diamond saistītā konfigurācija

Klienta faktiskajā izpildāmajā failā ir virkne `dia_meritscore_fomula` (oriģinālā pareizrakstība ar `fomula`). Tā tiek izmantota RVA `0x255F70–0x25646B` konfigurācijas parserī; references instrukcija ir `0x25621C`. Tas apliecina Diamond saistītus Merit konfigurācijas **atslēgvārdus**, nevis automātiski pierāda pilnas Diamond Insignia spēles sistēmas saderību. Vajag vēl dekodēt `meritsystem.enc` un salīdzināt servera datu formātus.

## Komplektā

- `src/Client291MeritWire.h/.cpp` — klienta C2S 18B bufera offline builder/parser un drošības vērtējums 0x09F3 atbildēm; NEDARBOJAS kā sūtītājs vai WorldSvr hooks.
- `tests/test_client291_wire.cpp` — formāta, garuma un konservatīvas 7B atbildes pārbaudes; `test_client291_s2c_branches.cpp` pārbauda visus novēroto klienta lookup-atbilžu atzarus.
- `evidence/verify_exact_client_world.py` — read-only pārbaude **pret trim īstajiem** SHA-piesietajiem binārajiem failiem; pārbauda konkrētos opcode, statusa un +7 DWORD lasīšanas instrukciju baitus un `.pdata` funkciju robežas.
- `evidence/VERIFIED_EVIDENCE.json` — šajā izpildījumā iegūtais pierādījumu apkopojums.
- `run-tests.sh` — C++17 testi + ASan/UBSan; tiek veikti tikai lokāli.

## Palaide izolētā analizēšanas vidē

```bash
./run-tests.sh
python3 evidence/verify_exact_client_world.py \
  --client /safe/path/CabalMain.exe \
  --merit /safe/path/meritsystem.enc \
  --world /safe/path/WorldSvr \
  --json evidence/VERIFIED_EVIDENCE.json
```

Nav klienta izmaiņu, nav process-memory atvēršanas, SQL vai VM savienojumu, nav `LD_PRELOAD` un WorldSvr restartu. **Pašlaik darbināmais serveris ir jāsaglabā neskarts.**

## Atlikušie integrācijas darbi

1. Noskaidrot `0x09F3` success `+7` DWORD nozīmi, izsekojot `0x6F84FC` sauktās spēles funkcijas un servera pilno 0x09F3 atbildes plūsmu. Vajadzīga īstā spēles datu forma, nevis divu DWORD nosaukumu minēšana.
2. Pierādīt, kuri v291 UI Diamond rank-up/Mastery klikšķi izsauc attiecīgās C2S komandas. `0x09F3` var būt saistīts ar citas Merit darbības apstrādi, nevis Diamond rank-up.
3. Saskaņot Diamond konfigurācijas datus (`meritsystem.enc`) un servera `MeritSystem.scp`; jāatrod īstais client decryptor/codec.
4. Integrēt autentificētu WorldSvr sesiju ar **reālu** spēles WExp/item 33554961 un MSSQL saglabāšanu vienā droši atkopjamā darījumā.
5. Testēt tikai izolētā VM klonā, jo agrāk mainīti `lib.so`/Supervisor jau izraisīja `exit 78` un servera atjaunošanu.