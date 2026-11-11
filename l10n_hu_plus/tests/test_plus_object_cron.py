# -*- coding: utf-8 -*-
# author: Online ERP
from __future__ import annotations

from odoo.tests.common import tagged

from .common import L10nHuPlusTestCommon


@tagged("l10n_hu_plus", "post_install_l10n", "post_install", "-at_install")
class TestPlusObjectCron(L10nHuPlusTestCommon):
    """Test suite for HU+ object API cron and registration log fields.

    Tests cover:
    - Object API cron record is inactive
    - run_object_api_cron is a no-op (no crash, no log growth)
    - Registration request log uses source_model_name / source_record_id
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Prepare company and log model references."""
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.Log = cls.env["l10n.hu.plus.log"]

    # -------------------------------------------------------------------------
    # TEST: OBJECT API CRON
    # -------------------------------------------------------------------------

    def test_object_api_cron_is_inactive(self) -> None:
        """Verify the HU+ object API cron stays inactive after module data load."""
        cron = self.env.ref("l10n_hu_plus.object_api_cron")
        self.assertFalse(cron.active)

    def test_run_object_api_cron_is_noop(self) -> None:
        """Verify a manual object API cron call neither crashes nor writes log rows."""
        before = self.Log.search_count([])
        result = self.env["l10n.hu.plus.object"].run_object_api_cron()
        after = self.Log.search_count([])
        self.assertTrue(result.get("skipped"))
        self.assertEqual(result.get("skip_reason"), "object_api_cron_disabled")
        self.assertEqual(result.get("company_ids"), [])
        self.assertEqual(before, after)

    # -------------------------------------------------------------------------
    # TEST: REGISTRATION LOG FIELDS
    # -------------------------------------------------------------------------

    def test_registration_request_log_uses_source_fields(self) -> None:
        """Verify registration creates a log with source_model_name and source_record_id."""
        before_ids = set(self.Log.search([]).ids)
        result = self.company.l10n_hu_plus_api_registration_request({"request_type": "get_registration"})
        log = result.get("log_record")
        self.assertTrue(log)
        self.assertNotIn(log.id, before_ids)
        self.assertEqual(log.source_model_name, "res.company")
        self.assertEqual(log.source_record_id, self.company.id)
        self.assertEqual(log.technical_name, "l10n_hu_plus.l10n_hu_plus_api_registration_request")
