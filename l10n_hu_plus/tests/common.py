# -*- coding: utf-8 -*-
# author: Online ERP

from __future__ import annotations

from typing import TYPE_CHECKING

from odoo.addons.l10n_hu_edi.tests.common import L10nHuEdiTestCommon

if TYPE_CHECKING:
    from odoo.addons.account.models.account_journal import AccountJournal
    from odoo.addons.base.models.res_currency import Currency


class L10nHuPlusTestCommon(L10nHuEdiTestCommon):
    """Common test base for l10n_hu_plus ZeroDivisionError / HUF rate guards."""

    @classmethod
    @L10nHuEdiTestCommon.setup_country("hu")
    def setUpClass(cls) -> None:
        """Set up HU+ journal flags and currency references on the HU EDI fixture."""
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("l10n_hu_plus.manager_group")
        # enable HU+ on the sale journal
        cls.journal_sale: AccountJournal = cls.company_data["default_journal_sale"]
        cls.journal_sale.write({
            "l10n_hu_plus_enabled": True,
            "l10n_hu_banner_enabled": True,
            "l10n_hu_edi_sending": "manual",
            "l10n_hu_delivery_date_default": "today",
            "l10n_hu_nav_payment_method": "TRANSFER",
            "l10n_hu_cron_batch": 10,
        })
        # currency references
        cls.currency_eur: Currency = cls.env.ref("base.EUR")
        cls.currency_huf: Currency = cls.env.ref("base.HUF")

    @classmethod
    def _setup_eur_company_clean_rates(
        cls,
        *,
        huf_rate: float = 400.0,
        usd_rate: float = 1.1,
        rate_date: str = "2024-01-01",
    ) -> None:
        """Switch the test company to EUR and install clean HUF/USD conversion rates.

        ``L10nHuEdiTestCommon`` creates EUR rates while the company is still HUF. After switching the company currency to
        EUR those leftover EUR rows poison ``_get_conversion_rate`` (EUR→HUF). Drop every company rate, then create HUF/USD
        rows with the technical ``rate`` field (1 company currency unit = ``rate`` foreign units).

        :param float huf_rate: HUF per 1 EUR (technical rate)
        :param float usd_rate: USD per 1 EUR (technical rate)
        :param str rate_date: ``res.currency.rate`` name (date) for the baseline rows
        """
        cls.currency_eur = cls.env.ref("base.EUR")
        cls.currency_huf = cls.env.ref("base.HUF")
        cls.currency_usd = cls.env.ref("base.USD")
        cls.currency_eur.active = True
        cls.currency_huf.active = True
        cls.currency_usd.active = True
        cls.company = cls.company_data["company"]
        cls.company.write({"currency_id": cls.currency_eur.id})
        cls.env["res.currency.rate"].search([("company_id", "=", cls.company.id)]).unlink()
        cls.huf_rate_baseline = cls.env["res.currency.rate"].create({
            "name": rate_date,
            "currency_id": cls.currency_huf.id,
            "company_id": cls.company.id,
            "rate": huf_rate,
        })
        cls.env["res.currency.rate"].create({
            "name": rate_date,
            "currency_id": cls.currency_usd.id,
            "company_id": cls.company.id,
            "rate": usd_rate,
        })
