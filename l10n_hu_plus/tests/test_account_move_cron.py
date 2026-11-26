# -*- coding: utf-8 -*-
# author: Online ERP
from __future__ import annotations

from odoo.tests.common import tagged

from .common import L10nHuPlusTestCommon


@tagged("l10n_hu_plus", "post_install_l10n", "post_install", "-at_install")
class TestAccountMoveCron(L10nHuPlusTestCommon):
    """Test suite for HU+ account move cron no-op logging.

    Tests cover:
    - No log row when a HU company has no eligible HU+ journals
    - Log row when at least one eligible journal exists
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Disable cron journals by default; tests enable them when needed."""
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.Log = cls.env["l10n.hu.plus.log"]
        # ensure fiscal country is HU (L10nHuEdi fixture) and sale journal is not cron-eligible by default here
        cls.journal_sale.write({
            "l10n_hu_plus_enabled": False,
            "l10n_hu_cron_batch": 0,
        })
        cls.company_data["default_journal_purchase"].write({
            "l10n_hu_plus_enabled": False,
            "l10n_hu_cron_batch": 0,
        })

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _cron_log_domain(self, company) -> list:
        """Build domain for account move cron log rows of a company.

        :param company: res.company record
        :returns: search domain
        """
        return [
            ("company", "=", company.id),
            ("technical_name", "=", "l10n_hu_plus.l10n_hu_run_account_move_cron"),
        ]

    # -------------------------------------------------------------------------
    # TEST: NO-OP SKIP
    # -------------------------------------------------------------------------

    def test_cron_skips_log_when_no_eligible_journals(self) -> None:
        """Verify HU companies without eligible journals do not get a cron log."""
        before = self.Log.search_count(self._cron_log_domain(self.company))
        result = self.env["account.move"].l10n_hu_run_account_move_cron()
        after = self.Log.search_count(self._cron_log_domain(self.company))
        self.assertEqual(before, after)
        self.assertNotIn(self.company.id, result.get("company_ids", []))

    # -------------------------------------------------------------------------
    # TEST: LOG WHEN WORK POSSIBLE
    # -------------------------------------------------------------------------

    def test_cron_creates_log_when_eligible_journal_exists(self) -> None:
        """Verify a cron log is created when at least one eligible journal exists."""
        self.journal_sale.write({
            "l10n_hu_plus_enabled": True,
            "l10n_hu_cron_batch": 10,
            "l10n_hu_edi_sending": "manual",
        })
        before = self.Log.search_count(self._cron_log_domain(self.company))
        result = self.env["account.move"].l10n_hu_run_account_move_cron()
        after = self.Log.search_count(self._cron_log_domain(self.company))
        self.assertEqual(after, before + 1)
        self.assertIn(self.company.id, result["company_ids"])
        self.assertTrue(result["log_ids"])
