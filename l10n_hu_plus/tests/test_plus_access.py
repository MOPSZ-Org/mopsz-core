# -*- coding: utf-8 -*-
# author: Online ERP
from __future__ import annotations

from odoo.exceptions import AccessError
from odoo.tests.common import new_test_user, tagged

from .common import L10nHuPlusTestCommon


@tagged("l10n_hu_plus", "post_install_l10n", "post_install", "-at_install")
class TestPlusAccess(L10nHuPlusTestCommon):
    """Test suite for HU+ portal ACL removal and company wizard context.

    Tests cover:
    - Portal users cannot read HU+ log / object / tag
    - source_display_name respects ACL (no unrestricted sudo)
    - Company API / configuration wizards pass default_company
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Create HU+ log fixture and portal / internal users."""
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.log = cls.env["l10n.hu.plus.log"].create({
            "app_name": "l10n_hu_plus",
            "company": cls.company.id,
            "direction": "outgoing",
            "level": "info",
            "log_type": "test",
            "name": "test plus access",
            "source_model_name": "res.partner",
            "source_record_id": cls.partner_company.id,
            "technical_name": "l10n_hu_plus.tests.test_plus_access",
        })
        cls.portal_user = new_test_user(
            cls.env,
            login="hu_plus_portal",
            groups="base.group_portal",
        )
        cls.internal_user = new_test_user(
            cls.env,
            login="hu_plus_internal_access",
            groups="base.group_user",
        )
        cls.manager_user = new_test_user(
            cls.env,
            login="hu_plus_manager_access",
            groups="base.group_user,l10n_hu_plus.manager_group,base.group_system",
        )

    # -------------------------------------------------------------------------
    # TEST: PORTAL ACL
    # -------------------------------------------------------------------------

    def test_portal_user_cannot_read_log(self) -> None:
        """Verify portal users no longer have READ on l10n.hu.plus.log."""
        log_as_portal = self.env["l10n.hu.plus.log"].with_user(self.portal_user)
        with self.assertRaises(AccessError):
            log_as_portal.search([("id", "=", self.log.id)])

    def test_portal_user_cannot_read_object(self) -> None:
        """Verify portal users no longer have READ on l10n.hu.plus.object."""
        Object = self.env["l10n.hu.plus.object"].with_user(self.portal_user)
        with self.assertRaises(AccessError):
            Object.search([])

    def test_portal_user_cannot_read_tag(self) -> None:
        """Verify portal users no longer have READ on l10n.hu.plus.tag."""
        Tag = self.env["l10n.hu.plus.tag"].with_user(self.portal_user)
        with self.assertRaises(AccessError):
            Tag.search([])

    # -------------------------------------------------------------------------
    # TEST: source_display_name ACL
    # -------------------------------------------------------------------------

    def test_source_display_name_visible_with_access(self) -> None:
        """Verify source_display_name resolves when the user can read the source."""
        self.log.write({
            "source_model_name": "res.partner",
            "source_record_id": self.partner_company.id,
        })
        self.log.invalidate_recordset(["source_display_name"])
        log_as_internal = self.log.with_user(self.internal_user)
        self.assertEqual(log_as_internal.source_display_name, self.partner_company.display_name)

    def test_source_display_name_hidden_without_access(self) -> None:
        """Verify source_display_name stays empty when the source is inaccessible."""
        other_company_data = self.setup_other_company()
        other_company = other_company_data["company"]
        other_move = self.env["account.move"].with_company(other_company).create({
            "move_type": "entry",
            "company_id": other_company.id,
            "journal_id": other_company_data["default_journal_misc"].id,
            "ref": "HU+ foreign company entry",
        })
        # keep the internal user on the main company only
        self.internal_user.write({"company_ids": [(6, 0, [self.company.id])], "company_id": self.company.id})
        log = self.env["l10n.hu.plus.log"].create({
            "app_name": "l10n_hu_plus",
            "company": self.company.id,
            "direction": "internal",
            "level": "info",
            "log_type": "test",
            "name": "test source acl hidden",
            "source_model_name": "account.move",
            "source_record_id": other_move.id,
            "technical_name": "l10n_hu_plus.tests.test_plus_access_hidden",
        })
        log.invalidate_recordset(["source_display_name"])
        log_as_internal = log.with_user(self.internal_user).with_company(self.company)
        self.assertFalse(
            log_as_internal.source_display_name,
            "Unprivileged users must not resolve source display names via sudo",
        )
        # admin/sudo path can still resolve the foreign move name
        log.invalidate_recordset(["source_display_name"])
        self.assertTrue(log.sudo().source_display_name)

    # -------------------------------------------------------------------------
    # TEST: default_company ON WIZARDS
    # -------------------------------------------------------------------------

    def test_api_create_registration_passes_default_company(self) -> None:
        """Verify create registration wizard context pins the opened company."""
        company = self.company.with_user(self.manager_user)
        company.sudo().write({"l10n_hu_plus_api_enabled": True})
        action = company.action_l10n_hu_plus_api_create_registration()
        self.assertEqual(action["context"]["default_company"], company.id)

    def test_configuration_wizard_passes_default_company(self) -> None:
        """Verify configuration wizard context pins the opened company."""
        company = self.company.with_user(self.manager_user)
        action = company.action_l10n_hu_plus_apply_configuration()
        self.assertEqual(action["context"]["default_company"], company.id)
