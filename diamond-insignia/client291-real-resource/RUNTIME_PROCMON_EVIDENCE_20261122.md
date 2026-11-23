# CABAL v291 Diamond — faktiski atvērtā Merit faila noteikšana

## Kāpēc
V5/V6/V11 precīzie x64 baiti pierāda: ID52 (`meritsystem.enc`) / ID53 (`meritsystem_msg.enc`) iet caur atšķirīgiem ceļa atlases zariem un abi var nonākt pie `CreateFileA` ielādētājā `0x2178E0`. Tomēr statiskais kods un 14 failu inventārs **nepierāda, kurš ceļš ir atvērts reālā spēles sesijā**. Tāpēc pirms ENC pārkodēšanas vajag failu I/O notikuma pierādījumu.

## Precīza, neinvazīva diagnostika
`audit_procmon_merit_paths.py` lasa **jau eksportētu** Microsoft Process Monitor CSV. Tas pats neko nemonitorē, neinstalē, nepalaiž CABAL, nepieslēdzas procesam, neveic procesā injekcijas un nemaina spēles failus.

1. Savā Windows testdatorā atver Process Monitor kā administrators (tikai uzticamā Microsoft Sysinternals versija).
2. Izslēdz notikumu savākšanu, notīri iepriekšējos notikumus, ieslēdz tikai *File System Activity*. Izmanto filtru **Process Name is CabalMain.exe**; ja iespējams, papildus filtrē **Path contains meritsystem**. Sāc savākšanu **pirms klienta starta**, jo Merit faili var tikt ielādēti vienreiz inicializācijas laikā.
3. Startē **tikai savu izolēto testa klientu**, kuram ir vecie, nemainītie faili. Kad klients ir ielādējis resursus, apturi notikumu savākšanu.
4. File → Save → CSV, izvēlies tikai filtrētos notikumus. Pārbaudi, lai CSV satur kolonnas `Process Name`, `Operation`, `Path`, `Result` (vēlams arī `PID`).
5. Palaid Python analizatoru ar CSV, piemēram:

```powershell
python audit_procmon_merit_paths.py "$env:USERPROFILE\Downloads\cabal_merit_procmon.csv" --output "$env:USERPROFILE\Downloads\cabal_merit_opened_paths.json"
```

Rezultāts nodala **veiksmīgu faila atvēršanu** (`CreateFile` / `QueryOpen` ar `SUCCESS`) no **veiksmīgas lasīšanas** (`ReadFile` ar `SUCCESS`), neveiksmīgiem mēģinājumiem (`NAME NOT FOUND`, `ACCESS DENIED`) un visu pārējo procesu/failu notikumiem. Pārbaudītājs neizdara nepamatotu secinājumu, ka veiksmīga faila atvēršana apliecina DEFLATE atkodēšanu vai tieši Diamond pogu.

**Privātums:** oriģinālais Procmon CSV var saturēt citus lokālos ceļus vai konta informāciju; neaugšupielādē pilnu žurnālu bez pārbaudes. Sagatavotais JSON iekļauj tikai konkrētā procesa Merit resursu failu ceļus.

## Pēc rezultāta
- Ja `ReadFile SUCCESS` parāda precīzu `Data/meritsystem.enc`, bet traileris rada nereālu atpakoto izmēru, tā ir spēcīga pazīme, ka ielādes/atkodēšanas maršruts atšķiras no pašreizējā pieņēmuma vai klients pieņem to kā neizdevušos ielādi; jāizseko atgriezes kodi, nevis jālabo fails uz aklo.
- Ja tiek lasīts cits `meritsystem.enc` ceļš, tad jāanalizē **tieši tas fails** un tā SHA. Nekopē citu EP failu bez protokola saderības pārbaudes.
- Ja žurnālā nav faila, tas **nepierāda**, ka klients to nekad nelasa: jāizvērtē uztveršanas brīdis, filtri, cita procesa nosaukums vai agrāka ielāde.

## Drošības robežas
Nekādus `lib.so`, LD_PRELOAD vai Supervisor izvietošanas mēģinājumus uz aktīvā WorldSvr; iepriekšējie mēģinājumi izraisīja `exit 78`. Šis posms ir **tikai klienta faila ceļa pierādīšanai**, nevis Diamond rank-up aktivizēšanai.
