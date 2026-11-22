# CABAL v291 Diamond Insignia — precīza klienta Merit faila identitātes pārbaude

## Pārbaudītā izšķiršana

- `QueryOpen SUCCESS` nav garantēts faila atvēršanas notikums; tas tiek uzskaitīts tikai kā metadatu vaicājums.
- `CreateFile SUCCESS` parāda, ka `CabalMain.exe` veiksmīgi atvēra konkrēto faila ceļu.
- `ReadFile SUCCESS` ir papildu lasīšanas pierādījums, bet tas nav obligāts failam, kuru klients lasa ar `MapViewOfFile`; tas arī **nepierāda**, ka saturs ir veiksmīgi DEFLATE atkodēts.
- `correlate_procmon_merit_assets.py` sasaista atvērto absolūto Windows ceļu ar agrāk savāktā `CABAL_v291_Merit_Actual_Path_Candidates_20261122.zip` manifestā verificētu relatīvo ceļu, un parāda **savākšanas brīdī** noteikto SHA256. Tas neapgalvo, ka spēles procesa atvēršanas brīdī faila baiti garantēti bija identiski.
- Ja ceļš nav manifestā, SHA un dekodēšanas rezultāti nav zināmi, pat ja faila nosaukums ir tas pats.

## Palaide pēc Process Monitor CSV eksporta

No GitHub lejupielādē šos trīs Python failus vienā direktorijā: `audit_procmon_merit_paths.py`, `audit_merit_candidates.py` un `correlate_procmon_merit_assets.py`.

```powershell
python correlate_procmon_merit_assets.py --procmon "$env:USERPROFILE\Downloads\cabal_merit_procmon.csv" --assets "$env:USERPROFILE\Downloads\CABAL_v291_Merit_Actual_Path_Candidates_20261122.zip" --client-root "F:\CABAL_291_TEST" --out "$env:USERPROFILE\Downloads\cabal_merit_runtime_match.json"
```

Analizators ir tikai lasāms attiecībā pret abiem avotiem un spēles failiem. CSV var saturēt privātus lokālos ceļus: pirms augšupielādes pārbaudi, ko kopīgo.

## Atlikušās robežas

Pats Process Monitor vēl nav uzstādīts vai palaists ar šiem rīkiem. Neesam ieguvuši lietotāja reālās sesijas CSV. Klienta precīzā Merit faila izvēle paliek **NEPIERĀDĪTA**, līdz tiek novērots konkrēts `CreateFile SUCCESS` vai cits ekvivalents runtime pierādījums.

Tas vēl nenosaka Diamond rank-up opcode, nedod izpildāmu klienta patch un neaktivizē esošos WorldSvr/MSSQL izolētos adapterus. Neuzstādīt veco `lib.so` vai sidecar aktīvajā serverī (iepriekšējais `exit 78`).
