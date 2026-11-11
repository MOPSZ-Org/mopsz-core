# -*- coding: utf-8 -*-
# author: Online ERP
from __future__ import annotations

from unittest.mock import MagicMock, patch

from odoo.tests.common import tagged

from .common import L10nHuPlusTestCommon


@tagged("l10n_hu_plus", "post_install_l10n", "post_install", "-at_install")
class TestPlusHttpUi(L10nHuPlusTestCommon):
    """Test suite for HU+ HTTP timeout, invoice search and debug removal.

    Tests cover:
    - requests calls use timeout=(5, 30)
    - invoice search keeps core name filter_domain (no proforma injection)
    - separate Proforma search field is present
    - wizard action_debug is removed
    """

    # -------------------------------------------------------------------------
    # TEST: HTTP TIMEOUT
    # -------------------------------------------------------------------------

    def test_api_request_response_uses_http_timeout(self) -> None:
        """Verify api_request_response passes timeout=(5, 30) to requests.get."""
        log = self.env["l10n.hu.plus.log"].create({
            "app_name": "l10n_hu_plus",
            "company": self.company_data["company"].id,
            "direction": "outgoing",
            "level": "info",
            "log_type": "test",
            "name": "test http timeout",
            "technical_name": "l10n_hu_plus.tests.test_plus_http_ui",
        })
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"payload": {}}}
        with patch("odoo.addons.l10n_hu_plus.models.log.requests.get", return_value=mock_response) as mock_get:
            log.api_request_response({
                "api_key": "test-key",
                "log": log,
                "request_data": {"payload": {}},
                "request_method": "GET",
                "request_type": "get_registration",
                "request_url": "https://example.test/registration",
            })
            mock_get.assert_called_once()
            self.assertEqual(mock_get.call_args.kwargs["timeout"], (5, 30))

    # -------------------------------------------------------------------------
    # TEST: INVOICE SEARCH
    # -------------------------------------------------------------------------

    def test_invoice_search_keeps_core_name_filter_domain(self) -> None:
        """Verify HU+ does not replace the core invoice name filter_domain."""
        view = self.env.ref("account.view_account_invoice_filter")
        arch = self.env["account.move"].get_view(view.id, "search")["arch"]
        self.assertIn('name="l10n_hu_proforma_name"', arch)
        # Core Invoice name field is self-closing (... filter_domain="..." />)
        name_field_chunk = arch.split('string="Invoice"', 1)[1].split("/>", 1)[0]
        self.assertIn("('name', 'ilike', self)", name_field_chunk)
        self.assertIn("filter_domain", name_field_chunk)
        self.assertNotIn("l10n_hu_proforma_name", name_field_chunk)

    def test_invoice_search_proforma_field_has_own_filter_domain(self) -> None:
        """Verify the dedicated Proforma search field filters only proforma name."""
        view = self.env.ref("l10n_hu_plus.view_account_invoice_filter_inherit")
        arch = view.arch_db
        self.assertIn('name="l10n_hu_proforma_name"', arch)
        self.assertIn("('l10n_hu_proforma_name', 'ilike', self)", arch)
        # Inherit must not rewrite core name filter_domain via attributes xpath
        self.assertNotIn('position="attributes"', arch)

    # -------------------------------------------------------------------------
    # TEST: DEBUG REMOVED
    # -------------------------------------------------------------------------

    def test_wizard_has_no_action_debug(self) -> None:
        """Verify debug action that dumped invoice payload is gone."""
        Wizard = self.env["l10n.hu.plus.wizard"]
        self.assertFalse(hasattr(Wizard, "action_debug"))
        view = self.env.ref("l10n_hu_plus.wizard_view_form")
        self.assertNotIn('name="action_debug"', view.arch_db)
