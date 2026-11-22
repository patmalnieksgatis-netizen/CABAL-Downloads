# CABAL v291 Diamond Insignia — precīzā `0x09F3` Merit protokola semantika

**Datums:** 2026-11-22. **Rezultāts:** jauni *lasāma pirmkoda* pierādījumi, nevis instalējams spēles labojums. Neviena aktīvā VM, SQL vai klienta faila izmaiņa.

## Pierādīts ar lietotāja precīzo klientu

- `CabalMain.exe` SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`, 15,089,000 B.
- `meritsystem.enc` SHA256 `3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a`, 41,368 B.
- Klienta **lokālā** notikuma ID `0x1A1` (koriģēts pēc pilnas reģistrācijas secības pārbaudes) ir reģistrēta funkcija RVA `0x6FF14C`, kas sūta C2S **`0x09F3` 18 baitu** paketi, pie `+0x0A` un `+0x0E` ievietojot `Merit` singleton `+0x118` un `+0x11C` laukus. Pārbaude: RVA `0x6F123F`, `0x6F1253`, `0x6FF157`, `0x6FF161`, `0x6FF17C`, `0x6FF197`.
- Tīkla `0x09F3` atbildes apstrādātājs reģistrēts pie RVA `0x6EFED7`, `0x6EFEEE`, mērķis `0x6F84FC`. Sekmīga statusa (`+6 == 1`) atzarā tiek **nosacīti** lasīts `uint32_le` no `+7` RVA `0x6F8585` vai `0x6F85B9`.
- Pirmajā atzarā `0x37FA34` saņemtais skaitlis tiek ierakstīts Merit objekta laukā `+0xAB6C`. Kad Merit UI saskaita izlietotos punktus, tās pārbaudes RVA `0x2523BF–0x2523E3` un `0x63B70F–0x63B72D` **salīdzina šo budžetu ar iztērēto punktu summu**. Tādēļ papildu vērtība šajā atzarā ir Merit pieejamais punktu budžets/limits, nevis ignorējams padding.
- Citā atzarā `0x37F9D8` pieraksta `+7` skaitli kā vērtību Merit divu atslēgu stāvokļa tabulā (sk. RVA `0x37FA1B`). Šīs tabulas domēna lauku nozīme nav pilnīgi identificēta.
- Iepriekš arhivētajā WorldSvr bija pierādīta *atsevišķa* `0x09F3` statusa `1` atbilde ar **7 baiti**, kam pie `+7` nav DWORD. Tā ne vienmēr izraisa atmiņas kļūdu: tas atkarīgs no tā, kuru klienta nosacīto atzaru serveris aktivizē. Šajā posmā oriģinālais `WorldSvr` binārais fails nebija pieejams atkārtotai binārai pārbaudei, tāpēc paļaujamies uz iepriekšējās pakotnes izsekojumu.

## Būtiska iepriekšējā pieņēmuma korekcija

`dia_meritscore_fomula` atrodas pašā klienta binārijā blakus atslēgām `trophyreward_meritscore` un `trophy_transform`; tas ir **Trophy konfigurācijas konteksts**, nevis pierādījums tieši *Diamond Insignia* pirkumu funkcijai. Turklāt `0x1030` iepriekš kļūdaini tika nosaukts par paketi, bet tā konkrētā lietošana ir teksta formatēšanas ceļš. Šīs lietas nedrīkst izmantot kā Diamond opcode pierādījumu.

## `.enc` atkodēšanas pārbaude

Publiskā [libcozip](https://github.com/Michael-K-GH/libcozip) formāta piemērā pirmie četri baiti ir atpakotais garums, nākamos **četrus saspiestās plūsmas baitus** XOR kodē un pārējo atpako ar raw DEFLATE. Lietotāja faila sākumā `0x000A1F26` = **663334** (ticams nesaspiestais garums, vēl nav pierādīts).

- Pārbaudīts algoritms ar pašu ģenerētu testu (600000 B, raw DEFLATE, atslēga `0x12345678`): **PASS**, rīks atrada īsto atslēgu, pilnībā atjaunoja datus.
- Tas pats algoritms ar **precīzo lietotāja 41368 B `meritsystem.enc`**: **NO VALID DEFLATE**, tika izslēgtas 138086 iespējamās kandidātgalvenes. Tātad failam var būt cita atslēgu shēma, cits iepakojuma variants vai papildu šifrēšana; **atkodējums nav iegūts**.
- Reālā klienta/SQL datu faili nav mainīti. Rīks nemēģina minēt spēlētāju kontus vai atslēgas serverim.

## Materiāli

- `evidence/verify_client291_semantics.py`: skripts piesaistīts precīzam SHA, pārbauda konkrētās x64 opcode instrukcijas un RIP relatīvās atsauces; neraksta klienta failos.
- `evidence/VERIFIED_CLIENT291_SEMANTICS.json`: faktiskais PASS pārskats no lietotāja klienta.
- `evidence/client291_09F3_disassembly.txt`: attiecīgo funkciju x64 disasemblētie fragmenti.
- `evidence/recover_enc_xor4.py`: ierobežota, lokāla CABAL veida raw-DEFLATE XOR pirmā DWORD formāta pārbaude ar sintētisku pozitīvo kontroli; **nav derīgs dekoders šī klienta failam**.
- `evidence/ENC_FORMAT_RESULT.txt`: pozitīvās kontroles un īstā faila negatīvās pārbaudes rezultāti.

## Nepieciešams reālajam Diamond labojumam

1. **Pierādīt, kuru C2S opcode sūta Diamond Insignia pogas**; `0x1A2` vietējā Merit darbība NAV tieši identificēta kā Diamond.
2. Pierādīt servera autoritatīvo `0x09F3` papildu skaitļa avotu un pilno S2C atbildes shēmu. **Nesūtīt izdomātu 11B success un nulles**.
3. Izprast v291 `meritsystem.enc` patieso kriptēšanas/dekompresijas metodi, nevis pielietot EP33 key.
4. Piesaistīt esošo `DiamondCommitGate`, ODBC adapteri, WorldSvr sesiju adapteri un `WorldSaveBarrier` reālai vienotai inventāra/WExp/kvīts saglabāšanai un pārbaudīt atsevišķā VM klonā.
5. **Nedrīkst** uzstādīt veco `lib.so` patch, Sidecar vai Supervisor instalatoru, jo iepriekš tie izraisīja WorldSvr `exit 78`. Pašreiz lietotājs jau pārbaudīja spēlē, ka atjaunotais serveris darbojas.

**Statuss:** PROTOCOL_EVIDENCE_PASS; DIAMOND_GAMEPLAY_PATCH_NOT_READY.
## Labojums — UI notikuma reģistrācija (2026-11-22)

Iepriekšējais apgalvojums par `0x1A2 -> 0x6FF14C` bija **off-by-one kļūda**. Pilns reģistrācijas kods pierāda: `0x1A1 -> 0x6FF14C -> C2S 0x09F3`, savukārt `0x1A2 -> 0x6FCD44 -> C2S 0x09FD` (atsevišķā nosacītā atzarā). Sk. [UI_EVENT_1A1_CORRECTION_AND_ADJACENT_C2S_20261122.md](UI_EVENT_1A1_CORRECTION_AND_ADJACENT_C2S_20261122.md). Nav pierādīts, ka kāds no tiem ir Diamond rank-up.
