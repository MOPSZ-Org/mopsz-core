# -*- coding: utf-8 -*-
# author: Online ERP
from __future__ import annotations

from unittest.mock import MagicMock, patch

from odoo.exceptions import AccessError
from odoo.tests.common import new_test_user, tagged

from .common import L10nHuPlusTestCommon


@tagged("l10n_hu_plus", "post_install_l10n", "post_install", "-at_install")
class TestLogSecrets(L10nHuPlusTestCommon):
    """Test suite for HU+ log secret redaction and technical_data ACL.

    Tests cover:
    - HTTP header redaction helper
    - Nested technical_data scrubbing
    - api_request_response never persists X-Api-Key
    - Existing log scrubber removes leaked keys
    - technical_data field restricted to Settings (group_system)
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Create a HU+ log fixture and internal / Settings test users."""
        super().setUpClass()
        cls.log_model = cls.env["l10n.hu.plus.log"]
        cls.secret_api_key = "super-secret-api-key-value"
        cls.log = cls.log_model.create({
            "app_name": "l10n_hu_plus",
            "company": cls.company_data["company"].id,
            "direction": "outgoing",
            "level": "info",
            "log_type": "test",
            "name": "test log secrets",
            "technical_name": "l10n_hu_plus.tests.test_log_secrets",
        })
        cls.internal_user = new_test_user(
            cls.env,
            login="hu_plus_log_internal",
            groups="base.group_user",
        )
        cls.system_user = new_test_user(
            cls.env,
            login="hu_plus_log_system",
            groups="base.group_user,base.group_system",
        )

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _leaked_technical_data(self) -> dict:
        """Build a technical_data payload that still contains secrets.

        :returns: nested dict with X-Api-Key and api_key values
        """
        return {
            "request_info": {
                "request_headers": {
                    "accept": "application/json",
                    "Content-Type": "application/json",
                    "X-Api-Key": self.secret_api_key,
                },
                "request_path": "https://example.test/api",
            },
            "nested": {"api_key": self.secret_api_key},
        }

    # -------------------------------------------------------------------------
    # TEST: REDACT / SCRUB HELPERS
    # -------------------------------------------------------------------------

    def test_redact_http_headers_masks_api_key(self) -> None:
        """Verify X-Api-Key and Authorization are replaced, other headers kept."""
        redacted = self.log_model._l10n_hu_plus_redact_http_headers({
            "accept": "application/json",
            "X-Api-Key": self.secret_api_key,
            "Authorization": "Bearer token",
        })
        self.assertEqual(redacted["accept"], "application/json")
        self.assertEqual(redacted["X-Api-Key"], "***")
        self.assertEqual(redacted["Authorization"], "***")

    def test_scrub_secrets_from_nested_technical_data(self) -> None:
        """Verify nested request_headers and api_key keys are scrubbed."""
        scrubbed = self.log_model._l10n_hu_plus_scrub_secrets_from_data(self._leaked_technical_data())
        self.assertEqual(scrubbed["request_info"]["request_headers"]["X-Api-Key"], "***")
        self.assertEqual(scrubbed["request_info"]["request_headers"]["accept"], "application/json")
        self.assertEqual(scrubbed["nested"]["api_key"], "***")
        self.assertNotIn(self.secret_api_key, str(scrubbed))

    # -------------------------------------------------------------------------
    # TEST: api_request_response LOGGING
    # -------------------------------------------------------------------------

    def test_api_request_response_does_not_store_api_key(self) -> None:
        """Verify api_request_response persists redacted headers only."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"payload": {}}}
        with patch("odoo.addons.l10n_hu_plus.models.log.requests.get", return_value=mock_response) as mock_get:
            self.log.api_request_response({
                "api_key": self.secret_api_key,
                "log": self.log,
                "request_data": {"payload": {}},
                "request_method": "GET",
                "request_type": "get_registration",
                "request_url": "https://example.test/registration",
            })
            mock_get.assert_called_once()
            sent_headers = mock_get.call_args.kwargs["headers"]
            self.assertEqual(sent_headers["X-Api-Key"], self.secret_api_key)

        self.log.invalidate_recordset(["technical_data"])
        technical_data = self.log.sudo().technical_data
        self.assertTrue(technical_data)
        stored_headers = technical_data["request_info"]["request_headers"]
        self.assertEqual(stored_headers["X-Api-Key"], "***")
        self.assertNotIn(self.secret_api_key, str(technical_data))

    # -------------------------------------------------------------------------
    # TEST: EXISTING ROW SCRUBBER
    # -------------------------------------------------------------------------

    def test_scrub_existing_log_technical_data(self) -> None:
        """Verify l10n_hu_plus_scrub_log_secrets cleans historical leaks."""
        # bypass write scrubber to simulate pre-fix rows still containing secrets
        self.log.sudo().with_context(l10n_hu_plus_skip_secret_scrub=True).write({
            "technical_data": self._leaked_technical_data(),
        })
        self.log.invalidate_recordset(["technical_data"])
        self.assertIn(self.secret_api_key, str(self.log.sudo().technical_data))
        updated = self.log_model.l10n_hu_plus_scrub_log_secrets()
        self.assertGreaterEqual(updated, 1)
        self.log.invalidate_recordset(["technical_data"])
        technical_data = self.log.sudo().technical_data
        self.assertEqual(technical_data["request_info"]["request_headers"]["X-Api-Key"], "***")
        self.assertEqual(technical_data["nested"]["api_key"], "***")
        self.assertNotIn(self.secret_api_key, str(technical_data))

    def test_write_scrubs_technical_data_automatically(self) -> None:
        """Verify normal write redacts secrets without an explicit scrub call."""
        self.log.sudo().write({"technical_data": self._leaked_technical_data()})
        self.log.invalidate_recordset(["technical_data"])
        technical_data = self.log.sudo().technical_data
        self.assertEqual(technical_data["request_info"]["request_headers"]["X-Api-Key"], "***")
        self.assertNotIn(self.secret_api_key, str(technical_data))

    # -------------------------------------------------------------------------
    # TEST: FIELD GROUPS
    # -------------------------------------------------------------------------

    def test_technical_data_hidden_from_internal_user(self) -> None:
        """Verify internal users cannot read log technical_data without Settings."""
        self.log.sudo().write({"technical_data": {"safe": True, "nested": {"api_key": self.secret_api_key}}})
        log_as_internal = self.log.with_user(self.internal_user)
        with self.assertRaises(AccessError):
            # force ACL check on the restricted Json field
            _ = log_as_internal.technical_data

    def test_technical_data_readable_by_system_user(self) -> None:
        """Verify Settings users can still read log technical_data."""
        payload = {"safe": True}
        self.log.sudo().write({"technical_data": payload})
        log_as_system = self.log.with_user(self.system_user)
        self.assertEqual(log_as_system.technical_data, payload)

    def test_company_technical_data_hidden_from_internal_user(self) -> None:
        """Verify company HU+ technical_data requires Settings group."""
        company = self.company_data["company"]
        company.sudo().write({
            "l10n_hu_plus_technical_data": {"hu_plus_api": {"api_key": self.secret_api_key}},
        })
        company_as_internal = company.with_user(self.internal_user)
        with self.assertRaises(AccessError):
            _ = company_as_internal.l10n_hu_plus_technical_data
