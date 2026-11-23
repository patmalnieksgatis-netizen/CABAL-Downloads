# CABAL v291 — biļetes 33554961 īstā WorldSvr metadatu tipa iegūšana

**2026-11-23 — sagatavots rīks. Vēl NAV iegūts īsta klona izpildes rezultāts.**

## Kāpēc šis posms ir vajadzīgs

Oriģinālais, apstiprinātais `WorldSvr_FULLCHAIN_20261108` izmanto
`0xAE0E90`, lai interpretētu priekšmeta daudzumu no 48 baitu
inventāra ieraksta. Daudzums atkarīgs no izpildes laikā ielādēta
priekšmeta kataloga ieraksta:

- prece `33554961 = 0x02000211`;
- kataloga indekss `529`, variants `1`;
- metadatu sākuma virtuālā adrese `0x13CAB48`;
- klasifikācija `DWORD +0x38 = 0x13CAB80`;
- stack/quantity konfigurācija `signed DWORD +0x3C = 0x13CAB84`.

Šie 8 baiti atrodas atmiņas apgabalā, ko nespēj sniegt
statiskā WorldSvr ELF faila diska kopija. Tos nevar aizstāt ar
`items.xml` priekšmeta nosaukuma rindu vai ar CashShop
`999` norādi (veikala piedāvājums nav servera inventāra kodējums).

## Jaunais praktiskais rīks

`capture_clone_ticket_catalog.py` nolasa **tikai šos 8 baitus**
no WorldSvr procesa, neapturot un nerakstot tā atmiņā.

Pirms lasīšanas tas pieprasa visus šos nosacījumus:

1. Operators patstāvīgi apstiprina, ka tiek izmantots
   **izolēts, atjaunojams VM klons**; uz aktīvā servera
   šo rīku nedrīkst palaist.
2. Procesam tiek uzrādīta lokāla autorizācijas JSON datne
   ar stingrām `0600` piekļuves tiesībām. Tajā fiksēta
   precīza `pid`, `machine_id`, ELF SHA256 un priekšmeta ID
   atbilstība.
3. `/proc/PID/exe` SHA256 precīzi sakrīt ar
   `caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3`
   un izmērs ir `10,596,184` baiti.
4. Virtuālās atmiņas karte apstiprina, ka
   `0x13CAB80..0x13CAB87` ir lasāms apgabals.
5. PID procesa sākuma laiks ir nemainīgs visā pārbaudē.

Pēc veiksmīga nolasījuma izvada tikai `kind_field38`,
`stack_field3c_signed` un iegūtā kodējuma atzara nosaukumu,
neizvadot kontu, varoņu, inventāra, atmiņas dump vai privātos datus.
**Autorizācijas JSON pats par sevi nepierāda, ka VM ir klons** — šo
faktu pārbauda operators. Darbībai vajadzīgas pietiekamas OS
tiesības uz sava klona procesu; kļūmes gadījumā rīks noraida, nevis
mēģina mainīt piekļuves politiku.

### Izmantošanas līgums klonā (Codex/operatoram)

Pēc klona identitātes, restaurācijas punkta un īstā WorldSvr PID
apstiprināšanas izveido autorizācijas failu ar tieši pieciem laukiem:

```json
{
  "purpose": "DIAMOND_V291_DISPOSABLE_CLONE_METADATA_READ_ONLY",
  "machine_id": "<32 simbolu klona /etc/machine-id>",
  "pid": 12345,
  "world_sha256": "caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3",
  "ticket_item_id": 33554961
}
```

Piešķir failam `0600` tiesības un izpildi **tikai klonā**:

```sh
python3 capture_clone_ticket_catalog.py --pid 12345 \
  --clone-marker /run/diamond_v291_clone_ticket_read.json
```

`12345` ir tikai dokumentācijas piemērs, **nevis atrasts PID**.

## Kas būs atrisināts ar īsto klona rezultātu

Kad metadatu dati būs iegūti, pārbaudāmais `0xAE0E90`
daudzuma lasīšanas atzars kļūs konkrēts (7/10/16 bitu vai
viens vienums), tādējādi varēs pareizi interpretēt biļetes
daudzumu oriģinālajā 48-baitu WorldSvr inventāra ierakstā.

Tas **vēl nebūs** pats Diamond rank-up produkts.
Atsevišķi paliek `0x0BDA` saraksta semantikas apstiprināšana,
stabils `PROCEDUREMAP` handlers, autentificēta GameData/MSSQL
saglabāšana un pirmā reālā veiksmīgā spēles darbība klonā.

## Testi un robežas

`test_capture_clone_ticket_catalog.py` izmanto tikai sintētiskus
Linux `/proc` tekstus, nelasa neviena reāla procesa atmiņu.
Tiek pārbaudīta markeru identitātes piesaiste, atmiņas robežas,
fiksētas adreses un visu daudzuma atzaru izvēle.
Tas ir pievienots GitHub Actions native workflow.

Atsevišķais `Diamond0BDATicketSelection.cpp` tagad
**pēc noklusējuma obligāti noraida** neapstiprinātu `0x0BDA`
biļešu slota nozīmi ar
`UnverifiedSelectionSemantics`; jaunās spēles komandas
saraksts nav automātiski ekvivalents oriģinālā Platinum
`0x0B10` inventāra sarakstam. Sintētiskajos testos šo
pieņēmumu var ieslēgt tikai kā skaidri marķētu fikstūru,
nevis uzskatīt par reālu WorldSvr apliecinājumu.

**Nav spēles procesa, SQL, GameData, klienta vai WorldSvr izmaiņu.**
