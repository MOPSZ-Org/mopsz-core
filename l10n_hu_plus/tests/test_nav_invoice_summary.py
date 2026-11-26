# -*- coding: utf-8 -*-
# author: Online ERP
from __future__ import annotations

from unittest.mock import patch

from freezegun import freeze_time

from odoo.addons.l10n_hu_edi.tests.common import L10nHuEdiTestCommon
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestNavInvoiceSummaryConsistency(L10nHuEdiTestCommon):
    """Test suite for NAV invoice summary rounding / split-tax-line fix.

    Tests cover:
    - Invoice summary totals are consistent with per-VAT-rate breakdown
    - Fix prevents INCORRECT_SUMMARY_CALCULATION NAV warnings
    - Split tax journal lines for the same VAT tax are aggregated (analytic)
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Set up test fixtures: posted invoices with amounts that trigger rounding."""
        with freeze_time("2024-02-01"):
            super().setUpClass()

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _assert_nav_summary_consistency(self, invoice_values: dict) -> None:
        """Assert that NAV summary totals are internally consistent with per-VAT-rate values.

        Checks all conditions validated by NAV:
        - invoiceNetAmount == sum(vatRateNetAmount)
        - invoiceVatAmount == sum(vatRateVatAmount)
        - vatRateVatAmount * exchangeRate == vatRateVatAmountHUF (per tax group)
        - invoiceVatAmount * exchangeRate == invoiceVatAmountHUF
        - invoiceGrossAmount == net + vat

        :param dict invoice_values: result of _l10n_hu_edi_get_invoice_values()
        """
        tax_summary = invoice_values["tax_summary"]
        currency_huf = self.env.ref("base.HUF")
        exchange_rate = invoice_values["exchangeRate"]
        sum_net = sum(tax_values["vatRateNetAmount"] for tax_values in tax_summary)
        sum_net_huf = sum(tax_values["vatRateNetAmountHUF"] for tax_values in tax_summary)
        sum_vat = sum(tax_values["vatRateVatAmount"] for tax_values in tax_summary)
        sum_vat_huf = sum(tax_values["vatRateVatAmountHUF"] for tax_values in tax_summary)
        self.assertEqual(invoice_values["invoiceNetAmount"], sum_net, "invoiceNetAmount must equal sum of vatRateNetAmount values")
        self.assertEqual(
            invoice_values["invoiceNetAmountHUF"], sum_net_huf, "invoiceNetAmountHUF must equal sum of vatRateNetAmountHUF values")
        self.assertEqual(
            invoice_values["invoiceVatAmount"], invoice_values["invoice"].currency_id.round(sum_vat),
            "invoiceVatAmount must equal sum of vatRateVatAmount values")
        self.assertEqual(
            invoice_values["invoiceVatAmountHUF"], currency_huf.round(sum_vat_huf),
            "invoiceVatAmountHUF must equal sum of vatRateVatAmountHUF values")
        # NAV check: vatRateVatAmount * exchangeRate == vatRateVatAmountHUF
        for tax_values in tax_summary:
            expected_vat_huf = currency_huf.round(tax_values["vatRateVatAmount"] * exchange_rate)
            self.assertEqual(
                tax_values["vatRateVatAmountHUF"], expected_vat_huf,
                "vatRateVatAmountHUF must equal vatRateVatAmount * exchangeRate")
        # NAV check: invoiceVatAmount * exchangeRate == invoiceVatAmountHUF
        expected_invoice_vat_huf = currency_huf.round(invoice_values["invoiceVatAmount"] * exchange_rate)
        self.assertEqual(
            invoice_values["invoiceVatAmountHUF"], expected_invoice_vat_huf,
            "invoiceVatAmountHUF must equal invoiceVatAmount * exchangeRate")
        expected_gross = invoice_values["invoice"].currency_id.round(sum_net + sum_vat)
        expected_gross_huf = currency_huf.round(sum_net_huf + sum_vat_huf)
        self.assertEqual(invoice_values["invoiceGrossAmount"], expected_gross, "invoiceGrossAmount must equal net + vat")
        self.assertEqual(
            invoice_values["invoiceGrossAmountHUF"], expected_gross_huf, "invoiceGrossAmountHUF must equal netHUF + vatHUF")
        self.assertEqual(
            invoice_values["invoiceVatAmount"], invoice_values["invoice"].currency_id.round(invoice_values["invoice"].amount_tax),
            "invoiceVatAmount must equal invoice.amount_tax")

    # -------------------------------------------------------------------------
    # TEST: SUMMARY CONSISTENCY WITH SIMULATED ROUNDING MISMATCH
    # -------------------------------------------------------------------------

    def test_summary_consistent_when_amount_total_differs_from_line_sum(self) -> None:
        """Verify invoice summary stays consistent even when amount_total diverges from per-line sum."""
        with freeze_time("2024-02-01"):
            invoice = self.create_invoice_simple()
            invoice.action_post()
            # simulate the real-world rounding mismatch: amount_total deviates by 1 HUF
            real_total = invoice.amount_total_in_currency_signed
            real_total_signed = invoice.amount_total_signed
            with patch.object(
                type(invoice), "amount_total_in_currency_signed",
                new_callable=lambda: property(lambda move: real_total + 1)
            ), patch.object(
                type(invoice), "amount_total_signed",
                new_callable=lambda: property(lambda move: real_total_signed + 1)
            ):
                result = invoice._l10n_hu_edi_get_invoice_values()
            self._assert_nav_summary_consistency(result)

    def test_summary_consistent_multi_line_eur_invoice(self) -> None:
        """Verify invoice summary consistency for multi-line EUR invoice with rate conversion."""
        with freeze_time("2024-02-01"):
            currency_eur = self.env.ref("base.EUR")
            invoice = self.env["account.move"].create({
                "move_type": "out_invoice",
                "journal_id": self.company_data["default_journal_sale"].id,
                "currency_id": currency_eur.id,
                "partner_id": self.partner_company.id,
                "invoice_date": self.today,
                "delivery_date": self.today,
                "invoice_line_ids": [
                    (0, 0, {
                        "product_id": self.product_a.id, "price_unit": 17.13, "quantity": 3,
                        "tax_ids": [(6, 0, self.tax_vat.ids)],
                    }),
                    (0, 0, {
                        "product_id": self.product_b.id, "price_unit": 23.47, "quantity": 7,
                        "tax_ids": [(6, 0, self.tax_vat.ids)],
                    }),
                    (0, 0, {
                        "product_id": self.product_service.id, "price_unit": 9.99, "quantity": 11,
                        "tax_ids": [(6, 0, self.tax_vat.ids)],
                    }),
                ],
            })
            invoice.action_post()
            real_total = invoice.amount_total_in_currency_signed
            real_total_signed = invoice.amount_total_signed
            with patch.object(
                type(invoice), "amount_total_in_currency_signed",
                new_callable=lambda: property(lambda move: real_total + 0.01)
            ), patch.object(
                type(invoice), "amount_total_signed",
                new_callable=lambda: property(lambda move: real_total_signed + 1)
            ):
                result = invoice._l10n_hu_edi_get_invoice_values()
            self._assert_nav_summary_consistency(result)

    def test_summary_consistent_without_mock(self) -> None:
        """Verify invoice summary consistency holds for a normal posted invoice (no mock)."""
        with freeze_time("2024-02-01"):
            invoice = self.create_invoice_simple()
            invoice.action_post()
            result = invoice._l10n_hu_edi_get_invoice_values()
            self._assert_nav_summary_consistency(result)

    def test_vat_huf_consistent_when_delivery_date_rate_differs(self) -> None:
        """Verify vatRateVatAmountHUF uses NAV rate even when accounting rate differs."""
        with freeze_time("2024-02-01"):
            currency_eur = self.env.ref("base.EUR")
            # delivery_date = yesterday (rate 377.66), invoice_date = today (rate 380.77)
            # Odoo accounting entries use invoice_date rate, but NAV XML must use delivery_date rate
            invoice = self.env["account.move"].create({
                "move_type": "out_invoice",
                "journal_id": self.company_data["default_journal_sale"].id,
                "currency_id": currency_eur.id,
                "partner_id": self.partner_company.id,
                "invoice_date": self.today,
                "delivery_date": self.yesterday,
                "invoice_line_ids": [
                    (0, 0, {
                        "product_id": self.product_a.id, "price_unit": 261.60, "quantity": 1,
                        "tax_ids": [(6, 0, self.tax_vat.ids)],
                    }),
                    (0, 0, {
                        "product_id": self.product_service.id, "price_unit": 9.00, "quantity": 1,
                        "tax_ids": [(6, 0, self.tax_vat.ids)],
                    }),
                ],
            })
            invoice.action_post()
            result = invoice._l10n_hu_edi_get_invoice_values()
            self._assert_nav_summary_consistency(result)

    def test_summary_consistent_with_multiple_tax_lines_same_tax(self) -> None:
        """Verify summary VAT remains correct when one VAT tax is split into multiple tax lines."""
        with freeze_time("2024-02-01"):
            # tax.analytic must be True, otherwise Odoo merges tax AMLs and ignores analytic grouping
            self.tax_vat.analytic = True
            analytic_plan = self.env["account.analytic.plan"].create({"name": "NAV Split Plan"})
            analytic_account_a = self.env["account.analytic.account"].create({
                "name": "NAV Split A", "plan_id": analytic_plan.id,
            })
            analytic_account_b = self.env["account.analytic.account"].create({
                "name": "NAV Split B", "plan_id": analytic_plan.id,
            })
            invoice = self.env["account.move"].create({
                "move_type": "out_invoice",
                "journal_id": self.company_data["default_journal_sale"].id,
                "currency_id": self.company_data["company"].currency_id.id,
                "partner_id": self.partner_company.id,
                "invoice_date": self.today,
                "delivery_date": self.today,
                "invoice_line_ids": [
                    (0, 0, {
                        "product_id": self.product_a.id, "price_unit": 1000.0, "quantity": 3,
                        "tax_ids": [(6, 0, self.tax_vat.ids)],
                        "analytic_distribution": {str(analytic_account_a.id): 100.0},
                    }),
                    (0, 0, {
                        "product_id": self.product_b.id, "price_unit": 2000.0, "quantity": 2,
                        "tax_ids": [(6, 0, self.tax_vat.ids)],
                        "analytic_distribution": {str(analytic_account_b.id): 100.0},
                    }),
                ],
            })
            invoice.action_post()
            tax_lines = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_vat)
            self.assertGreaterEqual(len(tax_lines), 2, "test setup must produce multiple tax lines for the same VAT tax")
            result = invoice._l10n_hu_edi_get_invoice_values()
            summary_line = next(tax_values for tax_values in result["tax_summary"] if tax_values["vat_tax"] == self.tax_vat)
            self.assertEqual(
                summary_line["vatRateVatAmount"], invoice.currency_id.round(invoice.amount_tax),
                "summary VAT amount must match posted invoice VAT when tax is split into multiple tax lines")
            self._assert_nav_summary_consistency(result)
