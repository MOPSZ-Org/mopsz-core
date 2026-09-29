# l10n_hu_plus — Tesztek

## Összefoglaló

| Fájl | Osztályok | Tesztmódszerek | Leírás |
|---|---|---|---|
| `common.py` | 1 | — | Közös teszt-bázis (`L10nHuPlusTestCommon`) |
| `test_account_move.py` | 9 | 53 | Számla computed mezők, onchange, akciók, szállítási/dokumentum/árfolyam/ÁFA adatok, EDI jogosultság |
| `test_account_move_status.py` | 3 | 28 | HU+ státusz, státusz checklist (HU+1–HU+12), státusz overview HTML |
| `test_res_partner.py` | 4 | 29 | Partner ÁFA-státusz, láthatóság, cégjegyzékszám validáció, onchange |
| `test_models.py` | 10 | 47 | Tag, log, napló, fizetési feltétel, számlasor, adópozíció, kerekítés, adó, mértékegység, account tag |
| `test_huf_rate_store.py` | 1 | 6 | Stored HUF Rate freeze (draft/post/cancel, Document HUF, NAV helper) |
| `test_storno_huf_rate.py` | 1 | 8 | Stornó / módosító HUF Rate + Reverse Date invisible |
| `test_huf_rate_migrate.py` | 1 | 6 | HUF Rate backfill migráció (XML, tábla, stornó, módosító, scope) |
| `test_invoice_currency_rate.py` | 1 | 2 | Invoice currency rate / delivery date |
| `test_nav_invoice_summary.py` | 1 | 5 | NAV invoice summary / exchangeRate konzisztencia |
| `test_final_invoice_huf_zero_clamp.py` | 1 | 4 | Document HUF zero-clamp végszámlán |
| **Összesen** | **33** | **188** | |

## Tag-ek

Minden tesztosztály a következő tag-ekkel van dekorálva:

```python
@tagged("l10n_hu_plus", "post_install_l10n", "post_install", "-at_install")
```

- `l10n_hu_plus` — csak ennek a modulnak a tesztjei
- `post_install_l10n` — az összes magyar lokalizációs teszt (l10n_hu_edi + l10n_hu_plus)
- `post_install` — Odoo standard: modulok telepítése UTÁN fut
- `-at_install` — modul telepítéskor NEM fut automatikusan

## Futtatás

### Előfeltételek

- Odoo 18 forráskód
- Tesztadatbázis (pl. `mopsz_test`), amelyre az `l10n_hu_plus` modul és függőségei telepítve vannak
- Az `--addons-path` tartalmazza a szükséges addon könyvtárakat

### Parancsok

Az összes példa az Odoo gyökérkönyvtárából indítandó.

**Összes l10n_hu_plus teszt futtatása:**

```bash
./odoo-bin \
    --addons-path=odoo/addons,../enterprise,../mopsz/mopsz-core,../mopsz/mopsz-extra,../oerp-utils \
    -d mopsz_test \
    -i l10n_hu_plus \
    --test-enable \
    --test-tags l10n_hu_plus \
    --stop-after-init
```

**Egy konkrét tesztosztály futtatása** (pl. `TestAccountMoveComputedFields`):

```bash
./odoo-bin \
    --addons-path=odoo/addons,../enterprise,../mopsz/mopsz-core,../mopsz/mopsz-extra,../oerp-utils \
    -d mopsz_test \
    -i l10n_hu_plus \
    --test-enable \
    --test-tags l10n_hu_plus.TestAccountMoveComputedFields \
    --stop-after-init
```

**Összes magyar lokalizációs teszt** (l10n_hu_edi + l10n_hu_plus együtt):

```bash
./odoo-bin \
    --addons-path=odoo/addons,../enterprise,../mopsz/mopsz-core,../mopsz/mopsz-extra,../oerp-utils \
    -d mopsz_test \
    -i l10n_hu_plus \
    --test-enable \
    --test-tags post_install_l10n \
    --stop-after-init
```

### Fontos CLI paraméterek

| Paraméter | Leírás |
|---|---|
| `--addons-path` | Addon könyvtárak vesszővel elválasztva; az útvonalakat a saját környezetedhez igazítsd |
| `-d` | Adatbázis neve |
| `-i` | Telepítendő modul (első futtatáskor); frissítéskor `-u` is használható |
| `--test-enable` | Tesztek futtatásának engedélyezése |
| `--test-tags` | Tag-szűrő — ez nélkül a `post_install` tesztek NEM futnak le |
| `--stop-after-init` | Szerver leáll a tesztek után (nem marad futva) |
| `--log-level=debug` | Részletesebb naplózás (opcionális; alapértelmezett: `info`) |

### Tippek

- Ha a modul már telepítve van, `-i` helyett `-u l10n_hu_plus` is elég.
- A `--test-tags` nélkül a `-at_install` tag miatt a tesztek **nem futnak le**.
- Több tag is megadható vesszővel: `--test-tags l10n_hu_plus,post_install_l10n`.
- A teszt-logokat az Odoo standard logban látod; szűrés: `grep -E "TEST|FAIL|ERROR"`.

## Tesztosztályok

### test_account_move.py

| Osztály | Tesztelt terület |
|---|---|
| `TestAccountMoveComputedFields` | Computed mezők (document_type, fiscal_position, stb.) |
| `TestAccountMoveOnchange` | Onchange események (partner, journal, move_type) |
| `TestAccountMoveActions` | Akciók (post, open_document_type, action buttons) |
| `TestAccountMoveDeliveryData` | Szállítási dátum és related adatok |
| `TestAccountMoveDocumentData` | Dokumentum típus adatok |
| `TestAccountMoveRateData` | Árfolyam adatok |
| `TestAccountMoveVatData` | ÁFA adatok |
| `TestAccountMoveGetData` | `l10n_hu_get_data()` összesítő metódus |
| `TestAccountMoveEdiEligibility` | EDI küldési jogosultság (`l10n_hu_get_send_edi_allowed`) |

### test_account_move_status.py

| Osztály | Tesztelt terület |
|---|---|
| `TestAccountMovePlusStatus` | HU+ státusz mező és átmenetek |
| `TestAccountMoveStatusChecklist` | Státusz checklist elemek (HU+1 – HU+12) |
| `TestAccountMoveStatusOverview` | Státusz overview HTML generálás |

### test_res_partner.py

| Osztály | Tesztelt terület |
|---|---|
| `TestResPartnerVatStatus` | Partner ÁFA-státusz kezelés |
| `TestResPartnerVisibility` | Mező-láthatóság HU+ kontextusban |
| `TestResPartnerCrnValidation` | Cégjegyzékszám (CRN) validáció |
| `TestResPartnerOnchange` | Partner onchange események |

### test_models.py

| Osztály | Tesztelt terület |
|---|---|
| `TestL10nHuPlusTag` | HU+ tag modell (CRUD, validáció, egyediség) |
| `TestL10nHuPlusLog` | HU+ log modell (létrehozás, szűrés, törlés) |
| `TestAccountJournal` | Napló HU+ mezők |
| `TestAccountPaymentTerm` | Fizetési feltétel HU+ mezők |
| `TestAccountMoveLine` | Számlasor HU+ mezők |
| `TestAccountFiscalPosition` | Adópozíció HU+ mezők |
| `TestAccountCashRounding` | Kerekítés HUF-hoz |
| `TestAccountTax` | Adó HU+ mezők és kategória |
| `TestUomUom` | Mértékegység HU+ mezők |
| `TestAccountTag` | Account tag HU+ mezők |

### test_huf_rate_store.py / test_storno_huf_rate.py / test_huf_rate_migrate.py

| Osztály | Tesztelt terület |
|---|---|
| `TestHufRateStore` | Draft refresh, posted/cancel freeze, Document HUF, NAV currency rate |
| `TestStornoHufRate` | Stornó / módosító rate öröklés, delivery_date váltás, Reverse Date invisible |
| `TestHufRateMigrate` | `_l10n_hu_migrate_huf_rates` (XML, tábla, stornó, módosító, draft/HUF cég skip) |

**Csak HUF Rate regresszió futtatása:**

```bash
./odoo-bin \
    --addons-path=odoo/addons,../enterprise,../mopsz/mopsz-core,../mopsz/mopsz-extra,../oerp-utils \
    -d mopsz_test \
    -u l10n_hu_plus \
    --test-enable \
    --test-tags l10n_hu_plus.TestHufRateStore,l10n_hu_plus.TestStornoHufRate,l10n_hu_plus.TestHufRateMigrate \
    --stop-after-init
```
