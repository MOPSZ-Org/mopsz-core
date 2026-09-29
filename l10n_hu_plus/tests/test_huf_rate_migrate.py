# -*- coding: utf-8 -*-
# author: Online ERP
from __future__ import annotations

import base64
from typing import TYPE_CHECKING
from odoo import Command, fields
from odoo.tests.common import tagged
from odoo.tools import float_compare
from .common import L10nHuPlusTestCommon

if TYPE_CHECKING:
    from odoo.addons.account.models.account_move import AccountMove
    from odoo.addons.base.models.res_currency import Currency
    from odoo.addons.l10n_hu_plus.models.tag import L10nHuPlusTag


@tagged("l10n_hu_plus", "post_install_l10n", "post_install", "-at_install")
class TestHufRateMigrate(L10nHuPlusTestCommon):
    """Test suite for stored ``l10n_hu_huf_rate`` backfill via ``_l10n_hu_migrate_huf_rates``.

    Tests cover:
    - Posted invoice with NAV XML uses XML ``exchangeRate``
    - Posted invoice without XML uses the live rate table
    - Storno without XML reuses the original rate after normals are migrated first
    - Modification without XML and matching delivery_date reuses the original rate
    - Modification without XML and other delivery_date uses the live table
    - Draft and HUF-company moves are left untouched
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

    def _create_and_post_invoice(
        self,
        currency: Currency | None = None,
        invoice_date: str = "2024-03-15",
        document_type: L10nHuPlusTag | None = None,
    ) -> AccountMove:
        """Create and post a customer invoice on the EUR company.

        :param Currency | None currency: invoice currency (defaults to company EUR)
        :param str invoice_date: invoice / delivery date string
        :param L10nHuPlusTag | None document_type: optional HU+ document type tag
        :returns: posted invoice
        """
        currency = currency or self.currency_eur
        date_value = fields.Date.from_string(invoice_date)
        values = {
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
        }
        if document_type:
            values["l10n_hu_document_type"] = document_type.id
        invoice = self.env["account.move"].create(values)
        return self._post_keeping_draft_huf_rate(invoice)

    def _clear_stored_huf_rate(self, move: AccountMove) -> None:
        """Force an empty stored HUF rate so the move becomes a migration candidate.

        :param AccountMove move: posted or cancelled move to clear
        """
        move.write({"l10n_hu_huf_rate": 0.0})
        self.assertFalse(move.l10n_hu_huf_rate, "Stored HUF rate must be empty before migration")

    def _attach_nav_exchange_rate_xml(self, move: AccountMove, exchange_rate: float) -> None:
        """Store a minimal NAV XML with ``exchangeRate`` on the move EDI attachment.

        :param AccountMove move: move to attach XML on
        :param float exchange_rate: value written into the ``exchangeRate`` element
        """
        xml_bytes = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f"<InvoiceData><exchangeRate>{exchange_rate}</exchangeRate></InvoiceData>"
        ).encode("utf-8")
        move.write({"l10n_hu_edi_attachment": base64.b64encode(xml_bytes)})

    def _create_and_post_reversal(
        self,
        original: AccountMove,
        *,
        document_type: L10nHuPlusTag,
        invoice_date: str | None = None,
    ) -> AccountMove:
        """Create and post a refund linked to ``original`` with the given document type.

        :param AccountMove original: invoice being reversed
        :param L10nHuPlusTag document_type: storno or modification tag
        :param str | None invoice_date: refund dates (defaults to the original delivery_date)
        :returns: posted refund
        """
        date_value = fields.Date.from_string(invoice_date) if invoice_date else original.delivery_date
        refund = self.env["account.move"].create({
            "move_type": "out_refund",
            "journal_id": self.journal_sale.id,
            "partner_id": self.partner_company.id,
            "currency_id": original.currency_id.id,
            "invoice_date": date_value,
            "delivery_date": date_value,
            "reversed_entry_id": original.id,
            "l10n_hu_document_type": document_type.id,
            "invoice_line_ids": [Command.create({
                "product_id": self.product_a.id,
                "quantity": 1,
                "price_unit": 1000.0,
                "tax_ids": [Command.set(self.tax_vat.ids)],
            })],
        })
        return self._post_keeping_draft_huf_rate(refund)

    # -------------------------------------------------------------------------
    # TEST: _l10n_hu_migrate_huf_rates
    # -------------------------------------------------------------------------

    def test_migrate_posted_with_nav_xml_uses_exchange_rate(self) -> None:
        """Verify posted invoice with NAV XML gets the XML exchangeRate on migrate."""
        invoice = self._create_and_post_invoice()
        self._clear_stored_huf_rate(invoice)
        self._attach_nav_exchange_rate_xml(invoice, 387.65)
        updated_count = self.env["account.move"]._l10n_hu_migrate_huf_rates()
        self.assertGreaterEqual(updated_count, 1)
        self.assertEqual(
            float_compare(invoice.l10n_hu_huf_rate, 387.65, precision_rounding=0.0001),
            0,
            "Migration must take exchangeRate from the stored NAV XML",
        )

    def test_migrate_posted_without_xml_uses_rate_table(self) -> None:
        """Verify posted invoice without NAV XML gets the live table rate on migrate."""
        invoice = self._create_and_post_invoice()
        self._clear_stored_huf_rate(invoice)
        updated_count = self.env["account.move"]._l10n_hu_migrate_huf_rates()
        self.assertGreaterEqual(updated_count, 1)
        self.assertEqual(
            float_compare(invoice.l10n_hu_huf_rate, 400.0, precision_rounding=0.0001),
            0,
            "Migration without XML must fall back to l10n_hu_plus_get_rate_data",
        )

    def test_migrate_storno_without_xml_reuses_original_rate(self) -> None:
        """Verify storno without XML reuses the original rate after normals migrate first."""
        invoice = self._create_and_post_invoice()
        self._clear_stored_huf_rate(invoice)
        storno = self._create_and_post_reversal(invoice, document_type=self.document_type_storno)
        self._clear_stored_huf_rate(storno)
        # first pass fills the original from the table; second pass can copy it onto the storno
        updated_count = self.env["account.move"]._l10n_hu_migrate_huf_rates()
        self.assertGreaterEqual(updated_count, 2)
        self.assertEqual(
            float_compare(invoice.l10n_hu_huf_rate, 400.0, precision_rounding=0.0001),
            0,
            "Original must migrate from the live table before the storno fallback runs",
        )
        self._clear_stored_huf_rate(storno)
        self.huf_rate_march.write({"rate": 410.0})
        self.env["account.move"]._l10n_hu_migrate_huf_rates()
        self.assertEqual(
            float_compare(storno.l10n_hu_huf_rate, invoice.l10n_hu_huf_rate, precision_rounding=0.0001),
            0,
            "Storno without XML must reuse the already migrated original rate",
        )
        self.assertNotAlmostEqual(
            storno.l10n_hu_huf_rate,
            410.0,
            places=4,
            msg="Storno must not take the bumped live table rate",
        )

    def test_migrate_modification_same_date_reuses_original_rate(self) -> None:
        """Verify modification without XML and matching delivery_date reuses the original rate."""
        invoice = self._create_and_post_invoice()
        self._clear_stored_huf_rate(invoice)
        modification = self._create_and_post_reversal(
            invoice,
            document_type=self.document_type_modification,
        )
        self._clear_stored_huf_rate(modification)
        self.env["account.move"]._l10n_hu_migrate_huf_rates()
        self.assertEqual(
            float_compare(invoice.l10n_hu_huf_rate, 400.0, precision_rounding=0.0001),
            0,
            "Original must be migrated before the modification fallback runs",
        )
        self._clear_stored_huf_rate(modification)
        self.huf_rate_march.write({"rate": 410.0})
        self.env["account.move"]._l10n_hu_migrate_huf_rates()
        self.assertEqual(
            float_compare(modification.l10n_hu_huf_rate, invoice.l10n_hu_huf_rate, precision_rounding=0.0001),
            0,
            "Same-date modification without XML must reuse the migrated original rate",
        )
        self.assertNotAlmostEqual(
            modification.l10n_hu_huf_rate,
            410.0,
            places=4,
            msg="Matching delivery_date must not take the bumped live table rate",
        )

    def test_migrate_modification_other_date_uses_rate_table(self) -> None:
        """Verify modification without XML and other delivery_date uses the live table."""
        invoice = self._create_and_post_invoice()
        self._clear_stored_huf_rate(invoice)
        self.env["res.currency.rate"].create({
            "name": "2024-04-01",
            "currency_id": self.currency_huf.id,
            "company_id": self.company.id,
            "rate": 420.0,
        })
        modification = self._create_and_post_reversal(
            invoice,
            document_type=self.document_type_modification,
            invoice_date="2024-04-01",
        )
        self._clear_stored_huf_rate(modification)
        self.env["account.move"]._l10n_hu_migrate_huf_rates()
        self.assertEqual(
            float_compare(invoice.l10n_hu_huf_rate, 400.0, precision_rounding=0.0001),
            0,
            "Original must keep the March table rate",
        )
        self.assertEqual(
            float_compare(modification.l10n_hu_huf_rate, 420.0, precision_rounding=0.0001),
            0,
            "Other delivery_date modification without XML must use the live table",
        )

    def test_migrate_skips_draft_and_huf_company(self) -> None:
        """Verify draft and HUF-company moves are not updated by migration."""
        draft = self.env["account.move"].create({
            "move_type": "out_invoice",
            "journal_id": self.journal_sale.id,
            "partner_id": self.partner_company.id,
            "currency_id": self.currency_eur.id,
            "invoice_date": fields.Date.from_string("2024-03-15"),
            "delivery_date": fields.Date.from_string("2024-03-15"),
            "invoice_line_ids": [Command.create({
                "product_id": self.product_a.id,
                "quantity": 1,
                "price_unit": 1000.0,
                "tax_ids": [Command.set(self.tax_vat.ids)],
            })],
        })
        draft_rate_before = draft.l10n_hu_huf_rate
        self.assertTrue(draft_rate_before > 0.0)
        posted = self._create_and_post_invoice()
        self._clear_stored_huf_rate(posted)
        original_company_currency = self.company.currency_id
        self.company.write({"currency_id": self.currency_huf.id})
        try:
            huf_company_invoice = self.env["account.move"].create({
                "move_type": "out_invoice",
                "journal_id": self.journal_sale.id,
                "partner_id": self.partner_company.id,
                "currency_id": self.currency_eur.id,
                "invoice_date": fields.Date.from_string("2024-03-15"),
                "delivery_date": fields.Date.from_string("2024-03-15"),
                "invoice_line_ids": [Command.create({
                    "product_id": self.product_a.id,
                    "quantity": 1,
                    "price_unit": 1000.0,
                    "tax_ids": [Command.set(self.tax_vat.ids)],
                })],
            })
            self._post_keeping_draft_huf_rate(huf_company_invoice)
            huf_company_invoice.write({"l10n_hu_huf_rate": 0.0})
            huf_rate_before = huf_company_invoice.l10n_hu_huf_rate
            # while company is HUF, migration must not touch the HUF-company invoice (nor the EUR posted via domain)
            self.env["account.move"]._l10n_hu_migrate_huf_rates()
        finally:
            self.company.write({"currency_id": original_company_currency.id})
        updated_count = self.env["account.move"]._l10n_hu_migrate_huf_rates()
        self.assertGreaterEqual(updated_count, 1)
        self.assertEqual(
            float_compare(draft.l10n_hu_huf_rate, draft_rate_before, precision_rounding=0.0001),
            0,
            "Draft moves must not be touched by HUF rate migration",
        )
        self.assertEqual(
            float_compare(huf_company_invoice.l10n_hu_huf_rate, huf_rate_before, precision_rounding=0.0001),
            0,
            "HUF company moves must not be touched by HUF rate migration",
        )
        self.assertEqual(
            float_compare(posted.l10n_hu_huf_rate, 400.0, precision_rounding=0.0001),
            0,
            "Non-HUF company posted invoice must still be migrated",
        )
