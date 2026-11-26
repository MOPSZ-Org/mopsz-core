# -*- coding: utf-8 -*-
# 1 : imports of python lib
import re

# 2 : imports of odoo
from odoo import _, api, exceptions, fields, models  # alphabetically ordered

# 3 : imports from odoo modules

# 4 : variable declarations


# Class
class L10nHuPlusResPartner(models.Model):
    # Private attributes
    _inherit = 'res.partner'

    # Default methods

    # Field declarations
    ## HU+
    l10n_hu_financial_representative = fields.Many2one(
        comodel_name='res.partner',
        copy=False,
        string="HU Financial Representative",
    )
    l10n_hu_plus_visible = fields.Boolean(
        compute='_compute_l10n_hu_plus_visible',
        string="HU+ Visible",
    )
    l10n_hu_self_billing = fields.Boolean(
        copy=False,
        default=False,
        string="HU Self Billing",
    )
    l10n_hu_vpid = fields.Char(
        copy=False,
        string="HU VPID",
    )
    ## FELIR
    l10n_hu_felir = fields.Char(
        copy=False,
        string="HU FELIR",
    )
    ## FISCAL POSITION
    l10n_hu_incorporation = fields.Selection(
        copy=False,
        index=True,
        selection=[
            ('organization', "Organization"),
            ('self_employed', "Self Employed"),
            ('taxable_person', "Taxable Person"),
        ],
        string="HU Taxpayer Type",
    )
    l10n_hu_tax_regime = fields.Selection(
        copy=False,
        selection=[
            ('ie', 'Individual Exemption'),
            ('ca', 'Cash Accounting'),
            ('sb', 'Small Business'),
        ],
        string="HU Tax Regime",
    )
    l10n_hu_trade_position = fields.Selection(
        copy=False,
        index=True,
        selection=[
            ('domestic', "Domestic"),
            ('eu', "EU"),
            ('other', "Other"),
        ],
        string="HU Trade Position",
    )
    l10n_hu_vat_status = fields.Selection(
        copy=False,
        index=True,
        selection=[
            ('domestic', "Domestic"),
            ('private_person', "Private Person"),
            ('other', "Other"),
        ],
        string="HU VAT Status",
    )

    # Compute and search fields, in the same order of field declarations
    @api.depends('country_id', 'commercial_partner_id', 'parent_id')
    def _compute_l10n_hu_plus_visible(self):
        for record in self:
            record.l10n_hu_plus_visible = record.l10n_hu_plus_get_visible()

    # Constraints and onchanges
    @api.onchange('country_id', 'is_company', 'parent_id', 'property_account_position_id')
    def _onchange_l10n_hu_plus_vat_status(self):
        if not self._l10n_hu_plus_partner_needs_hu_defaults():
            return
        vat_status_result = self.l10n_hu_plus_get_vat_status()
        self.l10n_hu_incorporation = vat_status_result.get('l10n_hu_incorporation', None)
        self.l10n_hu_vat_status = vat_status_result.get('l10n_hu_vat_status', None)

    # CRUD methods (and name_get, name_search, ...) overrides

    # Action methods
    def action_l10n_hu_plus_view_documentation(self):
        """ View HU+ documentation """
        # Make sure there is one record in self
        self.ensure_one()

        # Return
        return {
            'target': 'new',
            'type': 'ir.actions.act_url',
            'url': 'https://hungarodo.atlassian.net/wiki/spaces/ODOOHU',
        }

    def action_l10n_hu_plus_set_vat_status(self):
        # Manage only one record
        self.ensure_one()

        # Get data
        vat_status_result = self.l10n_hu_plus_get_vat_status()

        # Set data when possible
        if len(vat_status_result.get('error_list')) > 0:
            raise exceptions.UserError(str(vat_status_result['error_list']))
        else:
            self.write({
                'l10n_hu_incorporation': vat_status_result.get('l10n_hu_incorporation', None),
                'l10n_hu_tax_regime': vat_status_result.get('l10n_hu_tax_regime', None),
                'l10n_hu_trade_position': vat_status_result.get('l10n_hu_trade_position', None),
                'l10n_hu_vat_status': vat_status_result.get('l10n_hu_vat_status', None),
            })
            return

    # Business methods
    ## HU+
    def _l10n_hu_plus_partner_needs_hu_defaults(self):
        """Return whether HU fiscal defaults may be applied on this partner.

        Shared (company-less) foreign partners must not receive HU vat/incorporation
        defaults just because they are visible in a multi-company database.

        :returns: True when HU defaults are appropriate
        :rtype: bool
        """
        self.ensure_one()
        if self.country_id and self.country_id.code == "HU":
            return True
        if self.parent_id and self.parent_id.country_id and self.parent_id.country_id.code == "HU":
            return True
        if (self.commercial_partner_id and self.commercial_partner_id != self and self.commercial_partner_id.country_id
                and self.commercial_partner_id.country_id.code == "HU"):
            return True
        company = self.company_id or self.env.company
        company_is_hu = bool(
            (company.account_fiscal_country_id and company.account_fiscal_country_id.code == "HU")
            or (company.country_id and company.country_id.code == "HU")
        )
        if company_is_hu and (not self.country_id or self.country_id.code == "HU"):
            return True
        return False

    @api.model
    def l10n_hu_plus_get_vat_status(self):
        """ Get HU+ VAT status data

        :return: dictionary
        """
        # Initialize variables
        debug_list = []
        error_list = []
        info_list = []
        l10n_hu_incorporation = self.l10n_hu_incorporation
        l10n_hu_tax_regime = self.l10n_hu_tax_regime
        l10n_hu_trade_position = self.l10n_hu_trade_position
        l10n_hu_vat_status = self.l10n_hu_vat_status
        result = {}
        warning_list = []

        # Check for fiscal position
        if self.parent_id and self.commercial_partner_id != self:
            has_commercial_partner_text = _("Partner belongs to this commercial partner")
            has_commercial_partner_text += ": " + self.commercial_partner_id.display_name
            info_list.append(has_commercial_partner_text)
        elif not self.parent_id and self.commercial_partner_id == self and self.property_account_position_id:
            has_fiscal_position_text = _("Fiscal position set")
            has_fiscal_position_text += ": " + self.property_account_position_id.display_name
            info_list.append(has_fiscal_position_text)
        elif not self.parent_id and self.commercial_partner_id == self and not self.property_account_position_id:
            no_fiscal_position_text = _("Fiscal position is empty")
            no_fiscal_position_text += ": " + str(self.display_name)
            error_list.append(no_fiscal_position_text)
        else:
            pass

        # Consider fiscal position
        if not self.parent_id and self.property_account_position_id:
            if self.property_account_position_id.l10n_hu_incorporation:
                l10n_hu_incorporation = self.property_account_position_id.l10n_hu_incorporation
            elif self.l10n_hu_incorporation:
                l10n_hu_incorporation = self.l10n_hu_incorporation
            else:
                pass

            if self.property_account_position_id.l10n_hu_tax_regime:
                l10n_hu_tax_regime = self.property_account_position_id.l10n_hu_tax_regime
            elif self.l10n_hu_tax_regime:
                l10n_hu_tax_regime = self.l10n_hu_tax_regime
            else:
                pass

            if self.property_account_position_id.l10n_hu_trade_position:
                l10n_hu_trade_position = self.property_account_position_id.l10n_hu_trade_position
            elif self.l10n_hu_trade_position:
                l10n_hu_trade_position = self.l10n_hu_trade_position
            else:
                pass

            if self.property_account_position_id.l10n_hu_vat_status:
                l10n_hu_vat_status = self.property_account_position_id.l10n_hu_vat_status
            elif self.l10n_hu_vat_status:
                l10n_hu_vat_status = self.l10n_hu_vat_status
            else:
                pass
        else:
            pass

        # Update result
        result.update({
            'debug_list': debug_list,
            'error_list': error_list,
            'info_list': info_list,
            'l10n_hu_incorporation': l10n_hu_incorporation,
            'l10n_hu_tax_regime': l10n_hu_tax_regime,
            'l10n_hu_trade_position': l10n_hu_trade_position,
            'l10n_hu_vat_status': l10n_hu_vat_status,
            'warning_list': warning_list,
        })

        # Return result
        return result

    @api.model
    def l10n_hu_plus_get_visible(self):
        """ Determine if HU+ should be visible

        May be overridden by super

        :return: boolean
        """
        # Initialize variables
        result = False

        if self.country_id and self.country_id.code == 'HU':
            result = True
        elif self.parent_id and self.parent_id.country_id and self.parent_id.country_id.code == 'HU':
            result = True
        elif self.company_id and self.company_id.country_id and self.company_id.country_id.code == 'HU':
            result = True
        elif not self.company_id:
            result = True
        else:
            pass

        # Return result
        return result

    @api.model
    def l10n_hu_plus_check_crn(self, crn=None):
        """ Validate hungarian company registration number format """
        if crn and isinstance(crn, str):
            pass
        elif not crn and self.l10n_hu_crn:
            crn = self.l10n_hu_crn
        else:
            return False

        if crn:
            pattern = re.compile("(0[1-9]|1[0-9]|20)-(0[1-9]|1[0-9]|2[0-3])-[0-9]{6}")
            match = pattern.match(crn)

            if match and match.start() == 0 and match.end() == 12 and len(crn) == 12:
                return True
            else:
                return False
        else:
            return False
