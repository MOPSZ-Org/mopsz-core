# -*- coding: utf-8 -*-
# author: Online ERP
from __future__ import annotations

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import L10nHuPlusTestCommon


@tagged("l10n_hu_plus", "post_install_l10n", "post_install", "-at_install")
class TestPlusPartnerAttachment(L10nHuPlusTestCommon):
    """Test suite for HU+ partner defaults guard and attachment audit trail.

    Tests cover:
    - Foreign shared partners do not get HU onchange defaults
    - HU partners still get HU vat status defaults from fiscal position
    - Audit trail skips raw read for non-HU companies
    - HU audit trail still blocks unlink of protected attachments
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Create HU/DE partners and a HU fiscal position fixture."""
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.country_de = cls.env.ref("base.de")
        cls.country_hu = cls.env.ref("base.hu")
        cls.fiscal_position_hu = cls.env["account.fiscal.position"].create({
            "name": "HU+ Test FP",
            "company_id": cls.company.id,
            "l10n_hu_incorporation": "organization",
            "l10n_hu_vat_status": "domestic",
            "l10n_hu_trade_position": "domestic",
        })

    # -------------------------------------------------------------------------
    # TEST: PARTNER HU GUARD
    # -------------------------------------------------------------------------

    def test_foreign_shared_partner_skips_hu_onchange_defaults(self) -> None:
        """Verify shared DE partners do not receive HU vat fields via onchange."""
        partner = self.env["res.partner"].create({
            "name": "Shared DE Partner",
            "country_id": self.country_de.id,
            "company_id": False,
        })
        self.assertFalse(partner._l10n_hu_plus_partner_needs_hu_defaults())
        partner = partner.with_company(self.company)
        partner.property_account_position_id = self.fiscal_position_hu
        partner._onchange_l10n_hu_plus_vat_status()
        self.assertFalse(partner.l10n_hu_vat_status)
        self.assertFalse(partner.l10n_hu_incorporation)

    def test_hu_partner_applies_hu_onchange_defaults(self) -> None:
        """Verify HU partners still get vat status defaults from fiscal position."""
        partner = self.env["res.partner"].create({
            "name": "HU Partner",
            "country_id": self.country_hu.id,
            "company_id": self.company.id,
        }).with_company(self.company)
        self.assertTrue(partner._l10n_hu_plus_partner_needs_hu_defaults())
        partner.property_account_position_id = self.fiscal_position_hu
        partner._onchange_l10n_hu_plus_vat_status()
        self.assertEqual(partner.l10n_hu_vat_status, "domestic")
        self.assertEqual(partner.l10n_hu_incorporation, "organization")

    def test_property_account_position_tracking_not_forced_by_hu_plus(self) -> None:
        """Verify HU+ no longer forces tracking=True on fiscal position."""
        field = self.env["res.partner"]._fields["property_account_position_id"]
        # Odoo 19 Field omits the attribute when tracking is unset
        self.assertFalse(getattr(field, "tracking", False))

    # -------------------------------------------------------------------------
    # TEST: ATTACHMENT AUDIT TRAIL ORDER
    # -------------------------------------------------------------------------

    def test_audit_trail_skips_raw_for_non_hu_company(self) -> None:
        """Verify non-HU companies never enter the HU audit raw/mimetype path."""
        other = self.setup_other_company()
        other_company = other["company"]
        other_company.write({
            "account_fiscal_country_id": self.country_de.id,
            "restrictive_audit_trail": True,
        })
        move = self.env["account.move"].with_company(other_company).create({
            "move_type": "entry",
            "company_id": other_company.id,
            "journal_id": other["default_journal_misc"].id,
        })
        attachment = self.env["ir.attachment"].create({
            "name": "foreign.pdf",
            "res_model": "account.move",
            "res_id": move.id,
            "company_id": other_company.id,
            "raw": b"%PDF-1.4 foreign",
            "mimetype": "application/pdf",
        })
        # Must not raise for foreign fiscal country
        attachment._l10n_hu_plus_except_audit_trail()

    def test_audit_trail_blocks_unlink_for_protected_hu_move(self) -> None:
        """Verify HU restrictive audit trail still blocks deletion after guards."""
        self.company.restrictive_audit_trail = True
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "journal_id": self.journal_sale.id,
            "partner_id": self.partner_company.id,
            "invoice_date": "2024-06-15",
            "invoice_line_ids": [(0, 0, {
                "name": "line",
                "quantity": 1,
                "price_unit": 100,
            })],
        })
        invoice.action_post()
        invoice.checked = True
        attachment = self.env["ir.attachment"].create({
            "name": "hu-invoice.pdf",
            "res_model": "account.move",
            "res_id": invoice.id,
            "company_id": self.company.id,
            "raw": b"%PDF-1.4 hu",
            "mimetype": "application/pdf",
        })
        with self.assertRaises(UserError):
            attachment.unlink()
