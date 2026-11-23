# Diamond v291 — pirmais pareizi izolētais 0x0BDA grade-up integrācijas ceļš

2026-11-23. **Statuss: precīzais klienta protokola kandidāts un kompilēts
klona testa adapteris. Spēlē NAV instalēts un NAV darbspējīgs.**

## Kļūdainā 0x0BDD hipotēze ir izslēgta

Oriģinālā klienta S2C `0x6DBDA0` ir **Platinum 0x0B13
Mastery Slot Open Cancel**, nevis `0x0B10` Badge Grade Up.
Šī iemesla dēļ `0x0BDD` kā rank-up kandidāts **tika atsaukts**;
`DiamondGrade2Ingress.cpp` tagad vienmēr atļauj tikai lasīšanu,
neveic darījumu arī ar veco `DIAMOND_ENABLE_GRADE2_CLONE_TRIAL` makro.

## Spēcīgākais jaunais grade-up kandidāts: 0x0BDA

Pareizā Platinum Badge Grade Up `0x0B10` klients ir:
- UI event `0x216` / sender `0x6E06F8`;
- S2C handler `0x6DB688`, kas apstrādā Merit grupu **1**.

Jaunais `0x0BDA` klients ir:
- UI event `0x21C` / sender `0x6DFD08`;
- S2C handler `0x6DA920`, kas apstrādā Merit grupu **2**.

Abi izmanto vienu un to pašu `0x244D3C` Merit atlasītāju, `+0xAB88`
izvēli, `0x2B7A40` sūtītāju un piecas galvenās S2C atjaunošanas
funkcijas. To precīzo baitu atbilstību verificē
`verify_gradeup_0bda.py` ar oriģinālā EXE SHA256
`52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`.
**Tā ir spēcīga statiska analoģija, nevis spēles Diamond pirkuma
darījuma pierādījums.**

## Uzrakstītais C++ integrācijas prototips

`DiamondGradeUp0BDA.h/.cpp`:

1. Atpazīst tikai `0x0BDA` klasisko 10 B C2S galveni un
   `u16 count + u16[count]` sarakstu; noraida nekorektu garumu,
   nulles/nesamērīgu skaitu un izmainītas galvenes.
2. Neskar `0x0B10` Platinum, `0x0B13` atcelšanu,
   `0x0BDD` atcelšanas kandidātu vai citas paketes.
3. Pieprasa atsevišķu **servera apliecinājumu** par autentificētu
   sesiju, verified grade-2 katalogu, tieši konkrēto UI semantiku,
   visiem izvēlētajiem ierakstiem un reālu GameData/WExp backendu.
   Paketes dati nekad nekļūst par uzticamu kontu, revīziju,
   maksājumu vai Mastery ID.
4. Parastajā būvē vienmēr ir **Disabled**.
   Tikai atsevišķā būvē ar `DIAMOND_ENABLE_0BDA_CLONE_TRIAL` un visiem
   apliecinājumiem nodod pieprasījumu esošajam
   `diamond::DiamondCommandService`/autoritatīvajam atomiskajam
   backendam. Pašlaik tikai ar **sintētisku testa backendu**.
5. Pat pie veiksmīgas testa backend izpildes atgriež
   `CloneBackendAppliedPendingSaveProof` un
   `maySendS2cSuccess=false`; **nevienu S2C atbildi nesūta**.

Testi pārbauda nulli blakņu bez apliecinājuma, klienta ierakstu
viltošanu, nepareizu garumu, Platinum neskartumu, 100 biļešu
un 30 000 WExp norakstīšanu tikai sintētiskajā modelī, neveiksmīgu
saglabāšanu bez stāvokļa maiņas un atkārtota pieprasījuma
noraidīšanu. CI kompilē gan parasto, gan klona testa būvi.

## Kas obligāti trūkst spēlē instalējamai versijai

- Apstiprināta `0x0BDA` UI pogas darbība, precīza `u16` saraksta
  nozīme un klienta S2C atbildes formāts izolētā sesijā.
- Droša `0x0BDA` C2S handlera reģistrācija īstajā
  `WorldSvr_FULLCHAIN_20261108` bez vecā sidecar/`exit 78` riska;
  autentificēts WorldSvr lietotāja un varoņa īpašnieks.
- Reāla item `33554961` stack-count atkodēšana, WExp debets,
  atjaunota GameData/SQL Diamond progresija, revīzijas un kvīts,
  noturīga norakstīšana plus `cmd46/47` saglabāšanas barjera.
- Patstāvīgs reload/re-login un atkārtota pieprasījuma tests
  atsevišķā VM klonā, saglabājot strādājošo Platinum/Costume/EventPass.

**Gatavais 116 812 B staged Diamond SCP ar 316 definīcijām jau ir
pārbaudīts un nav jātaisa no jauna**, taču tas nav instalēts.
Nevienam aktīvam VM, SQL, klienta vai WorldSvr failam neko nemainīja.
