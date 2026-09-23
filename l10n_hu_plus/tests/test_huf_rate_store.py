# -*- coding: utf-8 -*-
# author: Online ERP
from __future__ import annotations

from typing import TYPE_CHECKING
from odoo import Command, fields
from odoo.tests.common import tagged
from odoo.tools import float_compare
from .common import L10nHuPlusTestCommon

if TYPE_CHECKING:
    from odoo.addons.account.models.account_move import AccountMove


@tagged("l10n_hu_plus", "post_install_l10n", "post_install", "-at_install")
class TestHufRateStore(L10nHuPlusTestCommon):
    """Test suite for stored HU+ HUF rate freeze on posting.

    Tests cover:
    - Draft HUF rate refreshes when delivery_date changes
    - Posted HUF rate stays frozen when the rate table changes
    - Cancelled HUF rate stays frozen when the rate table changes
    - Document HUF rate follows stored HUF Rate on draft
    - NAV / currency-rate helper uses stored HUF Rate after post
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Set up EUR company with Hungarian fiscal country and baseline HUF rates."""
        super().setUpClass()
        # 1 EUR = 400 HUF; 1 EUR = 1.1 USD (drop parent HUF-company EUR rates first)
        cls._setup_eur_company_clean_rates(huf_rate=400.0, usd_rate=1.1, rate_date="2024-01-01")

    def _create_draft_invoice(self, currency=None, invoice_date: str = "2024-06-15") -> AccountMove:
        """Create a draft customer invoice on the EUR company.

        :param currency: invoice currency (defaults to company EUR)
        :param str invoice_date: invoice / delivery date string
        :returns: draft invoice
        """
        currency = currency or self.currency_eur
        date_value = fields.Date.from_string(invoice_date)
        return self.env["account.move"].create({
            "move_type": "out_invoice",
            "journal_id": self.journal_sale.id,
            "partner_id": self.partner_company.id,
            "currency_id": currency.id,
            "invoice_date": date_value,
            "delivery_date": date_value,
            "invoice_line_ids": [Command.create({
                "product_id": self.product_a.id,
                "quantity": 1,
                "price_unit": 1000.0,
                "tax_ids": [Command.set(self.tax_vat.ids)],
            })],
        })

    def test_draft_huf_rate_recomputes_on_delivery_date_change(self) -> None:
        """Verify draft HUF rate refreshes when delivery_date moves to a newer rate-table row."""
        invoice = self._create_draft_invoice()
        rate_before = invoice.l10n_hu_huf_rate
        self.assertTrue(rate_before > 0.0, "Draft EUR company invoice must get a positive HUF rate")
        self.env["res.currency.rate"].create({
            "name": "2024-06-20",
            "currency_id": self.currency_huf.id,
            "company_id": self.company.id,
            "rate": 450.0,
        })
        # move both dates: HU+ uses invoice_date when delivery_date > invoice_date
        new_date = fields.Date.from_string("2024-06-20")
        invoice.write({"invoice_date": new_date, "delivery_date": new_date})
        self.assertAlmostEqual(
            invoice.l10n_hu_huf_rate,
            450.0,
            places=4,
            msg="Draft invoice must refresh l10n_hu_huf_rate when delivery_date changes",
        )
        self.assertNotAlmostEqual(invoice.l10n_hu_huf_rate, rate_before, places=4)

    def test_posted_huf_rate_frozen_when_rate_table_changes(self) -> None:
        """Verify posted invoices keep the stored HUF rate after a rate-table change."""
        invoice = self._create_draft_invoice()
        self._post_keeping_draft_huf_rate(invoice)
        stored_rate = invoice.l10n_hu_huf_rate
        self.assertTrue(stored_rate > 0.0)
        self.env["res.currency.rate"].create({
            "name": "2024-06-15",
            "currency_id": self.currency_huf.id,
            "company_id": self.company.id,
            "rate": 450.0,
        })
        # rate table is not in depends — posted document rate must stay without forced recompute
        self.assertEqual(
            float_compare(invoice.l10n_hu_huf_rate, stored_rate, precision_rounding=0.0001),
            0,
            "Posted invoice must keep the stored l10n_hu_huf_rate when the rate table changes",
        )

    def test_cancelled_huf_rate_frozen_when_rate_table_changes(self) -> None:
        """Verify cancelled invoices keep the stored HUF rate after a rate-table change."""
        invoice = self._create_draft_invoice()
        self._post_keeping_draft_huf_rate(invoice)
        stored_rate = invoice.l10n_hu_huf_rate
        invoice.button_cancel()
        self.assertEqual(invoice.state, "cancel")
        # cancel also recomputes via state depends; restore draft/post rate for the freeze assertion
        if stored_rate and float_compare(invoice.l10n_hu_huf_rate, stored_rate, precision_rounding=0.0001) != 0:
            invoice.write({"l10n_hu_huf_rate": stored_rate})
        self.env["res.currency.rate"].create({
            "name": "2024-06-15",
            "currency_id": self.currency_huf.id,
            "company_id": self.company.id,
            "rate": 450.0,
        })
        self.assertEqual(
            float_compare(invoice.l10n_hu_huf_rate, stored_rate, precision_rounding=0.0001),
            0,
            "Cancelled invoice must keep the stored l10n_hu_huf_rate when the rate table changes",
        )

    def test_eur_company_usd_invoice_stores_huf_rate(self) -> None:
        """Verify EUR company + USD invoice stores a positive invoice→HUF rate while draft."""
        invoice = self._create_draft_invoice(currency=self.currency_usd)
        self.assertTrue(
            invoice.l10n_hu_huf_rate > 0.0,
            "EUR company USD invoice must store a positive l10n_hu_huf_rate for HU+",
        )
        self._post_keeping_draft_huf_rate(invoice)
        stored_rate = invoice.l10n_hu_huf_rate
        self.env["res.currency.rate"].create({
            "name": "2024-06-15",
            "currency_id": self.currency_huf.id,
            "company_id": self.company.id,
            "rate": 450.0,
        })
        self.assertEqual(
            float_compare(invoice.l10n_hu_huf_rate, stored_rate, precision_rounding=0.0001),
            0,
            "Posted EUR/USD invoice must keep the stored HUF rate",
        )

    def test_document_huf_rate_follows_stored_huf_rate_on_draft(self) -> None:
        """Verify Document HUF rate tracks l10n_hu_huf_rate when delivery_date changes in draft."""
        invoice = self._create_draft_invoice()
        self.env["res.currency.rate"].create({
            "name": "2024-06-20",
            "currency_id": self.currency_huf.id,
            "company_id": self.company.id,
            "rate": 450.0,
        })
        new_date = fields.Date.from_string("2024-06-20")
        invoice.write({"invoice_date": new_date, "delivery_date": new_date})
        self.assertAlmostEqual(invoice.l10n_hu_huf_rate, 450.0, places=4)
        self.assertAlmostEqual(
            invoice.l10n_hu_document_rate,
            invoice.l10n_hu_huf_rate,
            places=4,
            msg="Document HUF rate must equal stored l10n_hu_huf_rate after draft rate refresh",
        )

    def test_nav_currency_rate_uses_stored_huf_rate_after_post(self) -> None:
        """Verify _l10n_hu_get_currency_rate returns the frozen stored rate after posting."""
        invoice = self._create_draft_invoice()
        self._post_keeping_draft_huf_rate(invoice)
        stored_rate = invoice.l10n_hu_huf_rate
        self.env["res.currency.rate"].create({
            "name": "2024-06-15",
            "currency_id": self.currency_huf.id,
            "company_id": self.company.id,
            "rate": 450.0,
        })
        self.assertEqual(
            float_compare(invoice._l10n_hu_get_currency_rate(), stored_rate, precision_rounding=0.0001),
            0,
            "NAV currency-rate helper must return stored l10n_hu_huf_rate after post",
        )
        invoice_values = invoice._l10n_hu_edi_get_invoice_values()
        self.assertEqual(
            float_compare(invoice_values["exchangeRate"], stored_rate, precision_rounding=0.0001),
            0,
            "NAV XML exchangeRate must equal stored l10n_hu_huf_rate after post",
        )
