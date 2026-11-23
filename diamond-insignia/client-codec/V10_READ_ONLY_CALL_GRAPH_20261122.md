# CABAL v291 Diamond Insignia — V10 statiskā x64 analīze

**Stāvoklis:** tikai lasāma analīze. Nekas nav instalēts spēlē.

Iepriekšējais V9 skripts `Inspect-Cabal291-MeritProcessing-V9.ps1` eksportē trīs faktisko x64 funkciju kontekstus:

- `buffer_processing_step` pie RVA `0x2B8004`;
- `buffer_copy_like_callee` pie `0xA37890`;
- `linked_buffer_free_callee` pie `0xA6BE2C`.

V10 `analyze_v9_call_graph.py` izmanto **oriģinālo V9 eksportu** (ZIP vai JSON), pārbauda precīzus EXE/ENC SHA256, statiskās analīzes atzīmes, PDATA diapazonus un koda baitu garumus. Pēc tam ar GNU objdump veido x64 disasemblējumu un tiešo CALL izsaukumu sarakstu.

Palaide Linux vai WSL:

```bash
python3 analyze_v9_call_graph.py CABAL_DIAMOND_MERIT_X64_V9_YYYYMMDD-HHMMSS.zip --out V9_DISASSEMBLY
python3 -m unittest -v test_analyze_v9_call_graph.py
```

Rezultāts: `V9_STATIC_CALL_GRAPH.json` un katrai funkcijai atsevišķs `.asm.txt`. Izvades direktorijai iepriekš nav jāeksistē.

**Svarīgi:** līdz reālā V9 ZIP rezultāta izlasīšanai nevar apgalvot, ka `0x2B8004` pievieno XOR, AES, zlib vai citu konkrētu transformāciju. Tiešo izsaukumu karte vēl nav datu plūsmas pierādījums. Visu 14 iesūtīto Merit resursu nesaderība ar *vienu* novēroto XOR4 + raw-DEFLATE interpretāciju nenozīmē, ka faili ir bojāti.

Diamond C2S/S2C identifikācija un īsta spēles inventāra/WExp + MSSQL darījuma pieslēgšana WorldSvr joprojām ir atsevišķi nepierādīti posmi. Nedrīkst atkārtoti uzstādīt veco `lib.so`/Sidecar testu uz aktīvā servera pēc agrākā `exit 78`.
