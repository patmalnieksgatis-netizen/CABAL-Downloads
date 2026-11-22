# CABAL v291 — Diamond Insignia WorldSvr/DBAgent saglabāšanas barjera

**Datums:** 2026-11-22. **Statuss:** C++17 pirmkods + offline testi PASS; **NAV** pieslēgts aktīvajam WorldSvr/DBAgent, nav MSSQL produkcijas rakstīšanas, nav S2C un nav klientā ieslēgta Diamond iegāde. Šī ir **Diamond Insignia**, nevis Mandarat.

## Konkrēta izmaiņa pēc ODBC adaptera

Agrākais `DiamondCommitGate` un `DiamondLabOdbcBackend` droši apstrādā **tikai sintētisko** `Server01_DiamondLab` transakciju. Īstajā CABAL WorldSvr inventārs tiek rakstīts citā ķēdē: v14 pirmkods dokumentē `IPC_UPDATECHDAT` **cmd46** -> DBAgent -> `IPC_RESULT_UPDATECHDAT` **cmd47**; atbildei ir **18 baiti**, `CharacterIdx` un `PackFlags`, bet **nav unikāla Diamond darījuma ID**.

Ar jaunā `DiamondWorldSaveBarrier` C++ state machine nepietiek tikai ar SQL vai vienu `cmd47` atbildi. Pirms Diamond pirkuma `success` drīkst būt: ārēji autentificēta sesija -> ārēji noturīgi reģistrēts unikāls intents -> īpašnieka lock ietvaros piemērota izmaiņa -> izsūtīts cmd46 bez konkurējošas rakstīšanas -> pareizs cmd47 ar `CharacterIdx`, `PackFlags` un monotonu notikuma secību -> **no datubāzes neatkarīgi atkārtoti nolasīts faktiskais spēles WExp, inventāra priekšmets 33554961, revīzija, Mastery un saglabātais kvīts ieraksts**. Nevienā no vidusposmiem vēl nav atļauta veiksmīga klienta atbilde.

Jebkura neskaidrība (paralēls cmd46, nozaudēts ACK, neatbilstošs inventāra atlikums, nepareiza revīzija, nesaglabāta kvīts) pāriet `RecoveryRequired` un neļauj paziņot success. `Reset()` apzināti nav: neskaidru darījumu nedrīkst aizmirst no RAM, neizlīdzinot noturīgo stāvokli.

## Precīzi zināmais par Server01 (nolasīts iepriekš tikai metadata režīmā)

- `dbo.cabal_merit_table`: `UserNum`, `MeritPoint`, `MeritMasteryPoint`, `MeritMasteryData varbinary(8000)`.
- `dbo.cabal_merit_platinum_table`: `HaveMeritPlatinumBagde`, `MeritPlatinumPoint`, `MeritPlatinumMasteryPoint`, `MeritPlatinumMasteryOpenIndex`, `MeritPlatinumMasteryRemainPoint varbinary(128)`, `MeritPlatinumMasteryOpenSlot varbinary(1024)` u.c.
- `dbo.cabal_merit_platinum_mastery_table`: `UserNum`, `MeritPlatinumMastery varbinary(8000)`.
- Pastāv `cabalApp_merit_get`, `cabalApp_merit_platinum_get`, `cabalApp_merit_platinum_mastery_get`, bet **nav pierādīts, kā Diamond dati kodēti šajos laukos**.
- Vēl nav pierādīta īstā WExp / priekšmeta 33554961 inventāra transakciju datu bāze un lauku vai procedūru kodējums. Tāpēc šī bibliotēka NEVEIC rakstīšanu un netiek izmantota tieši `Server01`.

## Testi

`bash run-tests.sh` (parasts `g++` un ASan/UBSan):

```text
DIAMOND_WORLD_SAVE_BARRIER_TEST=PASS
IPC_46_47_18B=VALIDATED_AGAINST_SOURCE
ACK_WITHOUT_DURABLE_RECONCILIATION=CANNOT_ACK_SUCCESS
AMBIGUOUS_CONCURRENT_SAVE=RECOVERY_REQUIRED
LIVE_VM_UNCHANGED=YES
```

Testi izmanto sintētiskas datu struktūras, kas atbilst iepriekš v14 pirmkodā identificētajam cmd47 rāmim; netika pārbaudītas reālas CABAL spēlētāju sesijas vai reāli DBAgent atbildes.

## Pirms integrācijas spēlē vēl trūkst

1. Reāls WorldSvr **autentificēta spēlētāja sessijas** adapteris un per-character save lock, kas nepieļauj citas cmd46 rakstīšanas laika logā.
2. Noturīgs `durableIntent` / recovery žurnāls, kura transakcija atspoguļo **faktisko** inventāra un WExp saglabāšanu; sintētiskā `Server01_DiamondLab` tabula nav spēles wallet.
3. Pierādīts WorldSvr/DBAgent `cmd46/47` callback un pārlasīšanas funkcija, kas piešķir `verifiedGameInventory`, `verifiedGameWexp` un `receiptCommitted` tikai pēc neatkarīgas persistence verifikācijas.
4. Reāli v291 Diamond C2S un S2C klienta lauki. `0x0B10` paliek Platinum grade-up; to nedrīkst pārņemt Diamond vajadzībām.
5. Pilns tests izolētā VM *klonā*, nevis pašreizējā strādājošajā VM.

Pirmkods **neaizvieto** `lib.so`, **nemaina** `LD_PRELOAD` un **nerestartē** WorldSvr. Iepriekšējās bibliotēkas/sidecar izmēģināšanas kļūdas (exit 78) neesmu ignorējis.