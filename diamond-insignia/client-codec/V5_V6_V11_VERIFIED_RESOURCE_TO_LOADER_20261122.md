# CABAL v291 Diamond — precīza Merit resursu ceļa nodošanas pārbaude (2026-11-22)

## Datu avoti

Izmantoti lietotāja iepriekš saglabātie V5, V6 un jaunā V11 īsto klienta baitu ZIP eksporta faili, visi ar `CabalMain.exe` SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`. V5: `selector_wrapper` (RVA 0x21CBD4–0x21CDA4, 464 baiti); V6: `indexed_path_wrapper_caller` (0x21CDA4–0x21CE36, 146 baiti); V11: `enc_file_loader` (0x2178E0–0x217A5C, 380 baiti). Visiem ir apstiprinātas PDATA robežas.

Jauns neatkarīgi reproducējams pārbaudītājs: `verify_v291_merit_loader_chain.py`. Tas pārbauda SHA/mode, funkcijas pilnu baitu garumu, 19 instrukciju/izsaukumu vietas. Sintētiskie testi atsaka izmainītu resursa zaru vai mainītu faila ielādētāja CALL mērķi. Šis ir tikai statisks pētījums — nav palaists spēles process.

## Pierādītais izsaukumu maršruts

1. `0x21CDA4` saņem resursa ID `edx`; to saglabā `rbx` un `0x21CDC6` izsauc `0x21CBD4`, lai izveidotu resursa ceļu.
2. `0x21CBD4` izmanto `0x21CC2A -> 0x21D938` resursa tipa karodziņu. Kā iepriekš pierādīts, ID 52=1 un 53=0.
3. Karodziņa 1 zars: `0x21CC90` izmanto `SHLWAPI!PathFileExistsA`, un alternatīva trūkuma gadījumā `0x21CCA6 -> 0x217244` veido valodai atbilstošu rezerves ceļu. Karodziņa 0 zars: `0x21CCFA -> 0x216FAC` veido citu, `\\Data` ceļa variantu.
4. `0x21CDCE` pārbauda īsās virknes (SSO) robežu `0x10`; `0x21CDD8..0x21CDE2` no resursa ID aprēķina ierakstu ar soli **16 baiti**, adresējot `record+8`.
5. `0x21CDE6 -> 0x2178E0` tieši nodod iegūtā ceļa virkni, izvades bufera pointeri un ieraksta garuma lauka adresi; **starp diviem izsaukumiem nav citu datu satura transformāciju**.
6. `0x2178E0` Windows CreateFileA atver norādīto ceļu, SetFilePointer dodas uz faila beigām, ar `file_length-4` nolasa 4 baitu traileri, pēc tam kartē ievades failu un nodod `mapped+4` uz `0x2B7FAC`.
7. Tālāk V9/V11 ir apstiprināta DEFLATE BFINAL/BTYPE un bloku tipa 0/1/2 apstrāde; baitu lasītājs `0x2B7A90` pirmos 4 ievades baitus XORē ar `92 65 67 57`.

## Neatrisinātā atšķirība

Lietotāja 14 faktiskie `meritsystem*.enc` kandidāti nesakrīt ar šo vienkāršo `file[4:-4] -> XOR4 -> raw-DEFLATE` formātu. Piemēram, `Data/meritsystem.enc` traileris ir `5b 2f f2 58` (1 492 266 843 LE), kas nebūtu saprātīgs atpakotais izmērs salīdzinoši mazam resursam.

**Pārbaudītā funkciju izsaukumu ķēde nepierāda, ka spēle runtime tiešām atver šo konkrēto Data failu.** Alternatīvs ceļš, cita resursu pakotne vai cita formāta apstrāde joprojām ir iespējama. Nepārveidot ENC un neizdomāt atslēgas.

### Precīzais nākamais pierādījums

Jānosaka reālā faila atvēršanas ceļa vērtība **tieši `0x217918` CreateFileA izsaukuma brīdī**, un jāsaista to ar resursa ID 52/53, izmantojot tikai izolētu klienta kopiju / lasāmu runtime diagnostiku. Alternatīva ir pārbaudīt klienta globālo valodas konfigurācijas stāvokli un failu esamību konkrētajos ceļos, tomēr tas nav tik pārliecinošs kā faktiska atvēršana.

Kad ir pierādīts reālais resurss un ENC kodējums, var atšķirt esošā Merit atbalsta robežas no trūkstošā Diamond atbalsta. Spēlē izmantojamu Diamond rank-up opcode, WorldSvr patiesu inventāra/WExp+SQL vienoto darījumu, S2C atbildi un VM klona regresijas joprojām nav pierādīts. Veco `lib.so` / Supervisor instalēšanu neatkārtot pēc `exit 78`.

**Šis posms: tikai lasīšana, nav klienta, WorldSvr, SQL un VM modifikāciju.**
