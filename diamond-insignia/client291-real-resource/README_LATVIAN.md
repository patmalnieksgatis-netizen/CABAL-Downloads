# CABAL v291 Diamond Insignia — atrasts Merit resursa faktiskā ceļa izvēles mehānisms

**Statuss 2026-11-22:** tikai lasāma precīzā x64 klienta statiskā analīze; 16 instrukciju / literāļu / izsaukumu pārbaudes PASS. **NAV** instalējams Diamond labojums, nav pārbaudīta īstā spēles izpildes laika atvērtā faila adrese. Aktīvā CABAL servera fails `lib.so`, Supervisor un SQL netika mainīti.

## Problēma, ko šis posms atrisina

Iepriekš lietotājs iesūtīja `F:\CABAL_291_TEST\Data\meritsystem.enc` (SHA256 `3d859032a8b42c3e011c6d7ff739c9ac088b7f63effbc8afbc7215e162c1b78a`). Vecā `.enc` XOR4 + raw-DEFLATE interpretācija šo konkrēto failu nevar atvērt, bet **tas nenozīmē, ka tieši šis fails spēlē tiek ielādēts**.

Precīzajā `Bin\x64\CabalMain.exe` (SHA256 `52e7956d4781fea1f0369cac8ab1eac4c3ddec2d1977c6557be53ec2b79885d9`):

- RVA `0x21D938` izdara maršruta izvēli: `flag[52]=1` (`meritsystem.enc`), `flag[53]=0` (`meritsystem_msg.enc`).
- Pie `0x21CC2A` tiek izsaukts šis karodziņu atlasītājs. Ja karodziņš ir 1, `0x21CC90` veic Windows **`SHLWAPI!PathFileExistsA`** izsaukumu caur IAT ierakstu `0xB329F8` pār alternatīvo ceļu. Esoša faila gadījumā ietvertais `jne` zars izlaiž papildus meklēšanu.
- Ja alternatīva nav pieejama, `0x21CCA6` izsauc `0x217244`, kura koda posmā tiek izmantots **`\Language\`** ceļa fragments (literal RVA `0xB5E500`) un valodas iestatījumu vērtības. Pilnais ceļš ir atkarīgs no klienta runtime globālajiem iestatījumiem.
- Resursam 53 (flag 0) pie `0x21CCFA` tiek izsaukts `0x216FAC`, kura kodā ir **`\Data`** fragments (literal RVA `0xB5E4E4`). Šis ir cits ceļa salikšanas zars.
- Tikai no statiskās binārā faila pārbaudes **nevar** precīzi apgalvot, kurš no iespējamajiem ceļiem ir reāli atvērts konkrētajā palaistajā CABAL sesijā.

## Nākamais praktiskais solis

`Collect-CABAL291-Merit-Resolved-Candidates.ps1` pārbauda pareizo EXE SHA256, **tikai nolasa** visus failus ar nosaukumu `meritsystem.enc` vai `meritsystem_msg.enc` zem `F:\CABAL_291_TEST`, saglabā to relatīvos ceļus un SHA256, un izveido jaunu ZIP lietotāja `Downloads` mapē. Tas nemaina spēles failus, neatver procesu, neveic VM piekļuvi. Pēc ZIP saņemšanas var salīdzināt, vai valodas resursa variants atšķiras no iepriekšējā `Data\meritsystem.enc`, un mēģināt atkodēt **īsto alternatīvo failu** ar klienta kodam atbilstošu apstrādi.

PowerShell palaišanai ar skriptu Downloads mapē:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\Collect-CABAL291-Merit-Resolved-Candidates.ps1"
```

Augšupielādēt iegūto `CABAL_v291_Merit_Actual_Path_Candidates_20261122.zip`. Ja tiek atrasts tikai sākotnējais Data fails, tas ir derīgs negatīvs rezultāts: tad jāizpēta alternatīvās bāzes direktorijas/runtimes opcijas, nevis jāmin atslēga.

## Verifikācija

```bash
python3 verify_language_fallback.py --client-zip /mnt/data/CABAL_v291_Diamond_Client_exact.zip
python3 -m unittest -v test_selection.py
```

Ir 16 statiski pārbaudīti elementi, 3 regresijas testi. Tas nav pierādījums, ka Diamond pirkuma pieprasījums izmanto `0x09F3`; tas ir vēl esošā Merit protokola ceļš.