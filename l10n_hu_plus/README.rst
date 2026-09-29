===
HU+
===

*Először magyarul, utána angolul.*

*Hungarian first, English version below.*

----

Magyar leírás
=============

A **HU+** modul az Odoo számlázási és könyvelési folyamatait egészíti ki a magyar jogszabályi előírásoknak megfelelően.

Főbb funkciók
--------------

- **Számla bizonylattípusok** — magyar számla bizonylattípusok kezelése és besorolása
- **Pro-forma számlázás** — dedikált munkafolyamat pro-forma számlák kiállításához
- **Sztornó (érvénytelenítő) számlák** — érvénytelenítő számlák kiállítása a magyar szabályok szerint
- **Folyamatos szolgáltatás számlák** — ismétlődő/folyamatos szolgáltatási számlák támogatása
- **ÁFA dátum kezelés** — külön ÁFA dátum kezelés a számlákon
- **Árfolyam kezelés** — devizás számlák árfolyama a *HU+* fülön (nem forintos könyvelésű cégnél
  a dokumentum HUF árfolyama megerősítéskor rögzül, és ezt használja a NAV-beküldés és a nyomtatás is);
  sztornó átveszi az eredeti számla árfolyamát; módosító számlán azonos teljesítési dátum esetén az eredeti
  árfolyam marad, eltérő dátumnál az aktuális árfolyam érvényesül; a jóváírás varázslón a visszakönyvelési
  dátum mező nem jelenik meg; modulfrissítéskor a megerősített / érvénytelenített számlákon az üres HUF
  árfolyam automatikusan kitöltődik (NAV XML, eredeti számla vagy az aktuális árfolyam alapján; a piszkozat
  és a forintos könyvelésű cég érintetlen marad)
- **Pénzforgalmi számlák** — pénzforgalmi ÁFA elszámolású számlák kezelése
- **Bejövő számlák keltezése** — szállítói számlák eredeti kibocsátási dátumának nyilvántartása
- **Státusz ellenőrző lista** — 12 pontos validációs ellenőrző lista (HU+1 – HU+12) a számlaadatok teljességének biztosítására küldés előtt
- **EDI jogosultság** — automatikus ellenőrzések az elektronikus adatcsere készenlétéhez

A modul a magyar elektronikus számlázási (NAV) megoldásra épül, és a magyar számlatükörrel együtt használandó.

Konfiguráció
-------------

Telepítés után engedélyezze a HU+ funkciókat a megfelelő naplókon a *HU+* fülön. Rendeljen hozzá megfelelő adópozíciókat,
bizonylattípusokat és fizetési módokat a partnerekhez és számlákhoz.

Részletes dokumentáció: `mopsz.odoo.com <https://mopsz.odoo.com>`_.

----

English description
===================

The **HU+** module extends Odoo's invoicing and accounting workflows to comply with Hungarian regulations.

Key capabilities
-----------------

- **Invoice document types** — classification and management of Hungarian invoice document types
- **Pro-forma invoicing** — dedicated workflow for issuing pro-forma invoices
- **Storno (cancellation) invoices** — issuing cancellation invoices according to Hungarian rules
- **Continuous service invoices** — support for recurring/continuous service invoicing
- **VAT date handling** — separate VAT date management on invoices
- **Currency rate management** — foreign-currency document rates on the *HU+* tab (for non-HUF company
  currency the document HUF rate is locked on posting and used for NAV submission and printing);
  storno takes over the original invoice rate; on a modification invoice the original rate is kept when the
  delivery date matches the original, otherwise the current rate applies; the reverse date field is hidden
  on the credit note wizard; on module upgrade, empty HUF rates on posted / cancelled invoices are filled
  automatically (from NAV XML, the original invoice, or the current rate; drafts and HUF-currency companies
  are left unchanged)
- **Cash-flow invoices** — handling of cash accounting (pénzforgalmi) invoices
- **Incoming invoice issue dates** — tracking original issue dates on vendor bills
- **Status checklist** — 12-point validation checklist (HU+1 – HU+12) ensuring invoice data completeness before sending
- **EDI eligibility** — automated checks for electronic data interchange readiness

The module builds on the Hungarian electronic invoicing (NAV) solution and is intended for use with the Hungarian Chart of Accounts.

Configuration
--------------

After installation, enable HU+ features on the relevant journals via the *HU+* tab. Assign appropriate
fiscal positions, document types, and payment modes to your partners and invoices.

For detailed documentation, visit `mopsz.odoo.com <https://mopsz.odoo.com>`_.
