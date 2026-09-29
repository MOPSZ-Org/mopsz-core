# -*- coding: utf-8 -*-
# 1 : imports of python lib
from collections import defaultdict
import base64
import copy
import datetime
import json
from lxml import etree

# 2 : imports of odoo
from odoo import _, api, exceptions, fields, models, tools  # alphabetically ordered
from odoo.tools import formatLang

# 3 : imports from odoo modules
from odoo.addons.l10n_hu_edi.models.l10n_hu_edi_connection import format_bool, L10nHuEdiConnection, L10nHuEdiConnectionError

# 4 : variable declarations


# Class
class L10nHuPlusAccountMove(models.Model):
    # Private attributes
    _inherit = 'account.move'

    L10N_HU_DOCUMENT_HUF_ZERO_CLAMP = 0.10

    # Default methods

    # Field declarations
    ## ODOO
    invoice_pdf_report_id = fields.Many2one(
        tracking=True,
    )
    ## CASH ACCOUNTING
    l10n_hu_cash_accounting = fields.Boolean(
        copy=False,
        default=False,
        index=True,
        string="HU Cash Accounting",
    )
    ## CURRENCY
    l10n_hu_company_currency_name = fields.Char(
        related='company_currency_id.name',
        string="HU Company Currency Name",
    )
    l10n_hu_currency_name = fields.Char(
        related='currency_id.name',
        string="HU Currency Name",
    )
    l10n_hu_huf_currency = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_l10n_hu_currency',
        string="HUF Currency",
    )
    l10n_hu_huf_rate = fields.Float(
        compute='_compute_l10n_hu_huf_rate',
        store=True,
        readonly=False,
        copy=False,
        string="HUF Rate",
    )
    l10n_hu_invoice_currency_rate_date = fields.Date(
        compute='_compute_l10n_hu_currency',
        string="HU Currency Date",
    )
    l10n_hu_invoice_currency_rate_inverse = fields.Float(
        compute='_compute_l10n_hu_currency',
        string="HU Invoice Currency Rate Inverse",
    )
    ## DELIVERY PERIOD
    l10n_hu_delivery_period_end = fields.Date(
        copy=False,
        string="HU Delivery Period End",
        tracking=True,
    )
    l10n_hu_delivery_period_start = fields.Date(
        copy=False,
        string="HU Delivery Period Start",
        tracking=True,
    )
    l10n_hu_delivery_period_summary = fields.Text(
        compute='_compute_l10n_hu_delivery_period_text',
        string="HU Delivery Period Summary",
    )
    ## DOCUMENT
    l10n_hu_document_gross_huf = fields.Monetary(
        compute='_compute_l10n_hu_document',
        currency_field='l10n_hu_huf_currency',
        help="Gross amount in HUF of the invoice document",
        string="HU Document Gross HUF",
    )
    l10n_hu_document_net_huf = fields.Monetary(
        compute='_compute_l10n_hu_document',
        currency_field='l10n_hu_huf_currency',
        help="Net amount in HUF of the invoice document",
        string="HU Document Net HUF",
    )
    l10n_hu_document_rate = fields.Float(
        compute='_compute_l10n_hu_document',
        help="Currency rate of the invoice document",
        string="HU Document Rate",
    )
    l10n_hu_document_type = fields.Many2one(
        comodel_name='l10n.hu.plus.tag',
        domain=[('tag_type', '=', 'document_type')],
        index=True,
        string="HU Document Type",
        tracking=True,
    )
    l10n_hu_document_type_code = fields.Char(
        related='l10n_hu_document_type.code',
        string="HU Document Type Code",
    )
    l10n_hu_document_type_technical_name = fields.Char(
        related='l10n_hu_document_type.technical_name',
        string="HU Document Type Technical Name",
    )
    l10n_hu_document_vat_huf = fields.Monetary(
        copy=False,
        currency_field='l10n_hu_huf_currency',
        help="VAT amount in HUF as indicated on the invoice document",
        string="HU Document VAT HUF",
    )
    ## HU+
    l10n_hu_plus_notes = fields.Char(
        copy=False,
        index=True,
        string="HU+ Notes",
    )
    l10n_hu_plus_status = fields.Selection(
        copy=False,
        selection=[
            ('ok', "Ok"),
            ('closed', "Closed"),
            ('warning', "Warning"),
            ('error', "Error"),
            ('other', "Other"),
        ],
        string="HU+ Status",
    )
    l10n_hu_plus_tag = fields.Many2many(
        column1='account_move',
        column2='tag',
        comodel_name='l10n.hu.plus.tag',
        domain=[('tag_type', 'in', ['account_move', 'general'])],
        index=True,
        relation='l10n_hu_plus_tag_account_move_rel',
        string="HU+ Tag",
    )
    ## JOURNAL
    l10n_hu_banner_enabled = fields.Boolean(
        related='journal_id.l10n_hu_banner_enabled',
        string="HU Banner",
    )
    l10n_hu_journal_type = fields.Selection(
        related='journal_id.type',
        string="HU Journal Type",
    )
    l10n_hu_plus_enabled = fields.Boolean(
        related='journal_id.l10n_hu_plus_enabled',
        string="HU+ Enabled",
    )
    ## ORIGINAL
    l10n_hu_original_invoice_number = fields.Char(
        copy=False,
        string="HU Original Invoice Number",
        tracking=True,
    )
    ## PARTNER
    l10n_hu_company_partner = fields.Many2one(
        related='company_id.partner_id',
        string="HU Company Partner",
    )
    l10n_hu_fiscal_representative = fields.Many2one(
        comodel_name='res.partner',
        index=True,
        string="HU Fiscal Representative",
    )
    l10n_hu_fiscal_representative_bank_account = fields.Many2one(
        comodel_name='res.partner.bank',
        index=True,
        string="HU Fiscal Representative Bank Account",
    )
    l10n_hu_partner_country = fields.Many2one(
        comodel_name='res.country',
        related='partner_id.country_id',
        index=True,
        store=True,
        string="HU Partner Country",
    )
    l10n_hu_trade_position = fields.Selection(
        related='fiscal_position_id.l10n_hu_trade_position',
        index=True,
        store=True,
        string="HU Trade Position",
    )
    ## PROFORMA
    l10n_hu_proforma_date = fields.Date(
        copy=False,
        help="The sending date of the proforma document",
        string="HU Proforma Date",
        tracking=True,
    )
    l10n_hu_proforma_name = fields.Char(
        copy=False,
        string="HU Proforma Name",
        tracking=True,
    )
    l10n_hu_proforma_sequence = fields.Many2one(
        related='journal_id.l10n_hu_proforma_sequence',
        string="HU Proforma Sequence",
    )
    ## VAT
    l10n_hu_vat_date = fields.Date(
        copy=False,
        index=True,
        string="HU VAT Date",
        tracking=True,
    )
    l10n_hu_vat_status = fields.Selection(
        copy=False,
        index=True,
        selection=[
            ('to_declare', "To Declare"),
            ('postponed', "Postponed"),
            ('declared', "Declared"),
            ('excluded', "Excluded"),
            ('out_of_scope', "Out of Scope"),
            ('legacy', "Legacy"),
        ],
        string="HU VAT Status",
        tracking=True,
    )

    # Compute and search fields, in the same order of field declarations
    ## SUPER
    @api.depends('country_code', 'move_type')
    def _compute_show_delivery_date(self):
        # EXTENDS 'account'
        super()._compute_show_delivery_date()
        for move in self:
            if move.company_id.account_fiscal_country_id.code == 'HU':
                move.show_delivery_date = True

    @api.depends('delivery_date')
    def _compute_invoice_currency_rate(self):
        # EXTENDS 'account' — recompute invoice_currency_rate when delivery_date changes
        # mirrors l10n_hu_edi's pattern for _compute_expected_currency_rate (see #77)
        return super()._compute_invoice_currency_rate()

    ## HU+
    @api.depends('currency_id', 'invoice_date', 'delivery_date')
    def _compute_l10n_hu_currency(self):
        for record in self:
            rate_data = record.l10n_hu_plus_get_rate_data({})
            record.l10n_hu_invoice_currency_rate_date = rate_data.get('l10n_hu_invoice_currency_rate_date', None)
            record.l10n_hu_huf_currency = rate_data.get('l10n_hu_huf_currency', None)
            record.l10n_hu_invoice_currency_rate_inverse = rate_data.get('l10n_hu_invoice_currency_rate_inverse', None)

    @api.depends(
        "currency_id",
        "invoice_date",
        "delivery_date",
        "state",
        "reversed_entry_id",
        "reversed_entry_id.delivery_date",
        "reversed_entry_id.l10n_hu_huf_rate",
        "l10n_hu_document_type_technical_name",
    )
    def _compute_l10n_hu_huf_rate(self):
        """Compute and store invoice→HUF rate; freeze after posting.

        Draft invoices refresh from ``l10n_hu_plus_get_rate_data`` when currency or document dates change. Posted and cancelled
        moves keep the DB value via ``_origin`` so later rate-table or date-driven recomputes cannot change the document HUF rate;
        if that value is empty (invalidated cache on post, or pre-store upgrade), compute once from the live table then freeze on
        later runs. When the reversal wizard sets ``l10n_hu_storno_original_huf_rates`` (non-HUF company HU storno), create-time
        compute takes the original invoice's stored rate instead of the live table — same pattern as ``l10n_hu_oerp`` for
        ``invoice_currency_rate``. Draft modification invoices (``invoice_modification``) reuse the original stored HUF rate while
        ``delivery_date`` matches the original invoice; any other delivery date falls through to the live table path.
        """
        storno_huf_rates = self.env.context.get("l10n_hu_storno_original_huf_rates")
        for record in self:
            # create-time HU storno: keep original stored invoice→HUF rate (wizard context)
            if storno_huf_rates and record.reversed_entry_id.id in storno_huf_rates:
                record.l10n_hu_huf_rate = storno_huf_rates[record.reversed_entry_id.id]
                continue
            if record.state != "draft":
                # freeze from DB (_origin); avoid x=x which can persist 0 after cache invalidation on post/cancel
                frozen_rate = record._origin.l10n_hu_huf_rate
                if frozen_rate:
                    record.l10n_hu_huf_rate = frozen_rate
                else:
                    rate_data = record.l10n_hu_plus_get_rate_data({})
                    record.l10n_hu_huf_rate = rate_data.get("l10n_hu_huf_rate", 0.0)
                continue
            # modification: same delivery date as original → reuse original stored HUF rate
            original = record.reversed_entry_id
            if (
                record.l10n_hu_document_type_technical_name == "invoice_modification"
                and original
                and record.delivery_date
                and record.delivery_date == original.delivery_date
                and original.l10n_hu_huf_rate
            ):
                record.l10n_hu_huf_rate = original.l10n_hu_huf_rate
                continue
            rate_data = record.l10n_hu_plus_get_rate_data({})
            record.l10n_hu_huf_rate = rate_data.get("l10n_hu_huf_rate", 0.0)

    def _compute_l10n_hu_delivery_period_text(self):
        for record in self:
            period_summary = ""
            if (record.move_type in ['out_invoice', 'out_refund']
                    and record.l10n_hu_delivery_period_start and record.l10n_hu_delivery_period_end):
                delivery_result = record.l10n_hu_plus_get_delivery_data({})
                if delivery_result.get('period_summary'):
                    period_summary = delivery_result['period_summary']
            record.l10n_hu_delivery_period_summary = period_summary

    @api.depends('amount_untaxed', 'amount_tax', 'currency_id', 'l10n_hu_document_vat_huf', 'l10n_hu_huf_rate')
    def _compute_l10n_hu_document(self):
        for record in self:
            data_result = record.l10n_hu_plus_get_document_data({})
            record.l10n_hu_document_gross_huf = data_result.get('l10n_hu_document_gross_huf', 0)
            record.l10n_hu_document_net_huf = data_result.get('l10n_hu_document_net_huf', 0)
            record.l10n_hu_document_rate = data_result.get('l10n_hu_document_rate', 0)

    # Constraints and onchanges
    @api.onchange('l10n_hu_delivery_period_end', 'l10n_hu_delivery_period_start')
    def onchange_l10n_hu_delivery_period(self):
        if self.l10n_hu_delivery_period_end and self.l10n_hu_delivery_period_start:
            if self.l10n_hu_delivery_period_end < self.l10n_hu_delivery_period_start:
                raise exceptions.ValidationError(_("Period end date must be after period start date!"))
            else:
                pass
        else:
            pass

    @api.onchange('l10n_hu_invoice_currency_rate_inverse')
    def onchange_l10n_hu_invoice_currency_rate_inverse(self):
        if self.l10n_hu_invoice_currency_rate_inverse < 0:
            raise exceptions.ValidationError(_("Currency rate must be more than 0!"))
        elif self.l10n_hu_invoice_currency_rate_inverse > 0:
            self.invoice_currency_rate = 1 / self.l10n_hu_invoice_currency_rate_inverse
        else:
            pass

    @api.onchange('invoice_currency_rate')
    def onchange_l10n_hu_invoice_currency_rate(self):
        if self.invoice_currency_rate < 0:
            raise exceptions.ValidationError(_("Currency rate must be more than 0!"))
        elif self.invoice_currency_rate > 0:
            self.l10n_hu_invoice_currency_rate_inverse = 1 / self.invoice_currency_rate
        else:
            pass

    @api.onchange('invoice_payment_term_id')
    def onchange_l10n_hu_payment_term_id(self):
        if self.invoice_payment_term_id and self.journal_id and self.journal_id.l10n_hu_plus_enabled:
            self.invoice_cash_rounding_id = self.invoice_payment_term_id.l10n_hu_rounding_method
            self.l10n_hu_payment_mode = self.invoice_payment_term_id.l10n_hu_nav_method
        else:
            pass

    @api.onchange('l10n_hu_vat_status')
    def onchange_l10n_hu_vat_status(self):
        if not self.l10n_hu_vat_status:
            self.l10n_hu_vat_date = None
        else:
            pass

    # CRUD methods (and display_name, name_search, ...) overrides

    # Action methods
    ## SUPER
    def action_post(self):
        """ Do not allow posting invoice when HU+ status is error """
        for record in self:
            if (record.state == 'draft' and record.journal_id and record.journal_id.l10n_hu_plus_enabled
                    and record.is_invoice(include_receipts=True) and record.l10n_hu_plus_status == 'error'):
                raise exceptions.UserError(_("Can not post invoice with HU+ error!") + " " + str(record.display_name))
        return super().action_post()

    ## HU+
    def action_l10n_hu_plus_view_documentation(self):
        """ View HU+ documentation """
        self.ensure_one()
        return self.company_id.action_l10n_hu_plus_view_documentation()

    def action_l10n_hu_send_proforma(self):
        """Open a window to compose an email using mail template loaded by default"""
        # Ensure one
        self.ensure_one()

        # Prepare proforma_name
        if not self.l10n_hu_proforma_name and self.journal_id and self.journal_id.l10n_hu_proforma_sequence:
            self.l10n_hu_proforma_name = self.journal_id.l10n_hu_proforma_sequence.next_by_id()
        elif not self.l10n_hu_proforma_name:
            self.l10n_hu_proforma_name = self.env["ir.sequence"].next_by_code("l10n.hu.account.move.proforma")
        else:
            pass

        # proforma_self
        proforma_self = self.with_context(l10n_hu_use_proforma=True, proforma=True)

        # Get mail template
        if self.journal_id and self.journal_id.l10n_hu_proforma_mail_template:
            template_id = self.journal_id.l10n_hu_proforma_mail_template.id
        else:
            try:
                template_id = self.env.ref('l10n_hu_plus.account_move_proforma_mail_template').id
            except ValueError:
                template_id = False

        # Get composer
        try:
            compose_form_id = self.env['ir.model.data']._xmlid_lookup('mail.email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False

        # Set template
        template = template_id and self.env['mail.template'].browse(template_id)

        # Set final language
        if template and template.lang:
            language_dict = template._render_template(template.lang, 'account.move', proforma_self.ids)
            # raise exceptions.UserError("language_dict" + str(language_dict))
            language = language_dict[self.id]
        else:
            language = self.env.context.get('lang')
        # raise exceptions.UserError("language" + str(language))

        # subtype_id
        subtype_id = self.env.ref('l10n_hu_plus.proforma_send_mail_message_subtype').id

        # Set mail_context
        mail_context = {
            'default_composition_mode': 'comment',
            'default_model': 'account.move',
            'default_res_ids': proforma_self.ids,
            'default_subtype_id': subtype_id,
            'default_template_id': template_id,
            'default_use_template': bool(template_id),
            'force_email': True,
            'l10n_hu_use_proforma': True,
            # 'model_description': self.with_context(lang=language).move_type,
            'model_description': _("Proforma"),
            'proforma': True,
        }

        # Return
        return {
            'context': mail_context,
            'res_model': 'mail.compose.message',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'view_mode': 'form',
        }

    def action_l10n_hu_send_edi(self):
        """ Send invoice to HU EDI (NAV Online Szamla """
        self.ensure_one()
        return self.l10n_hu_do_send_edi()

    def action_l10n_hu_uncheck(self):
        """ Set checked boolean to False """
        self.ensure_one()
        return self.write({'checked': False})

    def action_l10n_hu_update_fields(self):
        """ Update HU+ relevant fields """
        self.ensure_one()
        if self.state != 'draft':
            raise exceptions.UserError(_("Action only allowed for draft invoices!"))
        values_result = self.l10n_hu_plus_get_data({})
        if len(values_result.get('error_list')) == 0 and len(values_result.get('field_values')) > 0:
            self.write(values_result['field_values'])
            self.action_l10n_hu_update_plus_status()
            return
        elif len(values_result.get('field_values')) == 0:
            return
        else:
            raise exceptions.UserError(str(values_result['error_list']))

    def action_l10n_hu_update_plus_status(self):
        """ Update HU+ status """
        self.ensure_one()
        plus_status = self.l10n_hu_get_plus_status()
        return self.write({'l10n_hu_plus_status': plus_status})

    def action_l10n_hu_view_account_move_lines(self):
        """ View account move lines """
        self.ensure_one()
        form_id = self.env.ref('account.view_move_line_form').id
        kanban_id = self.env.ref('account.account_move_line_view_kanban').id
        list_id = self.env.ref('account.view_move_line_tree').id
        pivot_id = self.env.ref('account.view_move_line_pivot').id
        return {
            'name': _("Account Move Lines"),
            'domain': [('id', 'in', self.line_ids.ids), ('display_type', 'not in', ['line_section', 'line_note'])],
            'res_model': 'account.move.line',
            'target': 'current',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,pivot,kanban,form',
            'views': [(list_id, 'list'), (pivot_id, 'pivot'), (kanban_id, 'kanban'), (form_id, 'form')],
        }

    def action_l10n_hu_view_analytic_lines(self):
        """ View account move related analytic line """
        self.ensure_one()
        analytic_line_ids = self.env['account.analytic.line'].search([('move_line_id', 'in', self.line_ids.ids)]).ids
        form_view = self.env.ref('analytic.view_account_analytic_line_form')
        list_view = self.env.ref('analytic.view_account_analytic_line_tree')
        if analytic_line_ids and len(analytic_line_ids) == 1:
            return {
                'name': _("Analytic Line"),
                'res_id': analytic_line_ids[0],
                'res_model': 'account.analytic.line',
                'target': 'current',
                'type': 'ir.actions.act_window',
                'view_mode': 'form,list',
                'views': [(form_view.id, 'form'), (list_view.id, 'list')],
            }
        else:
            return {
                'name': _("Analytic Lines"),
                'domain': [('id', 'in', analytic_line_ids)],
                'res_model': 'account.analytic.line',
                'target': 'current',
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'views': [(list_view.id, 'list'), (form_view.id, 'form')],
            }

    def action_l10n_hu_view_original_invoice(self):
        """ View original invoice """
        self.ensure_one()
        original_invoice = None
        if self.l10n_hu_original_invoice_number:
            if self.move_type in ['in_invoice', 'in_refund']:
                original_invoice = self.env['account.move'].search([
                    ('company_id', '=', self.company_id.id),
                    ('move_type', 'in', ['in_invoice', 'in_refund']),
                    ('ref', 'ilike', self.l10n_hu_original_invoice_number)
                ], limit=1)
            elif self.move_type in ['out_invoice', 'out_refund']:
                original_invoice = self.env['account.move'].search([
                    ('company_id', '=', self.company_id.id),
                    ('move_type', 'in', ['out_invoice', 'out_refund']),
                    ('name', 'ilike', self.l10n_hu_original_invoice_number)
                ], limit=1)
            else:
                pass
        if original_invoice:
            return {
                'name': _("HU+ Wizard"),
                'res_id': original_invoice.id,
                'res_model': 'account.move',
                'target': 'current',
                'type': 'ir.actions.act_window',
                'view_mode': 'form,list',
            }
        else:
            raise exceptions.UserError(_("Original invoice not found!"))

    def action_l10n_hu_view_currency_rates(self):
        """ View currency rates """
        self.ensure_one()
        if self.currency_id and self.currency_id == self.company_id.currency_id:
            raise exceptions.UserError(_("Invoice currency is same as company currency!"))
        currency_ids = [self.currency_id.id]
        if self.company_id.currency_id.name != 'HUF':
            currency_ids.append(self.env.ref('base.HUF').id)
        return {
            'name': _("Currency Rates"),
            'context': {
                'search_default_name': self.delivery_date,
                'search_default_currency_id_filter_group_by': 1,
                'default_currency_id': self.currency_id.id
            },
            'domain': [('currency_id', 'in', currency_ids)],
            'res_model': 'res.currency.rate',
            'target': 'current',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
        }

    def action_l10n_hu_wizard_accounting(self):
        """ Open the HU+ wizard to update accounting fields """
        self.ensure_one()
        if self.state != 'draft':
            raise exceptions.UserError(_("Action only allowed for draft invoices!"))
        return {
            'name': _("HU+ Wizard"),
            'context': {
                'default_action_type': 'account_move',
                'default_action_type_visible': False,
                'default_account_move_action': 'update_fields',
                'default_company': self.company_id.id,
            },
            'res_model': 'l10n.hu.plus.wizard',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
        }

    def action_l10n_hu_wizard_check_status(self):
        """ Open the HU+ wizard to check status for HU+ """
        self.ensure_one()
        self.action_l10n_hu_update_plus_status()
        status_overview = self.l10n_hu_get_plus_status_overview()
        return {
            'name': _("HU+ Wizard"),
            'context': {
                'default_action_type': 'account_move',
                'default_action_type_visible': False,
                'default_account_move_action': 'check_status',
                'default_account_move_action_visible': False,
                'default_account_move_plus_overview': status_overview,
                'default_company': self.company_id.id,
            },
            'res_model': 'l10n.hu.plus.wizard',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
        }

    # Business methods
    ## SUPER
    def _l10n_hu_get_currency_rate(self):
        """Override: prefer stored HU+ HUF rate / manual invoice rate for NAV and document HUF.

        :return: currency conversion rate (invoice_ccy → HUF)
        :rtype: float

        Priority:
        1. Non-HUF company, HU fiscal, posted/cancel with stored ``l10n_hu_huf_rate`` — document rate frozen at post
           (draft must keep calling ``super()`` so ``_compute_l10n_hu_huf_rate`` can still refresh from the live table).
        2. HUF company with manually overridden ``invoice_currency_rate`` — ``1 / invoice_currency_rate``.
        3. Otherwise live ``res.currency.rate`` via ``l10n_hu_edi``.
        """
        self.ensure_one()
        currency_huf = self.env.ref("base.HUF")
        # posted/cancel non-HUF company: NAV XML and callers must use the frozen HU+ HUF Rate
        if (self.company_id.account_fiscal_country_id.code == "HU"
                and self.company_id.currency_id != currency_huf
                and self.state != "draft"
                and self.l10n_hu_huf_rate):
            if self.currency_id == currency_huf:
                return 1.0
            return self.l10n_hu_huf_rate
        # HUF company: honour a manual invoice_currency_rate override
        if (self.is_invoice(include_receipts=True)
                and self.company_id.currency_id == currency_huf
                and self.currency_id != self.company_id.currency_id
                and self.invoice_currency_rate
                and self.invoice_currency_rate != self.expected_currency_rate):
            return 1 / self.invoice_currency_rate
        return super()._l10n_hu_get_currency_rate()

    @api.model
    def _l10n_hu_migrate_huf_rates(self) -> int:
        """Backfill stored ``l10n_hu_huf_rate`` on posted/cancelled non-HUF company HU invoices.

        Search scope matches ``_l10n_hu_is_huf_rate_migration_candidate``. Process moves without
        ``reversed_entry_id`` first, then reversals, so storno / same-date modification fallbacks can read an already
        migrated original. Write the rate directly; do not rely on the posted freeze compute for empty fields.

        :returns: number of moves updated
        """
        currency_huf = self.env.ref("base.HUF")
        domain = [
            ("company_id.account_fiscal_country_id.code", "=", "HU"),
            ("company_id.currency_id", "!=", currency_huf.id),
            ("state", "in", ("posted", "cancel")),
            ("move_type", "in", self.get_invoice_types(include_receipts=True)),
            ("l10n_hu_huf_rate", "in", (False, 0, 0.0)),
        ]
        updated_count = 0
        # normals first, then storno / modification so original.l10n_hu_huf_rate is already filled when needed
        for reversed_entry_domain in (
            [("reversed_entry_id", "=", False)],
            [("reversed_entry_id", "!=", False)],
        ):
            moves = self.search(domain + reversed_entry_domain)
            for move in moves:
                rate = move._l10n_hu_get_migrated_huf_rate()
                if not rate:
                    continue
                move.write({"l10n_hu_huf_rate": rate})
                updated_count += 1
        return updated_count

    def _l10n_hu_get_migrated_huf_rate(self) -> float:
        """Resolve one move's HUF rate for migration.

        Out-of-scope moves return 0.0. Invoice currency HUF returns 1.0. Otherwise prefer NAV XML
        ``exchangeRate``; then original invoice rate for storno or same-date modification; then live
        ``l10n_hu_plus_get_rate_data``.

        :returns: HUF rate to store, or 0.0 when none could be resolved
        """
        self.ensure_one()
        if not self._l10n_hu_is_huf_rate_migration_candidate():
            return 0.0
        currency_huf = self.env.ref("base.HUF")
        if self.currency_id == currency_huf:
            return 1.0
        xml_rate = self._l10n_hu_get_huf_rate_from_nav_xml()
        if xml_rate:
            return xml_rate
        original = self.reversed_entry_id
        technical_name = self.l10n_hu_document_type_technical_name
        if technical_name == "invoice_storno" and original and original.l10n_hu_huf_rate:
            return original.l10n_hu_huf_rate
        if (
            technical_name == "invoice_modification"
            and original
            and self.delivery_date
            and self.delivery_date == original.delivery_date
            and original.l10n_hu_huf_rate
        ):
            return original.l10n_hu_huf_rate
        rate_data = self.l10n_hu_plus_get_rate_data({})
        return rate_data.get("l10n_hu_huf_rate", 0.0) or 0.0

    def _l10n_hu_is_huf_rate_migration_candidate(self) -> bool:
        """Return whether this move is in scope for stored HUF rate backfill.

        Scope: Hungarian fiscal company with non-HUF currency, posted or cancelled invoice/receipt, empty stored
        ``l10n_hu_huf_rate``. Draft and HUF-company moves are excluded.

        :returns: True when the move should receive a migrated HUF rate
        """
        self.ensure_one()
        currency_huf = self.env.ref("base.HUF")
        if self.company_id.account_fiscal_country_id.code != "HU":
            return False
        if self.company_id.currency_id == currency_huf:
            return False
        if self.state not in ("posted", "cancel"):
            return False
        if not self.is_invoice(include_receipts=True):
            return False
        if self.l10n_hu_huf_rate:
            return False
        return True

    def _l10n_hu_get_huf_rate_from_nav_xml(self) -> float:
        """Read ``exchangeRate`` from the stored NAV EDI XML attachment.

        :returns: exchange rate from XML, or 0.0 when missing or unreadable
        """
        self.ensure_one()
        if not self.l10n_hu_edi_attachment:
            return 0.0
        try:
            root = etree.fromstring(base64.b64decode(self.l10n_hu_edi_attachment))
        except (etree.XMLSyntaxError, ValueError, TypeError):
            return 0.0
        nodes = root.xpath("//*[local-name()='exchangeRate']")
        if not nodes or not (nodes[0].text or "").strip():
            return 0.0
        try:
            return float(nodes[0].text.strip())
        except ValueError:
            return 0.0

    def _get_invoice_currency_rate_date(self):
        self.ensure_one()
        result = super()._get_invoice_currency_rate_date()
        if (self.company_id.account_fiscal_country_id.code == 'HU' and self.delivery_date and self.invoice_date
                and self.delivery_date > self.invoice_date):
            return self.invoice_date
        return result

    def _get_report_base_filename(self) -> str:
        """ Get the filename for proforma"""
        if self.state == 'draft' and self.l10n_hu_proforma_name:
            return str(self.company_id.vat) + "_" + str(self.l10n_hu_proforma_name).replace('/', '_')
        else:
            return super()._get_report_base_filename()

    @api.model
    def _l10n_hu_zero_clamp_huf_amount(self, amount, threshold=None):
        """Return 0 for technical HUF residuals below the document display threshold."""
        if amount is None:
            return amount
        threshold = self.L10N_HU_DOCUMENT_HUF_ZERO_CLAMP if threshold is None else threshold
        return 0.0 if abs(amount) < threshold else amount

    @api.model
    def _l10n_hu_is_within_document_huf_tolerance(self, diff, threshold=None):
        threshold = self.L10N_HU_DOCUMENT_HUF_ZERO_CLAMP if threshold is None else threshold
        return abs(diff) < threshold

    def _l10n_hu_get_document_huf_rate(self):
        """Return the NAV/document HUF rate for foreign-currency customer invoices."""
        self.ensure_one()
        if self.invoice_currency_rate:
            return 1 / self.invoice_currency_rate
        if self.l10n_hu_invoice_currency_rate_inverse:
            return self.l10n_hu_invoice_currency_rate_inverse
        return 1.0

    def _l10n_hu_get_company_currency_tax_totals_for_report(self):
        """Return company-currency tax totals using document/NAV rate and zero-clamp."""
        self.ensure_one()
        tax_totals = copy.deepcopy(self.tax_totals or {})
        if not tax_totals.get('display_in_company_currency'):
            return tax_totals

        currency_huf = self.env.ref('base.HUF')
        if self.company_id.currency_id != currency_huf or self.currency_id == currency_huf:
            return tax_totals
        if not self.invoice_currency_rate:
            return tax_totals

        document_rate = self._l10n_hu_get_document_huf_rate()

        def _document_huf(amount_currency):
            return self._l10n_hu_zero_clamp_huf_amount(
                currency_huf.round(amount_currency * document_rate)
            )

        amount_pairs = (
            ('base_amount', 'base_amount_currency'),
            ('tax_amount', 'tax_amount_currency'),
            ('total_amount', 'total_amount_currency'),
        )
        for huf_field, currency_field in amount_pairs:
            if currency_field in tax_totals:
                tax_totals[huf_field] = _document_huf(tax_totals[currency_field])

        for subtotal in tax_totals.get('subtotals', []):
            for huf_field, currency_field in amount_pairs[:2]:
                if currency_field in subtotal:
                    subtotal[huf_field] = _document_huf(subtotal[currency_field])
            for tax_group in subtotal.get('tax_groups', []):
                for huf_field, currency_field in (
                    ('base_amount', 'base_amount_currency'),
                    ('tax_amount', 'tax_amount_currency'),
                    ('display_base_amount', 'display_base_amount_currency'),
                ):
                    if currency_field in tax_group and tax_group[currency_field] is not None:
                        tax_group[huf_field] = _document_huf(tax_group[currency_field])

        return tax_totals

    def _l10n_hu_get_invoice_totals_for_report(self):
        """ Super for original method in l10n_hu_edi app

        NOTES:
        - super result is a dictionary
        - company HUF and foreign invoice currency: use document/NAV rate with zero-clamp (see #3832)
        - company NOT HUF and HU fiscal country: convert VAT to HUF via l10n_hu_huf_rate (TASK-166)
        """
        # Execute super
        result = super()._l10n_hu_get_invoice_totals_for_report()
        if not result:
            return result

        self.ensure_one()
        currency_huf = self.env.ref('base.HUF')

        # Company HUF, foreign invoice currency: document/NAV rate HUF VAT with zero-clamp
        if (self.company_id.currency_id == currency_huf
                and self.currency_id != currency_huf
                and self.invoice_currency_rate):
            document_rate = self._l10n_hu_get_document_huf_rate()
            vat_huf = self._l10n_hu_zero_clamp_huf_amount(
                currency_huf.round(abs(self.amount_tax) * document_rate)
            )
            result['total_vat_amount_in_huf'] = vat_huf
            result['formatted_total_vat_amount_in_huf'] = formatLang(
                self.env, vat_huf, currency_obj=currency_huf
            )
        # Company NOT HUF, HU fiscal country: convert VAT to HUF via huf_rate
        elif self.company_id.currency_id.name != 'HUF' and self.company_id.account_fiscal_country_id.code == 'HU':
            huf_vat = result['total_vat_amount_in_huf']
            huf_rate = self.l10n_hu_huf_rate
            result['total_vat_amount_in_huf'] = huf_vat * huf_rate
            result['formatted_total_vat_amount_in_huf'] = formatLang(
                self.env, result['total_vat_amount_in_huf'], currency_obj=currency_huf
            )
            # Hide tax detail table in company currency
            result['display_in_company_currency'] = False

        # Return result
        return result

    def _l10n_hu_edi_get_invoice_values(self):
        """ Super for original method in l10n_hu_edi app

        NOTES:
        - super result is a dictionary containing invoice_values
        - we update the dictionary with some values
        - for xml rendering see file: data/template_invoice_xml.data

        """
        # Execute super
        result = super(L10nHuPlusAccountMove, self)._l10n_hu_edi_get_invoice_values()

        # fix invoice summary rounding: derive all HUF totals from EUR values * NAV exchange rate
        # to avoid INCORRECT_SUMMARY_CALCULATION / INCORRECT_SUMMARY_DATA NAV warnings (see #76)
        # The original code uses -line.balance (Odoo's accounting rate) for vatRateVatAmountHUF,
        # but the NAV validates: vatRateVatAmount * exchangeRate == vatRateVatAmountHUF
        # When delivery_date rate ≠ invoice_date rate, these diverge.
        currency_huf = self.env.ref("base.HUF")
        currency_rate = self._l10n_hu_get_currency_rate()
        is_company_huf = self.company_id.currency_id == currency_huf

        # aggregate VAT amounts by tax to handle multiple tax lines for the same VAT rate
        # (e.g. different analytic distribution / rounding splits)
        aggregated_tax_amounts = defaultdict(lambda: {
            "vatRateVatAmount": 0.0,
            "vatRateVatAmountHUF": 0.0,
        })
        for line in self.line_ids.filtered(lambda record: record.tax_line_id.l10n_hu_tax_type):
            vat_tax = line.tax_line_id
            aggregated_tax_amounts[vat_tax]["vatRateVatAmount"] += -line.amount_currency
            if is_company_huf:
                aggregated_tax_amounts[vat_tax]["vatRateVatAmountHUF"] += -line.balance
            else:
                aggregated_tax_amounts[vat_tax]["vatRateVatAmountHUF"] += currency_huf.round(-line.amount_currency * currency_rate)

        for vat_tax in aggregated_tax_amounts:
            aggregated_tax_amounts[vat_tax]["vatRateVatAmount"] = self.currency_id.round(
                aggregated_tax_amounts[vat_tax]["vatRateVatAmount"]
            )
            aggregated_tax_amounts[vat_tax]["vatRateVatAmountHUF"] = currency_huf.round(
                aggregated_tax_amounts[vat_tax]["vatRateVatAmountHUF"]
            )

        # replace super tax VAT amounts with aggregated values before summary recomputation
        for tax_vals in result["tax_summary"]:
            vat_tax = tax_vals["vat_tax"]
            if vat_tax in aggregated_tax_amounts:
                tax_vals["vatRateVatAmount"] = aggregated_tax_amounts[vat_tax]["vatRateVatAmount"]

        # recalculate vatRateVatAmountHUF from EUR VAT * NAV rate
        for tax_vals in result["tax_summary"]:
            tax_vals["vatRateVatAmountHUF"] = currency_huf.round(
                tax_vals["vatRateVatAmount"] * currency_rate
            )
        # derive all summary totals from per-VAT-rate values
        total_net = self.currency_id.round(
            sum(tv["vatRateNetAmount"] for tv in result["tax_summary"])
        )
        total_net_huf = currency_huf.round(
            sum(tv["vatRateNetAmountHUF"] for tv in result["tax_summary"])
        )
        total_vat = self.currency_id.round(
            sum(tv["vatRateVatAmount"] for tv in result["tax_summary"])
        )
        total_vat_huf = currency_huf.round(
            sum(tv["vatRateVatAmountHUF"] for tv in result["tax_summary"])
        )
        result.update({
            "invoiceNetAmount": total_net,
            "invoiceNetAmountHUF": total_net_huf,
            "invoiceVatAmount": total_vat,
            "invoiceVatAmountHUF": total_vat_huf,
            "invoiceGrossAmount": self.currency_id.round(total_net + total_vat),
            "invoiceGrossAmountHUF": currency_huf.round(total_net_huf + total_vat_huf),
        })

        # accounting_delivery_date
        if self.l10n_hu_delivery_period_start and self.l10n_hu_delivery_period_end:
            accounting_delivery_date = self.l10n_hu_delivery_period_end
        elif self.delivery_date:
            accounting_delivery_date = self.delivery_date
        elif self.date:
            accounting_delivery_date = self.date
        else:
            accounting_delivery_date = None

        # periodical_settlement
        if self.l10n_hu_delivery_period_start and self.l10n_hu_delivery_period_end:
            periodical_settlement = True
        else:
            periodical_settlement = False

        # Update result
        result.update({
            'invoiceAccountingDeliveryDate': accounting_delivery_date,
            'invoiceDeliveryPeriodEnd': self.l10n_hu_delivery_period_end,
            'invoiceDeliveryPeriodStart': self.l10n_hu_delivery_period_start,
            'periodicalSettlement': periodical_settlement
        })

        # Customer tax number
        ## NOTES: temporary workaround until Odoo S.A. fix, see https://github.com/hungarodo/odoohu-plus/issues/31
        customer = result.get('customer', None)
        if (customer and customer.is_company and customer.vat and customer.country_code != 'HU'
                and self.fiscal_position_id and self.fiscal_position_id.l10n_hu_vat_status == 'domestic'):
            result.update({
                'customer_vat_data': {
                    'tax_number': customer.l10n_hu_group_vat or customer.vat,
                    'group_member_tax_number': customer.l10n_hu_group_vat and customer.vat,
                },
                'customerVatStatus': 'DOMESTIC'
            })

        # Return result
        return result

    def _l10n_hu_edi_get_valid_actions(self):
        """ Super for original method in l10n_hu_edi app

        NOTES:
        - super result is a list containing possible HU EDI actions
        - we empty the list in case EDI is disabled on the journal
        """
        # Execute super
        result = super(L10nHuPlusAccountMove, self)._l10n_hu_edi_get_valid_actions()

        # No action when EDI sending is disabled on the journal (eg: externally issued invoices, OSS)
        if (self.company_id.account_fiscal_country_id.code == 'HU' and self.journal_id and self.state == 'posted'
                and self.is_sale_document() and self.journal_id.l10n_hu_edi_sending == 'disabled'):
            result = []
        return result

    ## HU+ CRON
    @api.model
    def l10n_hu_run_account_move_cron(self):
        """ Meant to be called by cron

        NOTES:
        - cron jobs are not company aware
        - we use batch limit per journal

        :return: dictionary, also an info entry into l10n_hu.log
        """
        # Initialize variables
        company_ids = []
        company_results = []
        date_today = fields.Date.today()
        debug_list = []
        error_list = []
        log_ids = []
        result = {}

        # Get companies
        companies = self.env['res.company'].sudo().search([('account_fiscal_country_id.code', '=', 'HU')])

        # Process companies
        for company in companies:
            # Initialize variables
            journal_ids = []
            journal_results = []

            # Get journals
            journals = self.env['account.journal'].sudo().search([
                ('company_id', '=', company.id),
                ('l10n_hu_cron_batch', '>', 0),
                ('l10n_hu_plus_enabled', '=', True),
                ('type', 'in', ['purchase', 'sale']),
            ])
            debug_list.append("processing company: " + str(company.id))
            debug_list.append("eligible journal count: " + str(len(journals)))

            # Process journals
            for journal in journals:
                # Initialize variables
                journal_debug_list = []
                journal_error_list = []

                # Set batch
                batch = journal.l10n_hu_cron_batch
                journal_debug_list.append("batch: " + str(batch))

                # 1: Update HU+ status
                status_invoices = self.env['account.move'].sudo().search([
                    ('journal_id', '=', journal.id),
                    ('l10n_hu_plus_status', 'not in', ['closed', 'other']),
                ], limit=batch, order='write_date asc')
                journal_debug_list.append("status_invoices count: " + str(len(status_invoices)))
                for status_invoice in status_invoices:
                    status_invoice.action_l10n_hu_update_plus_status()

                # 2: Send EDI (NAV Online Szamla)
                if journal.type == 'sale' and journal.l10n_hu_edi_sending in ['auto_edi', 'auto_edi_email']:
                    auto_edi_invoices = self.env['account.move'].sudo().search([
                        ('journal_id', '=', journal.id),
                        ('invoice_date', '=', date_today),
                        ('l10n_hu_edi_state', '=', None),
                        ('l10n_hu_plus_status', 'not in', ['closed']),
                        ('move_type', 'in', ['out_invoice', 'out_refund']),
                        ('state', '=', 'posted')
                    ], limit=batch, order='write_date asc')
                    journal_debug_list.append("auto_edi_invoices count: " + str(len(auto_edi_invoices)))
                    for auto_edi_invoice in auto_edi_invoices:
                        auto_edi_invoice.action_l10n_hu_send_edi()

                # Assemble journal_result
                journal_result = {
                    'journal_id': journal.id,
                    'journal_type': journal.type,
                    'journal_debug_list': journal_debug_list,
                    'journal_error_list': journal_error_list,
                }

                # Append to lists
                journal_ids.append(journal.id)
                journal_results.append(journal_result)

            # Assemble company_result
            company_result = {
                'company_id': company.id,
                'journal_ids': journal_ids,
                'journal_results': journal_results,
            }

            # Append to lists
            company_ids.append(company.id)
            company_results.append(company_result)

            # Create log
            ## NOTES: we want to log everything, even failed attempts
            log_description = {'company_result': company_result}
            log_values = {
                'app_name': 'l10n_hu_plus',
                'company': company.id,
                'description': json.dumps(log_description, default=str),
                'direction': 'internal',
                'level': 'info',
                'log_type': 'l10n_hu_run_account_move_cron',
                'name': 'l10n_hu_run_account_move_cron company_id:' + str(company.id),
                'source_model_name': 'res.company',
                'source_record_id': company.id,
                'technical_data': json.loads(json.dumps(company_result, default=str)),
                'technical_name': 'l10n_hu_plus.l10n_hu_run_account_move_cron',
                'timestamp': fields.Datetime.now(),
                'user_id': self.env.uid,
            }
            log_record = self.env['l10n.hu.plus.log'].create(log_values)
            log_ids.append(log_record.id)

        # Update result
        result.update({
            'company_ids': company_ids,
            'company_results': company_results,
            'debug_list': debug_list,
            'error_list': error_list,
            'log_ids': log_ids,
        })

        # Return result
        return result

    ## HU+ DATA
    @api.model
    def l10n_hu_plus_get_data(self, values):
        """ Get relevant HU+ related data

        NOTES:
        - central method to collect and compute hungarian localization data
        - some fields are computed by calling other methods
        - this method also prepares write operation compatible values for special hungarian fields
        - there should be no CRUD operation here, keep it in mind when using super()

        :param values: dictionary

        :return: dictionary
        """
        # raise exceptions.UserError("l10n_hu_plus_get_data BEGIN" + str(values))

        # Initialize variables
        debug_list = []
        error_list = []
        field_values = {}
        info_list = []
        result = {}
        warning_list = []

        # HU+ enabled
        if self.journal_id and self.journal_id.l10n_hu_plus_enabled:
            debug_list.append("HU+ enabled journal check passed")
        else:
            error_list.append("HU+ enabled journal check failed")

        # Check move type
        if self.move_type in ['in_invoice', 'in_refund', 'out_invoice', 'out_refund']:
            debug_list.append("move type check passed")
        else:
            error_list.append("invalid account move type")

        # Collect data using dedicated methods
        ## DELIVERY
        delivery_data = self.l10n_hu_plus_get_delivery_data(values)
        delivery_date = delivery_data.get('delivery_date')
        invoice_date_due = delivery_data.get('invoice_date_due')
        l10n_hu_delivery_period_end = delivery_data.get('l10n_hu_delivery_period_end')
        l10n_hu_delivery_period_start = delivery_data.get('l10n_hu_delivery_period_start')
        error_list += delivery_data.get('error_list', [])
        warning_list += delivery_data.get('warning_list', [])

        ## DOCUMENT
        document_data = self.l10n_hu_plus_get_document_data(values)
        error_list += document_data.get('error_list', [])
        warning_list += document_data.get('warning_list', [])

        ## RATE - NOTES: do this after date
        rate_values = values
        rate_values.update({'delivery_date': delivery_date})
        rate_data = self.l10n_hu_plus_get_rate_data(rate_values)
        error_list += rate_data.get('error_list', [])
        warning_list += rate_data.get('warning_list', [])

        ## VAT - NOTES: do this at last, we need to prepare values before this
        vat_values = values
        vat_values.update({'delivery_date': delivery_date})
        vat_data = self.l10n_hu_plus_get_vat_data(vat_values)
        error_list += vat_data.get('error_list', [])
        warning_list += vat_data.get('warning_list', [])

        # Process field values
        if len(error_list) == 0:
            # DUE DATE
            ## NOTES: we need this because payment term may change the due date
            if invoice_date_due and invoice_date_due != self.invoice_date_due:
                debug_list.append(f"invoice_date_due updated: {self.invoice_date_due}->{invoice_date_due}")
                field_values.update({'invoice_date_due': invoice_date_due})

            # DELIVERY
            ## NOTES: write on delivery date triggers recompute of currency rate date! Update it only when necessary!
            if delivery_date and delivery_date != self.delivery_date:
                delivery_date_update = True
            else:
                delivery_date_update = False
            if self.state == 'draft' and delivery_date_update:
                debug_list.append(f"delivery date updated: {self.delivery_date}->{delivery_date}")
                field_values.update({'delivery_date': delivery_date})
            if self.state == 'draft' and l10n_hu_delivery_period_end:
                field_values.update({'l10n_hu_delivery_period_end': l10n_hu_delivery_period_end})
            if self.state == 'draft' and l10n_hu_delivery_period_start:
                field_values.update({'l10n_hu_delivery_period_start': l10n_hu_delivery_period_start})

            # DOCUMENT
            if document_data.get('l10n_hu_document_type'):
                field_values.update({'l10n_hu_document_type': document_data['l10n_hu_document_type'].id})
            l10n_hu_document_vat_huf = document_data.get('l10n_hu_document_vat_huf', self.l10n_hu_document_vat_huf)
            l10n_hu_document_rate = document_data.get('l10n_hu_document_rate', self.l10n_hu_document_rate)
            field_values.update({
                'l10n_hu_document_rate': l10n_hu_document_rate,
                'l10n_hu_document_vat_huf': l10n_hu_document_vat_huf,
            })

            # RATE
            # modification with same delivery date: keep original stored HUF rate (do not overwrite from live table)
            huf_rate = rate_data.get("l10n_hu_huf_rate", 0.0)
            original = self.reversed_entry_id
            if (
                self.l10n_hu_document_type_technical_name == "invoice_modification"
                and original
                and self.delivery_date
                and self.delivery_date == original.delivery_date
                and original.l10n_hu_huf_rate
            ):
                huf_rate = original.l10n_hu_huf_rate
            field_values.update({
                "l10n_hu_huf_currency": rate_data.get("l10n_hu_huf_currency"),
                "l10n_hu_document_rate": rate_data.get("l10n_hu_document_rate", 0.0),
                "l10n_hu_huf_rate": huf_rate,
                "l10n_hu_invoice_currency_rate_date": rate_data.get("l10n_hu_invoice_currency_rate_date"),
                "l10n_hu_invoice_currency_rate_inverse": rate_data.get("l10n_hu_invoice_currency_rate_inverse", 0.0),
            })
            # Only update invoice currency rate if delivery date has changed
            if delivery_date_update:
                if rate_data.get('invoice_currency_rate') != self.invoice_currency_rate:
                    field_values.update({'invoice_currency_rate': rate_data['invoice_currency_rate']})
                    debug_list.append(f"invoice_currency_rate update: {rate_data['invoice_currency_rate']}")
                if rate_data.get('l10n_hu_invoice_currency_rate_date') != self.l10n_hu_invoice_currency_rate_date:
                    field_values.update({'l10n_hu_invoice_currency_rate_date': rate_data['l10n_hu_invoice_currency_rate_date']})
                    debug_list.append(f"l10n_hu_invoice_currency_rate_date update: {rate_data['l10n_hu_invoice_currency_rate_date']}")
                if rate_data.get('l10n_hu_invoice_currency_rate_inverse') != self.l10n_hu_invoice_currency_rate_inverse:
                    field_values.update({'l10n_hu_invoice_currency_rate_inverse': rate_data['l10n_hu_invoice_currency_rate_inverse']})
                    debug_list.append(f"l10n_hu_invoice_currency_rate_inverse update: {rate_data['l10n_hu_invoice_currency_rate_inverse']}")
            else:
                pass

            # VAT
            field_values.update({
                'l10n_hu_cash_accounting': vat_data.get('l10n_hu_cash_accounting', False),
                'l10n_hu_vat_date': vat_data.get('l10n_hu_vat_date', self.l10n_hu_vat_date),
                'l10n_hu_vat_status': vat_data.get('l10n_hu_vat_status', self.l10n_hu_vat_status),
            })

            # l10n_hu_payment_mode
            if values.get('l10n_hu_payment_mode'):
                field_values.update({'l10n_hu_payment_mode': values['l10n_hu_payment_mode'].upper()})
                debug_list.append("l10n_hu_payment_mode set from values: " + str(values['l10n_hu_payment_mode']))
            elif self.l10n_hu_payment_mode:
                field_values.update({'l10n_hu_payment_mode': self.l10n_hu_payment_mode})
                debug_list.append("l10n_hu_payment_mode set from self: " + str(self.l10n_hu_payment_mode))
            elif (not self.l10n_hu_payment_mode and self.invoice_payment_term_id
                  and self.invoice_payment_term_id.l10n_hu_nav_method):
                l10n_hu_payment_mode_2 = self.invoice_payment_term_id.l10n_hu_nav_method.upper()
                field_values.update({'l10n_hu_payment_mode': l10n_hu_payment_mode_2})
                debug_list.append("l10n_hu_payment_mode set from payment term: " + str(l10n_hu_payment_mode_2))
            elif not self.l10n_hu_payment_mode and self.journal_id.l10n_hu_nav_payment_method:
                l10n_hu_payment_mode_3 = self.journal_id.l10n_hu_nav_payment_method.upper()
                field_values.update({'l10n_hu_payment_mode': l10n_hu_payment_mode_3})
                debug_list.append("l10n_hu_payment_mode set from journal: " + str(l10n_hu_payment_mode_3))
            else:
                pass
        else:
            debug_list.append("processing skipped due to previous errors")

        # Update result
        result.update({
            'debug_list': debug_list,
            'delivery_data': delivery_data,
            'document_data': document_data,
            'error_list': error_list,
            'field_values': field_values,
            'info_list': info_list,
            'rate_data': rate_data,
            'vat_data': vat_data,
            'warning_list': warning_list,
        })

        # Return result
        # raise exceptions.UserError("l10n_hu_plus_get_data END" + str(result))
        return result

    @api.model
    def l10n_hu_plus_get_delivery_data(self, values):
        """ Get date data considering special hungarian rules

        NOTES:
        - This method only collects data, can be called by various other methods
        - Periodic delivery specification: 2007. CXXVII. 58.§ (1) https://njt.hu/jogszabaly/2007-127-00-00
        - MOPSZ 18.0 documentation: https://mopsz18.hungarodo.hu/odoo/knowledge/78

        :param values: dictionary

        :return: dictionary
        """
        # Initialize variables
        debug_list = []
        error_list = []
        info_list = []
        result = {}
        warning_list = []

        # dates
        accounting_date = values.get('date', self.date)
        delivery_date = values.get('delivery_date', self.delivery_date)
        invoice_date = values.get('invoice_date', self.invoice_date)
        period_end = values.get('l10n_hu_delivery_period_end', self.l10n_hu_delivery_period_end)
        period_start = values.get('l10n_hu_delivery_period_start', self.l10n_hu_delivery_period_start)

        # delivery_date_default
        if not delivery_date and self.move_type in ['in_invoice', 'in_refund'] and invoice_date:
            delivery_date_default = invoice_date
        elif not delivery_date and self.journal_id:
            delivery_date_default = self.journal_id.l10n_hu_get_default_delivery_date()
        else:
            delivery_date_default = None
            debug_list.append("delivery_date_default not set, this is a valid scenario")

        # period_enabled
        if period_start and period_end and self.state == 'draft' and self.move_type in ['out_invoice', 'out_refund']:
            period_enabled = True
        else:
            period_enabled = False

        # invoice_date_due
        if values.get('invoice_date_due'):
            invoice_date_due = values['invoice_date_due']
            debug_list.append(f"invoice_date_due set from values: {invoice_date_due}")
        elif self.invoice_payment_term_id:
            # NOTES: using a payment term needs a recompute, see _compute_invoice_date_due()
            if self.state == 'draft':
                self._compute_needed_terms()
            debug_list.append(f"needed_terms: {self.needed_terms}")
            invoice_date_due = self.needed_terms and max(
                (k['date_maturity'] for k in self.needed_terms.keys() if k),
                default=False,
            ) or self.invoice_date_due or fields.Date.context_today(self)
            debug_list.append(f"invoice_date_due set from invoice_payment_term_id: {invoice_date_due}")
        else:
            invoice_date_due = self.invoice_date_due
            debug_list.append(f"invoice_date_due set from self: {invoice_date_due}")

        # Set last day of delivery period month
        if period_enabled and period_end:
            # Get close to the end of the month and add 4 days to 'roll it over'
            period_next_month = period_end.replace(day=28) + datetime.timedelta(days=4)
            # Set the day to 1 gives us the start of next month
            period_first_day_of_next_month = period_next_month.replace(day=1)
            # Remove one day to get last day of this month
            period_month_last_day = period_first_day_of_next_month - datetime.timedelta(days=1)
        else:
            period_month_last_day = None

        # Set 60 days from period_end
        if period_enabled and period_end:
            period_end_plus_60 = period_end + datetime.timedelta(days=60)
        else:
            period_end_plus_60 = None

        # NAV SCENARIOS
        # 0) DEFAULT
        if delivery_date:
            scenario = '0_already_set'
        elif not delivery_date and delivery_date_default:
            scenario = '0_use_default'
            delivery_date = delivery_date_default
        else:
            scenario = '0_no_default'
        debug_list.append(f"delivery_date scenario 0: {scenario} - {delivery_date}")

        # 1) PERIOD END
        # Rule: period_end is set
        # Value: delivery_period_end
        if period_enabled and period_end:
            scenario = '1_period_end'
            delivery_date = period_end
        debug_list.append(f"delivery_date scenario 1: {scenario} - {delivery_date}")

        # 2) INVOICE DATE
        # Rule: BOTH invoice_date_due AND invoice_date are BEFORE period_end
        # Value: invoice_date
        if (period_enabled and invoice_date and invoice_date_due and period_end
                and invoice_date_due < period_end and invoice_date < period_end):
            scenario = '1a_invoice_date'
            delivery_date = invoice_date
        debug_list.append(f"delivery_date scenario 2: {scenario} - {delivery_date}")

        # 3) INVOICE DATE DUE (MAX 60)
        # Rule: invoice_date_due is AFTER period_end
        # Value: invoice_date_due (BUT max 60 days from period_end)
        if period_enabled and invoice_date_due and period_end and invoice_date_due > period_end:
            if invoice_date_due <= period_end_plus_60:
                scenario = '1b_invoice_date_due'
                delivery_date = invoice_date_due
            else:
                scenario = '1b_invoice_date_due_max_60'
                delivery_date = period_end_plus_60
        debug_list.append(f"delivery_date scenario 3: {scenario} - {delivery_date}")

        # period_summary
        period_summary = f"{_('Delivery period')}: {period_start} - {period_end}"

        # period_legal
        period_legal = "2007. CXXVII. 58.§"
        if scenario == '1a_invoice_date':
            period_legal += " (1) a)"
        elif scenario == '1b_invoice_date_due':
            period_legal += " (1) b)"
        elif scenario == '1b_invoice_date_due_max_60':
            period_legal += " (1) b) 60+ " + _("day")
        else:
            pass

        # Update result
        result.update({
            'accounting_date': accounting_date,
            'debug_list': debug_list,
            'delivery_date': delivery_date,
            'delivery_date_default': delivery_date_default,
            'error_list': error_list,
            'info_list': info_list,
            'invoice_date': invoice_date,
            'invoice_date_due': invoice_date_due,
            'l10n_hu_delivery_period_end': period_end,
            'l10n_hu_delivery_period_start': period_start,
            'period_enabled': period_enabled,
            'period_end_plus_60': period_end_plus_60,
            'period_legal': period_legal,
            'period_month_last_day': period_month_last_day,
            'period_scenario': scenario,
            'period_summary': period_summary,
            'warning_list': warning_list,
        })

        # Return result
        # raise exceptions.UserError("l10n_hu_plus_get_delivery_data" + "\n" + str(result))
        return result

    @api.model
    def l10n_hu_plus_get_document_data(self, values):
        """ Get document related data considering special hungarian rules

        NOTES:
        - This method only collects data, can be called by various other methods
        - is_storno_allowed: determine if storno is allowed for an account move
            - in certain cases (eg: issued to wrong partner) storno must be used instead of modification
            - we collect points, if all collected, storno is allowed
        - is_storno_invoice: determine if an account move is a storno invoice
            - Check storno by amount residual as suggested by Odoo
            - Odoo logic for storno: https://github.com/odoo/odoo/commit/5214296e8be76663ffdb6647c91645c66501121d

        :param values: dictionary

        :return: dictionary
        """
        # raise exceptions.UserError("l10n_hu_plus_get_document_data BEGIN" + str(values))

        # Initialize variables
        debug_list = []
        error_list = []
        info_list = []
        result = {}
        warning_list = []

        ## HUF VAT, document rate and amounts
        ### NOTES: document rate is NOT THE same as Odoo's invoice_currency_rate!
        ###        Odoo's invoice_currency_rate is used for accounting
        ###        Document rate is needed for VAT and can be a different rate
        ###        For example: vendor bill issuer might use different rate than our company for the same date
        huf_currency = self.env.ref('base.HUF')
        huf_rounding = huf_currency.decimal_places
        l10n_hu_document_rate = 1.0
        l10n_hu_document_vat_huf = values.get('l10n_hu_document_vat_huf', self.l10n_hu_document_vat_huf)
        if self.move_type in ['in_refund', 'out_refund'] and l10n_hu_document_vat_huf > 0:
            l10n_hu_document_vat_huf = l10n_hu_document_vat_huf * -1
        rate_rounding = 2

        ### CUSTOMER INVOICE - we issued it (Odoo or externally) so we must use accounting
        if self.move_type in ['out_invoice', 'out_refund']:
            amount_sign = -1 if self.move_type == 'out_refund' else 1
            # HUF invoice and HUF accounting
            if self.currency_id.name == 'HUF' and self.company_id.currency_id.name == 'HUF':
                l10n_hu_document_rate = 1.0
                l10n_hu_document_vat_huf = self.amount_tax_signed
            # NOT HUF invoice and HUF accounting: derive document VAT HUF from NAV rate (see #76, #3832)
            elif (self.currency_id.name != 'HUF' and self.company_id.currency_id.name == 'HUF'
                    and self.invoice_currency_rate != 0):
                l10n_hu_document_rate = 1 / self.invoice_currency_rate
                l10n_hu_document_vat_huf = huf_currency.round(self.amount_tax * l10n_hu_document_rate * amount_sign)
            # HUF invoice and NOT HUF accounting: use stored HU+ HUF Rate when set
            elif self.currency_id.name == 'HUF' and self.company_id.currency_id.name != 'HUF':
                l10n_hu_document_rate = self.l10n_hu_huf_rate or self._l10n_hu_get_currency_rate()
                l10n_hu_document_vat_huf = huf_currency.round(self.amount_tax * l10n_hu_document_rate * amount_sign)
            # NOT HUF invoice and NOT HUF accounting: Document HUF follows stored HU+ HUF Rate
            elif self.currency_id.name != 'HUF' and self.company_id.currency_id.name != 'HUF':
                l10n_hu_document_rate = self.l10n_hu_huf_rate or self._l10n_hu_get_currency_rate()
                l10n_hu_document_vat_huf = huf_currency.round(self.amount_tax * l10n_hu_document_rate * amount_sign)
            else:
                pass
        ### VENDOR BILL - we received it from vendor, we want to record the vendor's data
        elif self.move_type in ['in_invoice', 'in_refund']:
            amount_sign = -1 if self.move_type == 'in_refund' else 1
            # amount_tax and is l10n_hu_document_vat_huf not 0
            if l10n_hu_document_vat_huf != 0 and self.amount_tax != 0:
                l10n_hu_document_rate = l10n_hu_document_vat_huf / self.amount_tax * amount_sign
                debug_list.append(f"document rate vendor bill VAT HUF != 0 and amount_tax != 0: {l10n_hu_document_rate}")
            # amount_total not 0 and foreign ccy and HUF accounting
            elif self.amount_total != 0 and self.currency_id != self.company_id.currency_id and self.company_id.currency_id.name == 'HUF':
                l10n_hu_document_rate = abs(self.amount_total_signed) / abs(self.amount_total)
                debug_list.append(f"document rate vendor bill HUF company amount total!=0: {l10n_hu_document_rate}")
            # amount_total 0 and foreign ccy and HUF accounting
            elif self.amount_total == 0 and self.currency_id != self.company_id.currency_id and self.company_id.currency_id.name == 'HUF':
                l10n_hu_document_rate = tools.float_round(self.l10n_hu_invoice_currency_rate_inverse, rate_rounding)
                debug_list.append(f"document rate vendor bill HUF company HUF ccy amount_total==0: {l10n_hu_document_rate}")
            # NOT HUF accounting
            elif self.company_id.currency_id.name != 'HUF':
                l10n_hu_document_rate = self._l10n_hu_get_currency_rate()
                debug_list.append(f"document rate vendor bill NOT HUF company: {l10n_hu_document_rate}")
            else:
                pass
        else:
            amount_sign = 1

        # HUF document net and gross
        l10n_hu_document_net_huf = huf_currency.round(self.amount_untaxed * l10n_hu_document_rate * amount_sign)
        l10n_hu_document_gross_huf = l10n_hu_document_vat_huf + l10n_hu_document_net_huf

        # HUF AMOUNT DIFF AND SUMMARY
        accounting_amount_untaxed = self.amount_untaxed * l10n_hu_document_rate * amount_sign
        accounting_amount_tax = self.amount_tax * l10n_hu_document_rate * amount_sign
        accounting_amount_total = self.amount_total * l10n_hu_document_rate * amount_sign
        huf_amount_diff = False
        huf_amount_gross_diff = 0
        huf_amount_net_diff = 0
        huf_amount_vat_diff = 0
        if self.company_id.currency_id.name == 'HUF':
            huf_amount_net_diff = tools.float_round(accounting_amount_untaxed - l10n_hu_document_net_huf, huf_rounding)
            huf_amount_vat_diff = tools.float_round(accounting_amount_tax - l10n_hu_document_vat_huf, huf_rounding)
            huf_amount_gross_diff = tools.float_round(accounting_amount_total - l10n_hu_document_gross_huf, huf_rounding)
            if (not self._l10n_hu_is_within_document_huf_tolerance(huf_amount_net_diff)
                    or not self._l10n_hu_is_within_document_huf_tolerance(huf_amount_vat_diff)
                    or not self._l10n_hu_is_within_document_huf_tolerance(huf_amount_gross_diff)):
                huf_amount_diff = True
            huf_amount_summary = (f"{_('Document HUF amounts')}: "
            f" {_('Net difference')} {huf_amount_net_diff} ({accounting_amount_untaxed} - {self.l10n_hu_document_net_huf});"
            f" {_('VAT difference')} {huf_amount_vat_diff} ({accounting_amount_tax} - {self.l10n_hu_document_vat_huf});"
            f" {_('Gross difference')} {huf_amount_gross_diff} ({accounting_amount_total} - {self.l10n_hu_document_gross_huf})")
        else:
            huf_amount_summary = (f"{_('Document HUF amounts')}: "
                                  f" {_('Net difference')} {huf_amount_net_diff} ({self.l10n_hu_document_net_huf});"
                                  f" {_('VAT difference')} {huf_amount_vat_diff} ({self.l10n_hu_document_vat_huf});"
                                  f" {_('Gross difference')} {huf_amount_gross_diff} ({self.l10n_hu_document_gross_huf})")

        # MODIFICATION
        modification_document_type = self.env['l10n.hu.plus.tag'].search([
            ('company', '=', self.company_id.id),
            ('tag_type', '=', 'document_type'),
            ('technical_name', '=', 'invoice_modification'),
        ], limit=1)

        # STORNO
        ## Storno document type
        storno_document_type = self.env['l10n.hu.plus.tag'].search([
            ('company', '=', self.company_id.id),
            ('tag_type', '=', 'document_type'),
            ('technical_name', '=', 'invoice_storno'),
        ], limit=1)

        ## is_storno_invoice
        base_invoice = self._l10n_hu_get_chain_base()
        if self.move_type == 'out_refund' and self != base_invoice and base_invoice.amount_residual == 0:
            is_storno_invoice = True
        else:
            is_storno_invoice = False

        ## is_storno_allowed
        if (storno_document_type and self.move_type == 'out_invoice' and self.state == 'posted'
                and not self.reversed_entry_id and not self.l10n_hu_original_invoice_number):
            is_storno_allowed = True
        else:
            is_storno_allowed = False

        # DOCUMENT TYPE
        l10n_hu_document_type = values.get('l10n_hu_document_type', self.l10n_hu_document_type)
        if not l10n_hu_document_type and self.move_type in ['in_invoice', 'out_invoice']:
            l10n_hu_document_type = self.journal_id.l10n_hu_get_default_document_type()
        elif not l10n_hu_document_type and self.move_type == 'out_refund' and is_storno_invoice and storno_document_type:
            l10n_hu_document_type = storno_document_type
        elif not l10n_hu_document_type and self.move_type == 'out_refund' and modification_document_type:
            l10n_hu_document_type = modification_document_type
        else:
            pass

        # Update result
        result.update({
            'debug_list': debug_list,
            'error_list': error_list,
            'huf_amount_diff': huf_amount_diff,
            'huf_amount_gross_diff': huf_amount_gross_diff,
            'huf_amount_net_diff': huf_amount_net_diff,
            'huf_amount_vat_diff': huf_amount_vat_diff,
            'huf_amount_summary': huf_amount_summary,
            'info_list': info_list,
            'is_storno_allowed': is_storno_allowed,
            'is_storno_invoice': is_storno_invoice,
            'l10n_hu_document_gross_huf': l10n_hu_document_gross_huf,
            'l10n_hu_document_net_huf': l10n_hu_document_net_huf,
            'l10n_hu_document_rate': l10n_hu_document_rate,
            'l10n_hu_document_type': l10n_hu_document_type,
            'l10n_hu_document_vat_huf': l10n_hu_document_vat_huf,
            'modification_document_type': modification_document_type,
            'storno_document_type': storno_document_type,
            'warning_list': warning_list,
        })

        # Return result
        # raise exceptions.UserError("l10n_hu_plus_get_document_data" + "\n" + str(result))
        return result

    @api.model
    def l10n_hu_plus_get_rate_data(self, values):
        """ Get currency related data considering special hungarian rules

        NOTES:
        - This method only collects data, can be called by various other methods
        - we collect all HU relevant information (currencies, rates, etc..)
        - TODO write documentation:
            - expected_rate (accounting_rate) vs invoice_currency_rate (document rate)
            - issue_date vs delivery_date vs currency_rate_date

        :param values: dictionary

        :return: dictionary
        """
        # raise exceptions.UserError("l10n_hu_plus_get_rate_data BEGIN" + str(values))

        # Initialize variables
        debug_list = []
        error_list = []
        info_list = []
        result = {}
        warning_list = []

        # CURRENCIES
        company_currency = self.company_id.currency_id
        huf_currency = self.env.ref('base.HUF')
        invoice_currency = self.currency_id
        rate_rounding = 2

        # DATES
        delivery_date = values.get('delivery_date', self.delivery_date)
        invoice_date = values.get('invoice_date', self.invoice_date)

        ## currency_rate_date
        ## NOTES: if the invoice was issued before the delivery date then
        ##        that means that the rate for the delivery date did nto exist yet
        ##        so we use the rate for the issue date
        if delivery_date and invoice_date and delivery_date > invoice_date:
            currency_rate_date = invoice_date
        elif delivery_date:
            currency_rate_date = delivery_date
        else:
            currency_rate_date = fields.Date.today()

        # Float rates
        ## Odoo rates
        expected_currency_rate = self.expected_currency_rate
        invoice_currency_rate = values.get('invoice_currency_rate', self.invoice_currency_rate)

        ## Inverse rates
        if invoice_currency_rate != 0:
            l10n_hu_invoice_currency_rate_inverse = 1 / invoice_currency_rate
        else:
            l10n_hu_invoice_currency_rate_inverse = 0.0
        if expected_currency_rate != 0:
            expected_currency_rate_inverse = 1 / expected_currency_rate
        else:
            expected_currency_rate_inverse = 0.0

        ## HU+ document rate
        document_rate = values.get('l10n_hu_document_rate', self.l10n_hu_document_rate)

        # Rate objects (res.currency.rate)
        ## HU+ delivery_date_rcr
        if delivery_date:
            delivery_date_rcr = self.env['res.currency.rate'].search([
                ('company_id', '=', self.company_id.id),
                ('currency_id', '=', invoice_currency.id),
                ('name', '<=', delivery_date)
            ], limit=1)
        else:
            delivery_date_rcr = None

        ## HU+ invoice_date_rcr
        if invoice_date:
            invoice_date_rcr = self.env['res.currency.rate'].search([
                ('company_id', '=', self.company_id.id),
                ('currency_id', '=', invoice_currency.id),
                ('name', '<=', invoice_date)
            ], limit=1)
        else:
            invoice_date_rcr = None

        ## HU+ accounting_rate
        accounting_date = currency_rate_date
        accounting_rcr = self.env['res.currency.rate'].search([
            ('company_id', '=', self.company_id.id),
            ('currency_id', '=', invoice_currency.id),
            ('name', '<=', accounting_date)
        ], limit=1)
        debug_list.append("accounting_rcr set for foreign currency")
        if accounting_rcr:
            accounting_rate = accounting_rcr.company_rate
            debug_list.append(f"accounting_rate set: {accounting_rate}")
        else:
            accounting_rate = 0.0
            debug_list.append("accounting_rcr not found, it is set to default 0.0")

        ## HU+ huf_rate
        huf_rate = 0.0
        ### Company HUF AND invoice HUF
        if company_currency.name == 'HUF' and invoice_currency.name == 'HUF':
            huf_rate = 1.0
            debug_list.append("huf_rate is 1.0000 for HUF invoice currency and HUF company currency")
        ## Company NOT HUF or invoice NOT HUF
        elif (company_currency.name != 'HUF' or invoice_currency.name != 'HUF') and currency_rate_date:
            huf_rate_rcr = self.env['res.currency.rate'].search([
                ('company_id', '=', self.company_id.id),
                ('currency_id', '=', huf_currency.id),
                ('name', '<=', currency_rate_date)
            ], limit=1)
            debug_list.append(f"huf_rate_rcr: {huf_rate_rcr}")
            if huf_rate_rcr:
                debug_list.append(f"huf_rate_rcr company_rate: {huf_rate_rcr.company_rate}")
                debug_list.append(f"huf_rate_rcr inverse_company_rate: {huf_rate_rcr.inverse_company_rate}")

            # NOTES: we use the same method as in l10n_hu_edi app
            huf_rate = self._l10n_hu_get_currency_rate()
            debug_list.append(f"huf_rate _l10n_hu_get_currency_rate: {huf_rate}")
        else:
            debug_list.append("huf_rate else scenario, probably currency_rate_date is not set")

        ## SPECIAL CASE: invoice_date < delivery_date (periodic delivery)
        ## - customer invoice issued externally and downloaded
        ## - vendor bill
        ## NOTES: we need to do accounting for the invoice_date
        if (self.move_type in ['in_invoice', 'in_refund'] and invoice_date and delivery_date
                and invoice_date < delivery_date):
            invoice_currency_rate = invoice_date_rcr.company_rate
            debug_list.append(f"inbound invoice special: {invoice_date}<{delivery_date} = {invoice_currency_rate}")

        # l10n_hu_invoice_currency_rate_date
        l10n_hu_invoice_currency_rate_date = self._get_invoice_currency_rate_date()
        if l10n_hu_invoice_currency_rate_date > currency_rate_date:
            l10n_hu_invoice_currency_rate_date = currency_rate_date

        # document_rate_diff
        document_rate_diff = tools.float_round(l10n_hu_invoice_currency_rate_inverse, rate_rounding) - tools.float_round(document_rate, rate_rounding)

        # currency_summary
        if company_currency == invoice_currency:
            currency_summary = _("This document uses the company currency")
        else:
            currency_summary = (f"{_('Currency rate')}: {l10n_hu_invoice_currency_rate_date}")

            # Currency rate
            if company_currency.name == 'HUF':
                currency_summary += f" {tools.float_round(l10n_hu_invoice_currency_rate_inverse, rate_rounding)}"
            else:
                currency_summary += f" {invoice_currency_rate}"

            # Expected rate
            if tools.float_round(l10n_hu_invoice_currency_rate_inverse, rate_rounding) != tools.float_round(expected_currency_rate_inverse, rate_rounding):
                currency_summary += (f" {_('Expected')}: {tools.float_round(expected_currency_rate_inverse, rate_rounding)}"
                                     f" {company_currency.name}/{invoice_currency.name}")

            # Document HUF
            if self.move_type in ['in_invoice', 'in_refund']:
                currency_summary += (f" {_('Document')}: {tools.float_round(document_rate, rate_rounding)}"
                                     f" {company_currency.name}/{invoice_currency.name}")

            # Rate difference
            if document_rate_diff != 0:
                currency_summary += f" {_('Rate difference')}: {tools.float_round(document_rate_diff, rate_rounding)}"

        # HUF rate
        if company_currency.name != 'HUF' or invoice_currency.name != 'HUF':
            currency_summary += (f" {_('HUF rate')}: {tools.float_round(huf_rate, rate_rounding)} "
                                 f" {huf_currency.name}/{invoice_currency.name}")

        # Update result
        result.update({
            'accounting_rate': accounting_rate,
            'currency_summary': currency_summary,
            'debug_list': debug_list,
            'delivery_date': delivery_date,
            'document_rate_diff': document_rate_diff,
            'error_list': error_list,
            'expected_currency_rate': expected_currency_rate,
            'expected_currency_rate_inverse': expected_currency_rate_inverse,
            'info_list': info_list,
            'invoice_currency_rate': invoice_currency_rate,
            'invoice_date': invoice_date,
            'l10n_hu_document_rate': document_rate,
            'l10n_hu_huf_currency': huf_currency,
            'l10n_hu_huf_rate': huf_rate,
            'l10n_hu_invoice_currency_rate_date': l10n_hu_invoice_currency_rate_date,
            'l10n_hu_invoice_currency_rate_inverse': l10n_hu_invoice_currency_rate_inverse,
            'res_currency_rate_accounting': accounting_rcr,
            'res_currency_rate_invoice_date': invoice_date_rcr,
            'res_currency_rate_delivery_date': delivery_date_rcr,
            'warning_list': warning_list,
        })

        # Return result
        # raise exceptions.UserError(f"l10n_hu_plus_get_rate_data\n{result}")
        return result

    @api.model
    def l10n_hu_plus_get_vat_data(self, values):
        """ Collect vat related data

        NOTES:
        - cash_accounting_summary: text summary for cash accounting
        - is_cash_accounting: cash accounting is relevant or not
        - l10n_hu_cash_accounting: value for the account move field
        - l10n_hu_vat_date: date of next VAT declaration
        - l10n_hu_vat_status: VAT status of the document

        :param values: dictionary

        :return: dictionary
        """
        # raise exceptions.UserError("l10n_hu_plus_get_vat_data BEGIN" + str(values))

        # Initialize variables
        debug_list = []
        error_list = []
        info_list = []
        result = {}
        warning_list = []

        # delivery_date
        delivery_date = values.get('delivery_date', self.delivery_date)

        # is_cash_accounting
        is_cash_accounting = False
        cash_accounting_summary = _("Cash accounting is not applicable for the invoice")
        if self.is_invoice(True) and self.state == 'draft':
            if (self.move_type in ['in_invoice', 'in_refund'] and self.partner_id
                    and self.partner_id.property_account_position_id
                    and self.partner_id.property_account_position_id.l10n_hu_trade_position == 'domestic'
                    and self.partner_id.property_account_position_id.l10n_hu_tax_regime == 'ca'):
                is_cash_accounting = True
                cash_accounting_summary = _("Domestic invoice issuer applies cash accounting")
            elif (self.partner_id and self.partner_id.property_account_position_id
                  and self.partner_id.property_account_position_id.l10n_hu_trade_position == 'domestic'
                  and self.company_id.l10n_hu_tax_regime == 'ca'):
                is_cash_accounting = True
                cash_accounting_summary = _("Domestic partner and company applies cash accounting")
            else:
                pass
        else:
            pass

        # l10n_hu_cash_accounting
        if self.state == 'draft' and is_cash_accounting:
            l10n_hu_cash_accounting = is_cash_accounting
        else:
            l10n_hu_cash_accounting = self.l10n_hu_cash_accounting

        # Taxes
        ## In case of cash accounting we check if the applied taxes are set to use cash accounting
        cash_accounting_taxes = []
        taxes = []
        vat_taxes = []
        if l10n_hu_cash_accounting:
            for invoice_line in self.invoice_line_ids:
                if invoice_line.product_id:
                    for tax in invoice_line.tax_ids:
                        if tax not in taxes:
                            taxes.append(tax)
                        if tax.l10n_hu_tax_type == 'VAT':
                            if tax not in vat_taxes:
                                vat_taxes.append(tax)
                            if tax.tax_exigibility == 'on_payment' and tax not in cash_accounting_taxes:
                                cash_accounting_taxes.append(tax)

        # l10n_hu_vat_status
        l10n_hu_vat_status = values.get('l10n_hu_vat_status', self.l10n_hu_vat_status)
        if not l10n_hu_vat_status and not is_cash_accounting:
            l10n_hu_vat_status = 'to_declare'

        # l10n_hu_vat_date
        l10n_hu_vat_date = values.get('l10n_hu_vat_date', self.l10n_hu_vat_date)
        if not l10n_hu_vat_date and not is_cash_accounting and l10n_hu_vat_status == 'to_declare':
            l10n_hu_vat_date = delivery_date

        # Update result
        result.update({
            'cash_accounting_summary': cash_accounting_summary,
            'cash_accounting_taxes': cash_accounting_taxes,
            'debug_list': debug_list,
            'error_list': error_list,
            'info_list': info_list,
            'is_cash_accounting': is_cash_accounting,
            'l10n_hu_cash_accounting': l10n_hu_cash_accounting,
            'l10n_hu_vat_date': l10n_hu_vat_date,
            'l10n_hu_vat_status': l10n_hu_vat_status,
            'taxes': taxes,
            'vat_taxes': vat_taxes,
            'warning_list': warning_list,
        })

        # Return result
        # raise exceptions.UserError("l10n_hu_plus_get_vat_data END" + str(result))
        return result

    ## HU+ EDI
    @api.model
    def l10n_hu_do_send_edi(self):
        """ Shorthand method to send invoice to EDI (NAV Online Szamla) without user interaction

        :return: boolean
        """
        if self.l10n_hu_get_send_edi_allowed():
            if self.journal_id.l10n_hu_edi_sending == 'auto_edi_email':
                mail_template = self.l10n_hu_get_send_invoice_mail_template()
                self.env['account.move.send']._generate_and_send_invoices(self, sending_methods=['email'], mail_template=mail_template)
            else:
                self.env['account.move.send']._generate_and_send_invoices(self, sending_methods=[])
            return True
        else:
            return False

    @api.model
    def l10n_hu_get_send_edi_allowed(self):
        """ Determine if EDI send is allowed for an account move

        NOTES:
        - we have a method because it is too complex to be handled by a domain
        - you can override with super if you want to check more conditions
        - we collect points, if all collected, it is allowed

        :return: boolean
        """
        # Initialize variables
        points = 0

        # 1) Company NAV connection configured
        if self.company_id.l10n_hu_edi_server_mode and self.company_id.l10n_hu_edi_server_mode in ['production', 'test']:
            points += 1

        # 2) Journal EDI automation is enabled
        if self.journal_id.l10n_hu_edi_sending in ['auto_edi', 'auto_edi_email']:
            points += 1

        # 3) Journal type
        if self.journal_id.type == 'sale':
            points += 1

        # 4) Move EDI state
        if not self.l10n_hu_edi_state:
            points += 1

        # 5) Move HU+ status
        if self.l10n_hu_plus_status != 'closed':
            points += 1

        # 6) Move type
        if self.move_type in ['out_invoice', 'out_refund']:
            points += 1

        # 7) Move state
        if self.state == 'posted':
            points += 1

        # 8) Move invoice date today
        if self.invoice_date == fields.Date.today():
            points += 1

        # Return
        if points == 8:
            return True
        else:
            return False

    @api.model
    def l10n_hu_get_send_invoice_mail_template(self):
        """ Get mail template to send out invoice email"""
        return self.env.ref('account.email_template_edi_invoice')

    ## HU+ STATUS
    @api.model
    def l10n_hu_get_plus_status(self):
        """ Get HU+ status

        NOTES:
        - meant to be used by automations
        - meant to be overridden by super for customizations

        :return: dictionary
        """
        # Do not modify closed and other
        if self.l10n_hu_plus_status in ['closed', 'other']:
            return self.l10n_hu_plus_status
        else:
            # Run checklist and determine status
            checklist_result = self.l10n_hu_get_plus_status_checklist()
            error_list = checklist_result.get('error_list', [])
            # info_list = checklist_result.get('info_list', [])
            success_list = checklist_result.get('success_list', [])
            warning_list = checklist_result.get('warning_list', [])
            if len(error_list) > 0:
                return 'error'
            elif len(warning_list) > 0:
                return 'warning'
            elif len(success_list) > 0:
                return 'ok'
            else:
                return None

    @api.model
    def l10n_hu_get_plus_status_checklist(self):
        """ Get HU+ status checklist

        NOTES:
        - we run here a lot of status checks
        - Odoo _l10n_hu_edi_check_invoices() method is not included as it returns only errors when posting

        :return: dictionary
        """
        # Initialize variables
        debug_list = []
        error_list = []
        info_list = []
        result = {}
        success_list = []
        warning_list = []

        # Odoo errors (actually, no need to include, it returns only errors for invoice issue)
        """
        l10n_hu_edi_error_dict = self._l10n_hu_edi_check_invoices()
        for check, values in l10n_hu_edi_error_dict.items():
            l10n_hu_edi_error = {
                'action_text': values.get('action_text', ""),
                'code': check,
                'description': values.get('message', ""),
                'records': values.get('records', None),
                'result': 'error'
            }
            error_list.append(l10n_hu_edi_error)
        """

        # HU+0: collect data using dedicated methods
        delivery_data = self.l10n_hu_plus_get_delivery_data({})
        document_data = self.l10n_hu_plus_get_document_data({})
        rate_data = self.l10n_hu_plus_get_rate_data({})
        vat_data = self.l10n_hu_plus_get_vat_data({})

        # HU+1: document type
        if self.l10n_hu_document_type:
            success_list.append({
                'action_text': None,
                'code': 'HU+1',
                'description': _("Document type set") + ": " + str(self.l10n_hu_document_type.display_name),
                'records': self.l10n_hu_document_type,
                'result': 'ok',
            })
        else:
            warning_list.append({
                'action_text': None,
                'code': 'HU+1',
                'description': _("Document type not set"),
                'records': None,
                'result': 'warning',
            })

        # HU+2: account move fiscal position
        if self.fiscal_position_id:
            success_list.append({
                'action_text': None,
                'code': 'HU+2',
                'description': _("Invoice fiscal position set") + ": " + str(self.fiscal_position_id.display_name),
                'records': self.filtered(lambda am: am.fiscal_position_id),
                'result': 'ok',
            })
        else:
            warning_list.append({
                'action_text': None,
                'code': 'HU+2',
                'description': _("Invoice fiscal position not set"),
                'records': self.filtered(lambda am: not am.fiscal_position_id),
                'result': 'warning',
            })

        # HU+3: partner fiscal position
        if self.partner_id.property_account_position_id:
            success_list.append({
                'action_text': None,
                'code': 'HU+3',
                'description': _("Partner fiscal position set") + ": " + self.partner_id.property_account_position_id.display_name,
                'records': self.partner_id.commercial_partner_id.filtered(lambda p: p.property_account_position_id),
                'result': 'ok',
            })
        else:
            warning_list.append({
                'action_text': None,
                'code': 'HU+3',
                'description': _("Partner fiscal position not set"),
                'records': self.partner_id.commercial_partner_id.filtered(lambda p: not p.property_account_position_id),
                'result': 'warning',
            })

        # HU+4: delivery date
        if self.delivery_date:
            success_list.append({
                'action_text': None,
                'code': 'HU+4',
                'description': _("Delivery date set") + ": " + str(self.delivery_date),
                'records': self,
                'result': 'ok',
            })
        else:
            error_list.append({
                'action_text': None,
                'code': 'HU+4',
                'description': _("Delivery date not set"),
                'records': self,
                'result': 'error',
            })

        # HU+5: delivery period
        l10n_hu_delivery_period_end = delivery_data.get('l10n_hu_delivery_period_end', None)
        l10n_hu_delivery_period_start = delivery_data.get('l10n_hu_delivery_period_start', None)
        period_legal = delivery_data.get('period_legal', None)
        hu_5_description = str(l10n_hu_delivery_period_start)
        hu_5_description += " - "
        hu_5_description += str(l10n_hu_delivery_period_end)
        if l10n_hu_delivery_period_start and l10n_hu_delivery_period_end:
            ## for outgoing invoices
            if self.move_type in ['out_invoice', 'out_refund'] and period_legal:
                hu_5_description += f" ({period_legal})"
            success_list.append({
                'action_text': None,
                'code': 'HU+5',
                'description': _("Delivery period set") + ": " + hu_5_description,
                'records': self,
                'result': 'info',
            })
        elif l10n_hu_delivery_period_start and not l10n_hu_delivery_period_end:
            error_list.append({
                'action_text': None,
                'code': 'HU+5',
                'description': _("Delivery period not set") + ": " + hu_5_description,
                'records': self,
                'result': 'error',
            })
        elif not l10n_hu_delivery_period_start and l10n_hu_delivery_period_end:
            error_list.append({
                'action_text': None,
                'code': 'HU+5',
                'description': _("Delivery period not set") + ": " + hu_5_description,
                'records': self,
                'result': 'error',
            })
        else:
            info_list.append({
                'action_text': None,
                'code': 'HU+5',
                'description': _("Delivery period not set"),
                'records': self,
                'result': 'info',
            })

        # HU+6: taxes
        no_tax_lines = []
        for line in self.invoice_line_ids:
            if line.account_id and not line.tax_ids:
                no_tax_lines.append(line)
        if len(no_tax_lines) == 0:
            success_list.append({
                'action_text': None,
                'code': 'HU+6',
                'description': _("Tax is set on all invoice lines"),
                'records': self,
                'result': 'success',
            })
        else:
            error_list.append({
                'action_text': None,
                'code': 'HU+6',
                'description': _("Tax must be set on all invoice lines"),
                'records': self,
                'result': 'error',
            })

        # HU+7: Document rate amounts
        if rate_data.get('document_rate_diff') and rate_data['document_rate_diff'] != 0:
            warning_list.append({
                'action_text': None,
                'code': 'HU+7',
                'description': str(rate_data.get('currency_summary', "")),
                'records': self,
                'result': 'warning',
            })
        elif rate_data.get('document_rate_diff') and rate_data['document_rate_diff'] == 0:
            success_list.append({
                'action_text': None,
                'code': 'HU+7',
                'description': str(rate_data.get('currency_summary', "")),
                'records': self,
                'result': 'success',
            })
        else:
            info_list.append({
                'action_text': None,
                'code': 'HU+7',
                'description': str(rate_data.get('currency_summary', "")),
                'records': self,
                'result': 'info',
            })

        # HU+8: Document HUF amounts
        if document_data.get('huf_amount_diff'):
            warning_list.append({
                'action_text': None,
                'code': 'HU+8',
                'description': str(document_data.get('huf_amount_summary', "")),
                'records': self,
                'result': 'warning',
            })
        else:
            info_list.append({
                'action_text': None,
                'code': 'HU+8',
                'description': str(document_data.get('huf_amount_summary', "")),
                'records': self,
                'result': 'info',
            })

        # HU+9: Cash accounting setting
        if vat_data.get('l10n_hu_cash_accounting') != self.l10n_hu_cash_accounting:
            warning_list.append({
                'action_text': None,
                'code': 'HU+9',
                'description': _("Cash accounting setting for document is inconsistent with partner settings"),
                'records': self,
                'result': 'warning',
            })
        else:
            hu_9_info_text = _("Document cash accounting setting") + ": "
            if self.l10n_hu_cash_accounting:
                hu_9_info_text += _("Yes")
            else:
                hu_9_info_text += _("No")
            info_list.append({
                'action_text': None,
                'code': 'HU+9',
                'description': hu_9_info_text,
                'records': self,
                'result': 'info',
            })

        # HU+10: Cash accounting taxes
        cash_accounting_taxes = vat_data.get('cash_accounting_taxes', [])
        vat_taxes = vat_data.get('vat_taxes', [])
        if vat_data.get('l10n_hu_cash_accounting') and len(cash_accounting_taxes) == len(vat_taxes):
            success_list.append({
                'action_text': None,
                'code': 'HU+10',
                'description': _("Cash accounting is set and all applied VAT taxes are set to on payment"),
                'records': self,
                'result': 'warning',
            })
        elif vat_data.get('l10n_hu_cash_accounting') and len(cash_accounting_taxes) != len(vat_taxes):
            warning_list.append({
                'action_text': None,
                'code': 'HU+10',
                'description': _("Cash accounting is set, but not all applied VAT taxes are set to on payment"),
                'records': self,
                'result': 'warning',
            })
        else:
            info_list.append({
                'action_text': None,
                'code': 'HU+10',
                'description': _("Cash accounting is not set, on payment tax check skipped"),
                'records': self,
                'result': 'info',
            })

        # HU+11: cash accounting summary
        info_list.append({
            'action_text': None,
            'code': 'HU+11',
            'description': str(vat_data.get('cash_accounting_summary', "")),
            'records': self,
            'result': 'info',
        })

        # HU+12: customer address
        address_error_text = f""
        if not self.partner_id:
            address_error_text += f"{_('Customer is not set!')} "
        if self.partner_id and not self.partner_id.zip:
            address_error_text += f"{_('Postal code is empty!')} "
        if self.partner_id and not self.partner_id.country_id:
            address_error_text += f"{_('Country is empty!')} "
        if self.partner_id and not self.partner_id.city:
            address_error_text += f"{_('City is empty!')} "
        if self.partner_id and not self.partner_id.street:
            address_error_text += f"{_('Street is empty!')} "

        if len(address_error_text) > 0:
            address_error_text = f"{_('Customer address error!')} " + address_error_text
            error_list.append({
                'action_text': None,
                'code': 'HU+12',
                'description': address_error_text,
                'records': self,
                'result': 'error',
            })
        else:
            success_list.append({
                'action_text': None,
                'code': 'HU+12',
                'description': f"{_('Customer address details ok')}",
                'records': self,
                'result': 'success',
            })

        # Update result
        result.update({
            'debug_list': debug_list,
            'error_list': error_list,
            'info_list': info_list,
            'success_list': success_list,
            'warning_list': warning_list,
        })

        # Return result
        return result

    @api.model
    def l10n_hu_get_plus_status_overview(self):
        """ Get HU+ status overview as an HTML table

        NOTES:
        - we return status check results
        - we also return an overview html table assembled by a different method

        @return: string (HTML syntax)
        """
        # Initialize variables
        result = ""

        # Run status check
        checklist_result = self.l10n_hu_get_plus_status_checklist()
        error_list = checklist_result.get('error_list', [])
        info_list = checklist_result.get('info_list', [])
        success_list = checklist_result.get('success_list', [])
        warning_list = checklist_result.get('warning_list', [])

        # Counts
        error_count = len(error_list)
        info_count = len(info_list)
        success_count = len(success_list)
        warning_count = len(warning_list)
        total_count = error_count + info_count + success_count + warning_count
        if total_count > 0:
            error_rate = error_count / total_count
            info_rate = info_count / total_count
            success_rate = success_count / total_count
            warning_rate = warning_count / total_count
            bad_count = error_count + (warning_count * 0.5)
            health_rate = int(tools.float_round(((total_count - bad_count) / total_count * 100), 0))
        else:
            error_rate = 0
            info_rate = 0
            success_rate = 0
            warning_rate = 0
            health_rate = 0

        # Assemble table
        ### TITLE
        result += '<h2 class="text-center mt-4">'
        result += str(self.display_name)
        result += '</h2>'
        ### SUBTITLE
        result += '<div class="fw-bold text-center mb-2">'
        result += _("HU+ check result")
        result += " " + str(fields.Datetime.now())
        result += " " + str(health_rate) + "%"
        result += '</div>'
        ### STATS
        result += '<div class="row p-1 mt-2 mb-2">'  # div row BEGIN
        result += '<div class="col-3 text-center text-uppercase text-danger">'
        result += '<span class="fa fa-exclamation-circle text-danger pe-1"/>'
        result += '<span class="fw-bold">' + _("Error") + ": " + str(error_count) + '</span>'
        # result += '<span class="fst-italic text-muted">' + str(error_rate) + '</span>'
        result += '</div>'
        result += '<div class="col-3 text-center text-uppercase text-warning">'
        result += '<span class="fa fa-exclamation-triangle text-warning pe-1"/>'
        result += '<span class="fw-bold">' + _("Warning") + ": " + str(warning_count) + '</span>'
        # result += '<span class="fst-italic ps-1 text-muted">' + str(warning_rate) + '</span>'
        result += '</div>'
        result += '<div class="col-3 text-center text-uppercase text-success">'
        result += '<span class="fa fa-check text-success pe-1"/>'
        result += '<span class="fw-bold">' + _("Success") + ": " + str(success_count) + '</span>'
        # result += '<span class="fst-italic ps-1 text-muted">' + str(success_rate) + '</span>'
        result += '</div>'
        result += '<div class="col-3 text-center text-uppercase text-info">'
        result += '<span class="fa fa-info-circle text-info pe-1"/>'
        result += '<span class="fw-bold">' + _("Information") + ": " + str(info_count) + '</span>'
        # result += '<span class="fst-italic ps-1 text-muted">' + str(info_rate) + '</span>'
        result += '</div>'
        result += '</div>'  # div row END
        ## TABLE BEGIN
        result += '<table class="table table-bordered table-sm" style="width:100%;">'
        ## THEAD BEGIN
        result += '<thead>'
        ### TH COLUMN NAMES
        result += '<tr>'
        result += '<th class="text-center" style="width:10%;">'
        result += _("Result")  # Result (eg: error, info, ok, other, warning)
        result += '</th>'
        result += '<th class="text-center" style="width:10%;">'
        result += _("Code")  # Code
        result += '</th>'
        result += '<th class="text-center" style="width:80%;">'
        result += _("Description")  # Description
        result += '</th>'
        result += '</tr>'
        ## THEAD END
        result += '</thead>'
        ## TBODY BEGIN
        result += '<tbody>'
        ### 1) errors
        for error_item in error_list:
            result += '<tr>'
            result += '<td class="text-center">'
            result += '<span class="fa fa-exclamation-circle text-danger me-2"/>'
            result += '</td>'
            result += '<td>'
            result += error_item.get('code', "-")
            result += '</td>'
            result += '<td>'
            result += error_item.get('description', "-")
            result += '</td>'
            result += '<tr>'
        ### 2) warnings
        for warning_item in warning_list:
            result += '<tr>'
            result += '<td class="text-center">'
            result += '<span class="fa fa-exclamation-triangle text-warning me-2"/>'
            result += '</td>'
            result += '<td>'
            result += warning_item.get('code', "-")
            result += '</td>'
            result += '<td>'
            result += warning_item.get('description', "-")
            result += '</td>'
            result += '<tr>'
        ### 3) success
        for success_item in success_list:
            result += '<tr>'
            result += '<td class="text-center">'
            result += '<span class="fa fa-check text-success me-2"/>'
            result += '</td>'
            result += '<td>'
            result += success_item.get('code', "-")
            result += '</td>'
            result += '<td>'
            result += success_item.get('description', "-")
            result += '</td>'
            result += '<tr>'
        ### 4) info
        for info_item in info_list:
            result += '<tr>'
            result += '<td class="text-center">'
            result += '<span class="fa fa-info-circle text-info me-2"/>'
            result += '</td>'
            result += '<td>'
            result += info_item.get('code', "-")
            result += '</td>'
            result += '<td>'
            result += info_item.get('description', "-")
            result += '</td>'
            result += '<tr>'
        ## TBODY END
        result += '</tbody>'
        ## TABLE END
        result += '</table>'

        # Return result
        return result
