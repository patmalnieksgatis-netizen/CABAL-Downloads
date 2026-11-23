# CABAL v291 Diamond — 0BDA game transaction path (2026-11-23)

## Šajā izmaiņu komplektā ir reāls C++ integrācijas posms

`Diamond0BDAGameplayAction.h/.cpp` kopā vienā funkcijā
`PrepareAndCommitRealGradeUp` savieno:

- **Oriģinālā v291 klienta 0BDA pieprasījuma** formāta parsēšanu;
- obligātu WorldSvr per-character ekskluzīvo lock, autentificēta
  UserNum/CharacterIdx, sesijas paaudzes un revīzijas atbilstību;
- atsevišķi apstiprināmu 0BDA inventāra izvēles semantiku,
  divu vai vairāku *servera* 48-baitu inventāra steku
  daudzuma atkodēšanu, dubulto slotu noraidīšanu;
- Platinum `0x0B10` nodošanu oriģinālajam serverim;
- oriģinālā Diamond `rank_up` 30 000 WExp, 100 biļešu,
  maxed Platinum un grade=2 nosacījumu atomisku plānu;
- `AtomicCommitCallback` ar skaidru
  `RolledBackOrRejected / CommittedNeedsIndependentSaveVerification /
  InDoubtRecoveryRequired` rezultātu;
- precīzu receipt intent/revision pārbaudi;
- **nekādu automātisku S2C**: pabeigta DB commit rezultāts viens
  pats vēl nav pierādījums `cmd46/47` un klienta atbildes ABI.

`test_0bda_gameplay_action.cpp` izmanto tikai **sintētisku**
hosta atmiņas/commit callback. Tas pārbauda 2 biļešu stekus
60+80, debit plan 60+40, 30 000 WExp, 100 biļešu samazinājumu,
nemainītu Platinum/opcode 0B10, svešu owner, neapstiprinātu
0BDA semantiku, nederīgu sarakstu, pārtrauktu/neskaidru commit
un svešas receipt noraidīšanu. C++17 kods ir iekļauts
`.github/workflows/diamond-native-rules.yml`, kur native
workflow **PASS** uz commit `0daa9fccc7356ae9680a42c06ae2d90a47211550`.
Tajā pašā commit arī pārējās divas CI darbplūsmas ir **PASS**.

## Kā to pieslēgt īstajam WorldSvr

Nepieciešams īsts savienojums, kas **vēl NAV implementēts**:

1. Pieņemt 0BDA paketē no precīzi šī servera jau autentificētā
   transporta un hosta reģistrācijas, nevis pārveidot Platinum handleri
   vai pieņemt viltotu klienta account ID.
2. Hosta WorldSvr owner lock laikā verificēt
   `0x0BDA` UI notikumu, inventāra slotu nozīmi, item 33554961
   pašreizējo itemcatalog kind+0x38/stack+0x3C un UserNum/CharacterIdx.
3. Hosta `AtomicCommitCallback` **vienā reālā GameData transakcijā**
   nodrošināt ticket-item blob un WExp ieturējumu, grade2/316 Mastery
   progresu, receipt un nonce/revision idempotenci. Shadow tabula
   `Server01_DiamondLab` nav pieņemama reālai spēlei.
4. Implementēt oriģinālā DBAgent `cmd46/47` async saglabāšanas
   barjeru ar **neatkarīgu** relogin/restart GameData pārbaudi
   un atbildes koda/garuma attiecību, kas iegūta no īstas
   v291 klienta / saderīga servera.
5. Integrēt faktiskajā `ProcSystem::DoProcessDataCtx` vai
   drošā WorldSvr procedūras reģistrācijā, nepārrakstot
   veco `0x0B10`/ `0x0B13` un neizmantojot extension
   opcode reģistru (tas ir tikai `4000+`, savukārt
   `0x0BDA = 3034`). Pilnā VM avota/bibliotēkas maiņa
   iepriekš beidzās ar `exit 78`, tāpēc to nedrīkst akli atkārtot.
6. Atjaunošanas punkts vai patiešām pilns failu un DB backup,
   pirmā pakāpes paaugstināšana klona testa kontā, atkārtota
   pieprasījuma un 2 steku WExp/GUI attēlošanas pārbaude.

**Svarīgi:** pat ja C++ hosta virsma ir uzrakstīta un sintētiskās
kompilācijas ir zaļas, **spēlē Diamond joprojām NAV ieslēgts**.
Neuzstādīt tikai `libDiamondNative.so` un neapgalvot, ka
tas spēlē radīs jaunu izvēlni vai strādājošu rank-up.

### Konkrēti, kas jāiegūst no `EP36_291_TEST`

- Precīzs `0BDA` pieprasījums, nospiežot Diamond rank-up UI;
- īstās ticket katalogu lauku `0x13CAB80/84` vērtības;
- konkrētais GameData `cabal_inventory_table` blob + WarExp
  saglabāšanas API un reālā Merit progresa shēma;
- verificēts WorldSvr callback reģistrācijas / S2C nosūtīšanas ceļš.

Bez šiem faktiem nav pamata ieviest spekulatīvu spēles resursu
norakstīšanu vai viltotu 7-baitu veiksmes paketi.

**Aktīvais EP36_291_TEST nav mainīts.** Tika labots tikai GitHub avots.
