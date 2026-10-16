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
    from odoo.addons.base.models.res_currency import Currency


@tagged("l10n_hu_plus", "post_install_l10n", "post_install", "-at_install")
class TestHufRateZde(L10nHuPlusTestCommon):
    """Test suite for ZeroDivisionError guards on empty invoice currency rate.

    Tests cover:
    - Journal entry compute sets l10n_hu_huf_rate to 0 without calling rate helpers
    - _l10n_hu_get_currency_rate does not divide by zero when invoice_currency_rate is 0
    - HUF-currency entry returns 1.0 from the currency-rate helper
    - Draft invoice still receives a positive HUF rate (regression)
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Set up EUR company with Hungarian fiscal country and baseline HUF rates."""
        super().setUpClass()
        cls._setup_eur_company_clean_rates(huf_rate=400.0, usd_rate=1.1, rate_date="2024-01-01")

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _create_misc_entry(self, currency: Currency | None = None, move_date: str = "2024-06-15") -> AccountMove:
        """Create a draft miscellaneous journal entry (non-invoice move).

        :param Currency | None currency: move currency (defaults to company EUR)
        :param str move_date: accounting date
        :returns: draft entry with empty invoice_currency_rate
        """
        currency = currency or self.currency_eur
        return self.env["account.move"].create({
            "move_type": "entry",
            "date": fields.Date.from_string(move_date),
            "journal_id": self.company_data["default_journal_misc"].id,
            "currency_id": currency.id,
        })

    # -------------------------------------------------------------------------
    # TEST: COMPUTE SKIP ON NON-INVOICE
    # -------------------------------------------------------------------------

    def test_entry_compute_sets_zero_huf_rate_without_zde(self) -> None:
        """Verify journal entries keep l10n_hu_huf_rate at 0 without ZeroDivisionError."""
        entry = self._create_misc_entry()
        self.assertFalse(entry.is_invoice(include_receipts=True))
        self.assertFalse(entry.invoice_currency_rate)
        entry.invalidate_recordset([
            "l10n_hu_huf_rate",
            "l10n_hu_huf_currency",
            "l10n_hu_invoice_currency_rate_date",
            "l10n_hu_invoice_currency_rate_inverse",
        ])
        entry._compute_l10n_hu_currency()
        self.assertEqual(
            float_compare(entry.l10n_hu_huf_rate, 0.0, precision_rounding=0.0001),
            0,
            "Non-invoice moves must keep l10n_hu_huf_rate = 0",
        )

    # -------------------------------------------------------------------------
    # TEST: _l10n_hu_get_currency_rate GUARD
    # -------------------------------------------------------------------------

    def test_get_currency_rate_guard_zero_invoice_currency_rate(self) -> None:
        """Verify _l10n_hu_get_currency_rate does not divide by zero when rate is 0."""
        entry = self._create_misc_entry()
        self.assertFalse(entry.invoice_currency_rate)
        rate = entry._l10n_hu_get_currency_rate()
        self.assertGreater(
            rate,
            0.0,
            "Guard must fall back to res.currency conversion rate instead of 1/0",
        )
        self.assertEqual(
            float_compare(rate, 400.0, precision_rounding=0.0001),
            0,
            "EUR company EUR entry should resolve HUF via the rate table (400)",
        )

    def test_get_currency_rate_guard_huf_currency_entry(self) -> None:
        """Verify HUF-currency entry with empty invoice_currency_rate returns 1.0."""
        entry = self._create_misc_entry(currency=self.currency_huf)
        self.assertFalse(entry.invoice_currency_rate)
        self.assertEqual(
            float_compare(entry._l10n_hu_get_currency_rate(), 1.0, precision_rounding=0.0001),
            0,
            "HUF move with empty invoice_currency_rate must return 1.0",
        )

    # -------------------------------------------------------------------------
    # TEST: INVOICE REGRESSION
    # -------------------------------------------------------------------------

    def test_draft_invoice_still_computes_positive_huf_rate(self) -> None:
        """Verify draft invoices still get a positive HUF rate after the guards."""
        date_value = fields.Date.from_string("2024-06-15")
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "journal_id": self.journal_sale.id,
            "partner_id": self.partner_company.id,
            "currency_id": self.currency_eur.id,
            "invoice_date": date_value,
            "delivery_date": date_value,
            "invoice_line_ids": [Command.create({
                "product_id": self.product_a.id,
                "quantity": 1,
                "price_unit": 1000.0,
                "tax_ids": [Command.set(self.tax_vat.ids)],
            })],
        })
        self.assertTrue(invoice.is_invoice(include_receipts=True))
        self.assertTrue(
            invoice.l10n_hu_huf_rate > 0.0,
            "Invoice HUF rate compute must remain active for invoices",
        )
