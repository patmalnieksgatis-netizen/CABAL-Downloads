# CABAL v291 Diamond — V11 iegūst nākamos īstos DEFLATE funkciju baitus

**Pamatojums:** no agrāk saglabātā īpašnieka `CABAL_DIAMOND_MERIT_X64_V9_20261122-095035.zip` neatkarīgi disasemblēti īstie 202 baiti RVA `0x2B8004–0x2B80CE`. V9 instrukcijas pierāda viena BFINAL un divu BTYPE bitu apstrādi, pēc kuras notiek trīs DEFLATE bloku atzari (tips 0, 1, 2) vai nederīgā tipa 3 atgriešana. Pilns pierādījums: `V9_REAL_BYTES_DEFLATE_DISPATCH_VERIFIED_20261122.md`.

`Inspect-Cabal291-MeritDeflate-V11.ps1` ir V9 read-only/PE/PData/SHA pārbaudes saglabājošs turpinājums. Tas **neatkārto V9 jau eksportēto 0x2B8004 funkciju**, bet iegūst šos V9 disasemblējumā precīzi norādītos piecus izsaukumu mērķus:

- `0x2B7A90` — baitu lasītājs (noskaidrot precīzu XOR4 ievades buferi);
- `0x2B83F0` — BTYPE 2 atzars;
- `0x2B8898` — BTYPE 1 atzars;
- `0x2B89F0` — BTYPE 0 atzars;
- `0x2178E0` — iepriekš analizētais faila ielādētājs (pārbaudīt plūsmas sākumu un garuma lauka izcelsmi).

### Uz īpašnieka Windows

```powershell
$u='https://raw.githubusercontent.com/patmalnieksgatis-netizen/CABAL-Downloads/feature/diamond-insignia-v291-20261121/diamond-insignia/client-codec/Inspect-Cabal291-MeritDeflate-V11.ps1'
$p="$env:USERPROFILE\Downloads\Inspect-Cabal291-MeritDeflate-V11.ps1"
Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $p -ErrorAction Stop
powershell -NoProfile -ExecutionPolicy Bypass -File $p
```

Skripts lasa tikai `F:\CABAL_291_TEST\Bin\x64\CabalMain.exe` un `Data\meritsystem.enc`, pārbauda precīzus SHA256 un izveido `CABAL_DIAMOND_MERIT_X64_V11_*.zip` ar `MERIT_X64_V11_REPORT.json` Downloads mapē. Koda eksportam ir PDATA robežu pārbaude, un gari/nedokumentēti mērķi tiek marķēti kā nepilnīgi, nevis pasniegti par pilnām funkcijām.

**Statuss:** V11 avots sagatavots GitHub, nav palaists uz Windows oriģināla. Nevar vēl apgalvot, ka DEFLATE atjauno reālo ENC. Nav izdarītas klienta/VM/SQL/WorldSvr izmaiņas.
