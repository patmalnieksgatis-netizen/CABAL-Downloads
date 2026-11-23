# CABAL v291 — īstā MeritSystem.scp konfigurācijas gatavības audits

**2026-11-23. Statuss: tikai lokāla, read-only avota datu pārbaude; Diamond NAV instalējams.**

## Oriģinālais servera SCP

Lietotāja agrāk augšupielādētajā `CABAL-DIAMOND-SOURCES-1bec4d3ce4.zip`
ir `server/active-v291/MeritSystem.scp` (54 866 B), SHA256
`307fc981ec3efe66f6cc1b0606ed7d86cd9e5a6e46205769a9bb34b012464295`.

Pārbaudīta precīza `[MeritMastery_Base]` sadaļa:

- Kopā **158 Mastery rindas**, `Mastery_Index` 1–158.
- `Badge_Grade=0` — 64 rindas, `Badge_Grade=1` — 94 rindas.
- **`Badge_Grade=2` — nulle rindu**; klona Diamond kataloga definīcijas šajā aktīvajā failā nav.

Pārbaudīta precīza `[UpGrade_Material]` sadaļa:

```text
Badge_Grade   Wexp    Need_Item  Need_Count
1             20000   33554961  100
```

Aktīvais `UpGrade_Material` satur tikai šo vienu pāreju
uz `Badge_Grade=1`. Tas nav Diamond rank-up uz pakāpi 2.
Pašlaik izolētajā Diamond noteikumu prototipā ir prasīti
**30 000 WExp un 100 × item 33554961** pakāpei 2; tas
ir **lab modeļa nosacījums**, nevis jau integrēta spēles konfigurācija.
Tāpēc nedrīkst automātiski uzskatīt šo SCP par Diamond gatavu.

## Jauns atkārtojams fails

`audit_real_merit_grade.py` nolasa agrāko ZIP tikai kā ievadi un
no faktiskās SCP tabulas izvada `mastery_grade_counts`,
`upgrade_material`, `diamond_config_candidate` un
`installable_product_confirmed=false`.

```bash
python3 diamond-insignia/native/catalog-audit/audit_real_merit_grade.py \
  --sources-zip /private/CABAL-DIAMOND-SOURCES-1bec4d3ce4.zip
```

`--require-candidate` atgriež nesekmīgu exit statusu, ja
neeksistē vienlaikus grade-2 Mastery rindas un vajadzīgā
`UpGrade_Material` definīcija. Pat pozitīvs rezultāts ir
tikai **konfigurācijas kandidāts**, nevis spēlējama sistēma.

GitHub CI izmanto sintētiskus ievades failus un pārbauda:
vecais Platinum tiek noraidīts, nepilnīgi grade-2 dati noraidīti,
dubultas Mastery ID/rindu indeksi noraidīti, pareizi formulēts
grade-2 kandidāts tiek atzīmēts, bet netiek uzskatīts par instalējamu.

## Tālākais integrācijas šķērslis

Atsevišķi jāidentificē īstā Diamond rank-up klienta komanda no
`0x0BDA–0x0BE0` saimes, jāapstiprina S2C atbilde un
autentificētais WorldSvr/GameData/WExp/MSSQL darījums ar crash-recovery.
Ne mainīt esošo `0x0B10` Platinum handleri, ne akli nomainīt
aktīvo SCP. GameData item stack daudzuma kodējums joprojām nav zināms.

Privātais SCP un klienta/servera bināriji **nav ielikti publiskajā GitHub**.
Aktīvais WorldSvr, SQL, klienta uzstādījums, VM un Supervisor nav mainīti.

## 2026-11-23: apstiprināts, ka staged Diamond SCP jau pastāv

Iepriekšējais aktīvā SCP audits **nenozīmē**, ka nav gatavas
Diamond kataloga kandidātkonfigurācijas. Atsevišķā, lietotāja agrāk
saglabātajā `CABAL_Diamond_v14_ABI3_Lease_OFFLINE_20261122.zip`
ir `MeritSystem.DIAMOND_STAGED_DO_NOT_INSTALL.scp` (116 812 B;
SHA256 `26c9c4cbe3136f67f0298c8e412a4aa7620ba46d62b5c3950880fe821f2ee2e5`).

Tieši salīdzināts ar oriģinālo aktīvo 54 866 B SCP:

- **19/19 sadaļas** vienā un tajā pašā secībā.
- **Visu 19 sadaļu galvenes un iepriekšējās rindas identiskas**.
- **2442 jaunas rindas**: Mastery Base 316, Mastery Value 1096,
  UpGrade Material 1, SlotOpen Material 616, SlotOpen Time 308,
  SpecialMastery Material 1, SpecialMastery Value 100,
  SpecialMastery Active 4.
- Staged Mastery grade-counts: grade 0 = 64; grade 1 = 94;
  **grade 2 = 316**. Staged `UpGrade_Material` satur abas pārejas:
  grade 1 = 20 000 WExp + 100 × 33554961,
  grade 2 = 30 000 WExp + 100 × 33554961.

Jauns `verify_staged_scp_parity.py` + sintētiskais CI tests
precīzi pārbauda šo invariantu kopumu, noraida izmainītu sākotnējo
rindu vai kļūdainu jauno rindu skaitu, un pēc noklusējuma piesaista
faktiskos oriģinālo failu SHA256.

```bash
python3 diamond-insignia/native/catalog-audit/verify_staged_scp_parity.py \
  --active-zip /private/CABAL-DIAMOND-SOURCES-1bec4d3ce4.zip \
  --staged-zip /private/CABAL_Diamond_v14_ABI3_Lease_OFFLINE_20261122.zip
```

**Šis posms izpildīts offline.** Staged SCP jau ir derīgs
pēc statiskās saglabāšanas paritātes pārbaudes; tas **joprojām
NAV** pārbaudīts pret reālo WorldSvr ielādi, spēles C2S/S2C,
GameData inventāru vai MSSQL. Uz aktīvā servera neinstalēt.
