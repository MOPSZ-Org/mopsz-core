# -*- coding: utf-8 -*-
# author: Online ERP
from __future__ import annotations

from typing import TYPE_CHECKING
from lxml import etree
from odoo import Command, fields
from odoo.tests.common import tagged
from odoo.tools import float_compare
from .common import L10nHuPlusTestCommon

if TYPE_CHECKING:
    from odoo.addons.account.models.account_move import AccountMove
    from odoo.addons.base.models.res_currency import Currency


@tagged("l10n_hu_plus", "post_install_l10n", "post_install", "-at_install")
class TestStornoHufRate(L10nHuPlusTestCommon):
    """Test suite for non-HUF company HU storno / modification stored ``l10n_hu_huf_rate``.

    Tests cover:
    - EUR company EUR invoice storno keeps the original stored HUF rate after the table changes
    - EUR company USD invoice storno keeps the original stored HUF rate after the table changes
    - Draft storno refreshes from the live table when delivery_date changes
    - Non-storno credit note tagged as modification reuses the original rate while delivery_date matches
    - Modification credit note reuses the original rate; other delivery_date uses the live table; restore uses original
    - Update HU+ fields keeps the original rate on modification while delivery_date matches
    - Reverse Date is invisible on the HU+ account.move.reversal form
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Set up EUR company with HU fiscal country and a baseline March HUF rate."""
        super().setUpClass()
        cls._setup_eur_company_clean_rates(huf_rate=400.0, usd_rate=1.1, rate_date="2024-03-01")
        cls.huf_rate_march = cls.huf_rate_baseline

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _create_and_post_invoice(self, currency: Currency | None = None, invoice_date: str = "2024-03-15") -> AccountMove:
        """Create and post a customer invoice on the EUR company.

        :param Currency | None currency: invoice currency (defaults to company EUR)
        :param str invoice_date: invoice / delivery date string
        :returns: posted invoice
        """
        currency = currency or self.currency_eur
        date_value = fields.Date.from_string(invoice_date)
        invoice = self.env["account.move"].create({
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
        return self._post_keeping_draft_huf_rate(invoice)

    def _bump_march_huf_rate(self, company_rate: float = 410.0) -> None:
        """Change the March HUF table rate so a live recompute would diverge from the stored original.

        :param float company_rate: new technical rate (HUF per 1 EUR) on the March HUF row
        """
        self.huf_rate_march.write({"rate": company_rate})

    def _create_reversal(self, move: AccountMove, date: str, storno: bool = False, is_modify: bool = False) -> AccountMove:
        """Create a reversal via the HU+ wizard and return the resulting move.

        :param AccountMove move: invoice to reverse
        :param str date: reversal date string
        :param bool storno: whether to enable the HU storno flag
        :param bool is_modify: whether to use modify mode (credit note + new draft)
        :returns: reversed move (or new draft when ``is_modify``)
        """
        wizard = self.env["account.move.reversal"].with_context(
            active_model="account.move",
            active_ids=move.ids,
        ).create({
            "date": fields.Date.from_string(date),
            "journal_id": move.journal_id.id,
            "reason": "test storno huf rate",
            "l10n_hu_storno_enabled": storno,
        })
        action = wizard.reverse_moves(is_modify=is_modify)
        return self.env["account.move"].browse(action["res_id"])

    def _align_refund_dates_with_original(self, refund: AccountMove, original: AccountMove) -> None:
        """Set refund invoice/delivery dates to the original so modification HUF-rate reuse can apply.

        The standard reversal wizard may set dates from the wizard ``date``, not the original delivery_date.
        Modify mode often posts the credit note (invoice_date becomes readonly) — reset to draft first so dates
        can be aligned and the draft compute / Update HU+ fields paths remain testable.
        """
        if refund.state == "posted":
            refund.button_draft()
        refund.write({
            "invoice_date": original.invoice_date,
            "delivery_date": original.delivery_date,
        })

    # -------------------------------------------------------------------------
    # TEST: STORNO HUF RATE
    # -------------------------------------------------------------------------

    def test_storno_keeps_original_huf_rate_on_eur_invoice(self) -> None:
        """Verify EUR company EUR storno keeps the original stored HUF rate after the table changes."""
        invoice = self._create_and_post_invoice()
        original_huf_rate = invoice.l10n_hu_huf_rate
        self.assertAlmostEqual(original_huf_rate, 400.0, places=4)
        self._bump_march_huf_rate(410.0)
        storno = self._create_reversal(invoice, "2024-04-01", storno=True)
        self.assertEqual(
            float_compare(storno.l10n_hu_huf_rate, original_huf_rate, precision_rounding=0.0001),
            0,
            "Storno must keep the original stored l10n_hu_huf_rate after create (context + post-create write)",
        )
        self.assertNotAlmostEqual(
            storno.l10n_hu_huf_rate,
            410.0,
            places=4,
            msg="Storno must not take the updated live table rate",
        )

    def test_storno_keeps_original_huf_rate_on_usd_invoice(self) -> None:
        """Verify EUR company USD storno keeps the original stored invoice→HUF rate after the table changes."""
        invoice = self._create_and_post_invoice(currency=self.currency_usd)
        original_huf_rate = invoice.l10n_hu_huf_rate
        self.assertTrue(original_huf_rate > 0.0, "USD invoice must store a positive HUF rate")
        self._bump_march_huf_rate(410.0)
        storno = self._create_reversal(invoice, "2024-04-01", storno=True)
        self.assertEqual(
            float_compare(storno.l10n_hu_huf_rate, original_huf_rate, precision_rounding=0.0001),
            0,
            "USD invoice storno must keep the original stored l10n_hu_huf_rate",
        )

    def test_draft_storno_huf_rate_refreshes_when_delivery_date_changes(self) -> None:
        """Verify a draft storno refreshes from the live table after delivery_date changes."""
        invoice = self._create_and_post_invoice()
        original_huf_rate = invoice.l10n_hu_huf_rate
        self.assertAlmostEqual(original_huf_rate, 400.0, places=4)
        self.env["res.currency.rate"].create({
            "name": "2024-04-01",
            "currency_id": self.currency_huf.id,
            "company_id": self.company.id,
            "rate": 420.0,
        })
        # draft storno without wizard auto-post: create-time rate set like wizard takeover, then date change
        storno = self.env["account.move"].create({
            "move_type": "out_refund",
            "journal_id": self.journal_sale.id,
            "partner_id": self.partner_company.id,
            "currency_id": self.currency_eur.id,
            "invoice_date": fields.Date.from_string("2024-03-15"),
            "delivery_date": invoice.delivery_date,
            "reversed_entry_id": invoice.id,
            "l10n_hu_document_type": self.document_type_storno.id,
            "invoice_line_ids": [Command.create({
                "product_id": self.product_a.id,
                "quantity": 1,
                "price_unit": 1000.0,
                "tax_ids": [Command.set(self.tax_vat.ids)],
            })],
        })
        storno.write({"l10n_hu_huf_rate": original_huf_rate})
        self.assertEqual(storno.state, "draft")
        self.assertEqual(
            float_compare(storno.l10n_hu_huf_rate, original_huf_rate, precision_rounding=0.0001),
            0,
            "Draft storno setup must start from the original stored HUF rate",
        )
        # move both dates: HU+ uses invoice_date when delivery_date > invoice_date
        april = fields.Date.from_string("2024-04-01")
        storno.write({"invoice_date": april, "delivery_date": april})
        self.assertEqual(
            float_compare(storno.l10n_hu_huf_rate, 420.0, precision_rounding=0.0001),
            0,
            "Draft storno must refresh l10n_hu_huf_rate from the live table when delivery_date changes",
        )

    def test_credit_note_without_storno_reuses_original_huf_rate_when_delivery_date_matches(self) -> None:
        """Verify non-storno credit note (tagged modification) keeps the original rate while delivery_date matches."""
        invoice = self._create_and_post_invoice()
        original_huf_rate = invoice.l10n_hu_huf_rate
        self.assertAlmostEqual(original_huf_rate, 400.0, places=4)
        self._bump_march_huf_rate(410.0)
        reversal = self._create_reversal(invoice, "2024-04-01", storno=False)
        self.assertEqual(
            reversal.l10n_hu_document_type_technical_name,
            "invoice_modification",
            "Non-storno refund must be tagged as invoice_modification by the HU+ wizard",
        )
        self._align_refund_dates_with_original(reversal, invoice)
        self.assertEqual(
            float_compare(reversal.l10n_hu_huf_rate, original_huf_rate, precision_rounding=0.0001),
            0,
            "Modification credit note must reuse the original stored rate while delivery_date matches",
        )
        self.assertNotAlmostEqual(
            reversal.l10n_hu_huf_rate,
            410.0,
            places=4,
            msg="Matching delivery_date must not take the bumped live table rate",
        )

    def test_modification_credit_note_reuses_original_huf_rate_when_delivery_date_matches(self) -> None:
        """Verify modification credit note reuses the original stored HUF rate while delivery_date matches."""
        invoice = self._create_and_post_invoice()
        original_huf_rate = invoice.l10n_hu_huf_rate
        self._bump_march_huf_rate(410.0)
        self._create_reversal(invoice, "2024-04-01", is_modify=True, storno=False)
        credit_note = self.env["account.move"].search([
            ("reversed_entry_id", "=", invoice.id),
            ("move_type", "=", "out_refund"),
        ], limit=1)
        self.assertTrue(credit_note, "Modification must create a credit note")
        self.assertEqual(
            credit_note.l10n_hu_document_type_technical_name,
            "invoice_modification",
            "Plus must tag the credit note as invoice_modification",
        )
        self._align_refund_dates_with_original(credit_note, invoice)
        self.assertEqual(
            float_compare(credit_note.l10n_hu_huf_rate, original_huf_rate, precision_rounding=0.0001),
            0,
            "Modification credit note must reuse the original stored rate while delivery_date matches",
        )

    def test_modification_huf_rate_follows_delivery_date_change_and_restore(self) -> None:
        """Verify modification uses the live table on other delivery_date and restores original on match."""
        invoice = self._create_and_post_invoice()
        original_huf_rate = invoice.l10n_hu_huf_rate
        self.assertAlmostEqual(original_huf_rate, 400.0, places=4)
        self._bump_march_huf_rate(410.0)
        self.env["res.currency.rate"].create({
            "name": "2024-04-01",
            "currency_id": self.currency_huf.id,
            "company_id": self.company.id,
            "rate": 420.0,
        })
        self._create_reversal(invoice, "2024-04-01", is_modify=True, storno=False)
        credit_note = self.env["account.move"].search([
            ("reversed_entry_id", "=", invoice.id),
            ("move_type", "=", "out_refund"),
        ], limit=1)
        self.assertTrue(credit_note, "Modification must create a credit note")
        self._align_refund_dates_with_original(credit_note, invoice)
        self.assertEqual(
            float_compare(credit_note.l10n_hu_huf_rate, original_huf_rate, precision_rounding=0.0001),
            0,
            "Matching delivery_date must keep the original stored HUF rate",
        )
        april = fields.Date.from_string("2024-04-01")
        credit_note.write({"invoice_date": april, "delivery_date": april})
        self.assertEqual(
            float_compare(credit_note.l10n_hu_huf_rate, 420.0, precision_rounding=0.0001),
            0,
            "Other delivery_date must refresh l10n_hu_huf_rate from the live table",
        )
        credit_note.write({
            "invoice_date": invoice.invoice_date,
            "delivery_date": invoice.delivery_date,
        })
        self.assertEqual(
            float_compare(credit_note.l10n_hu_huf_rate, original_huf_rate, precision_rounding=0.0001),
            0,
            "Restoring original delivery_date must take the original invoice HUF rate again",
        )

    def test_modification_update_fields_keeps_original_huf_rate(self) -> None:
        """Verify Update HU+ fields does not overwrite the original rate while delivery_date matches."""
        invoice = self._create_and_post_invoice()
        original_huf_rate = invoice.l10n_hu_huf_rate
        self._bump_march_huf_rate(410.0)
        self._create_reversal(invoice, "2024-04-01", is_modify=True, storno=False)
        credit_note = self.env["account.move"].search([
            ("reversed_entry_id", "=", invoice.id),
            ("move_type", "=", "out_refund"),
        ], limit=1)
        self.assertTrue(credit_note, "Modification must create a credit note")
        self._align_refund_dates_with_original(credit_note, invoice)
        self.assertEqual(
            float_compare(credit_note.l10n_hu_huf_rate, original_huf_rate, precision_rounding=0.0001),
            0,
            "Modification must start with the original stored HUF rate",
        )
        credit_note.action_l10n_hu_update_fields()
        self.assertEqual(
            float_compare(credit_note.l10n_hu_huf_rate, original_huf_rate, precision_rounding=0.0001),
            0,
            "Update HU+ fields must keep the original rate while delivery_date matches",
        )
        self.assertNotAlmostEqual(
            credit_note.l10n_hu_huf_rate,
            410.0,
            places=4,
            msg="Update HU+ fields must not write the bumped live table rate",
        )

    # -------------------------------------------------------------------------
    # TEST: REVERSAL WIZARD VIEW
    # -------------------------------------------------------------------------

    def test_reversal_wizard_reverse_date_invisible(self) -> None:
        """Verify Reverse Date is invisible on the combined account.move.reversal form."""
        base_view = self.env.ref("account.view_account_move_reversal")
        view_info = self.env["account.move.reversal"].get_view(base_view.id, "form")
        arch = etree.fromstring(view_info["arch"])
        date_nodes = arch.xpath("//field[@name='date']")
        self.assertTrue(date_nodes, "date field must remain on the reversal form")
        self.assertIn(
            date_nodes[0].get("invisible"),
            ("1", "True", "true"),
            "HU+ must hide Reverse Date (date) on account.move.reversal",
        )
