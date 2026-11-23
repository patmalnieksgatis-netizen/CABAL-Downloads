# CABAL v291 — Diamond Insignia: precīzs Merit resursa ielādes maršruts

2026-11-22. **Statuss: binārā klienta statiska analīze + testi PASS; nekas nav instalēts spēlē.** Šis darbs risina `.enc` formāta nesaderības cēloņa noskaidrošanu, nevis pabeigtu Diamond sistēmas labojumu.

## Pierādīts no klienta oriģinālā `CabalMain.exe`

- Precīza EXE SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`; precīza `Data/meritsystem.enc` SHA256 `3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a`.
- RVA `0x269281` tiešais `call` uz resursu inicializatoru RVA `0x21CE38`, kura cikls ar `mov edx,edi` → `call 0x21CDA4` → `inc edi` → `cmp edi,0x85` apstrādā resursu ID **0 līdz 132**. Tā ir **statiska** izsaukuma saite, nevis dinamiski novērota klienta sesija.
- Failu atlasītājs sasaista ID **52** ar `meritsystem.enc` (RVA `0x21C4A5`, literals `0xB5EE68`) un ID **53** ar `meritsystem_msg.enc` (RVA `0x21C564`, literals `0xB5EE78`).
- Iekšējais lēmumu masīvs pie RVA `0x21D96C`: `flag[52]=1`, `flag[53]=0`. Tāpēc abi resursi iet cauri **atšķirīgiem ceļa/filename veidošanas zariem**. Šie ir *maršrutēšanas* karodziņi, NAV atkodēšanas atslēgas vai Diamond paketes.
- `0x21CDA4 -> 0x21CBD4` veido faila ceļu; `0x21CDE6 -> 0x2178E0` izsauc faila ielādētāju. Pēc šī izsaukuma tiešajā vietā ir `NOP`, pēc tam atbrīvošanas kods; **nav redzama tūlītēja atgriezes koda pārbaude**. Tas vien nenozīmē, ka spēle nekad nepamana kļūdu citviet.
- Ielādētājs veido saspiestās datu plūsmas pointeri no `file+4`, bet konkrētā apakšprogramma pirmos 4 plūsmas baitus XORē ar `92 65 67 57`.
- Tavs oriģinālais `meritsystem.enc` pirmajā DWORD uzrāda 663 334, pēc četrbaitu XOR plūsmas pirmais baits kļūst `9F`. Raw DEFLATE `BTYPE=3` ir aizliegts, tātad **neizdodas šī precīzā ceļa parastā raw-DEFLATE interpretācija**. Tas vēl nepierāda ne faila vispārēju bojājumu, ne citas apstrādes neesamību. Iepriekšējā 138 086 sākuma hipotēžu pārbaude arī nedeva korektu DEFLATE plūsmu.
- Oriģinālā EXE nesatur precīzās baitu virknes `Diamond`/`Insignia` ne ASCII, ne UTF-16LE formā. Tas **nepierāda**, ka Diamond UI vai binārs atbalsts nav pieejams: nosaukumi var būt datu failos, lokalizācijās vai citā formā.

## Kāpēc tas ir svarīgi labojumam

Līdz šim nepamatoti būtu nomainīt esošo `.enc`, ievietot citu versiju vai iekodēt nejaušu Diamond resursu: klients dažādi veido ceļus 52/53, un faktiskā atpakošanas secība vēl nav verificēta ar runtime novērojumu. Arī iepriekš atrastais Merit `0x09F3` nav pierādīta Diamond iegādes komanda. **Nedrīkstētu nosūtīt 11 baitu 0x09F3 veiksmīgu atbildi ar izdomātu Merit budžeta vērtību.**

## Reproducējama pārbaude

```bash
python3 src/prove_resource_route.py --archive /path/CABAL_v291_Diamond_Client_exact.zip --report evidence.json
```

Skripts lasa tikai lietotāja oriģinālo 2-failu ZIP, pārbauda abas SHA256, **17 precīzas x64 instrukciju vietas un 7 tiešas izsaukumu saites**, nolasa klienta `.rdata` failu vārdus un izveido JSON atskaiti. Nekādas atmiņas lasīšanas, spēles startēšanas, klienta modifikācijas, servera restartēšanas vai SQL izmaiņas.

Testi (`tests/test_resource_route.py`) pārbauda precīzo sākotnējo ZIP, kā arī atsakās no jebkādā veidā modificēta `CabalMain.exe` vai `.enc`. Pašas oriģinālā EXE/ENC binārās kopijas netiek iekļautas jaunajā GitHub repozitorijā vai atskaites ZIP.

## Nākamā nepieciešamā saite

**Atrast faktiskās, klienta runtime ielādētās `meritsystem` datu plūsmas struktūru un Diamond UI darbības sūtītāju.** Tā ir objektīva prasība pirms spēlē izmantojama servera atbildes moduļa. Mūsu darījuma, MSSQL un WorldSvr sesijas moduļi joprojām ir izolētā testu stadijā; šis darbs nav gatavs `lib.so` patch.