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
