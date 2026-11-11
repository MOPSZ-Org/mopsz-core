# -*- coding: utf-8 -*-
# 1 : imports of python lib
import json

# 2 : imports of odoo
from odoo import _, api, exceptions, fields, models  # alphabetically ordered

# 3 : imports from odoo modules

# 4 : variable declarations


# Class
class L10nHuPlusWizard(models.TransientModel):
    # Private attributes
    _name = 'l10n.hu.plus.wizard'
    _description = "HU+ Wizard"

    # Default methods
    @api.model
    def _get_default_account_move(self):
        if self._context.get('active_model') and self._context['active_model'] == 'account.move':
            account_move_ids = self._context.get('active_ids', [])
        elif self._context.get('wizard_account_move_ids'):
            account_move_ids = self._context.get('wizard_account_move_ids', [])
        else:
            account_move_ids = []
        return [(4, x, 0) for x in account_move_ids]

    @api.model
    def _get_default_active_model(self):
        model_id = False
        if self._context.get('active_model'):
            model_name = self._context.get('active_model')
            model = self.env['ir.model'].sudo().search([('model', '=', model_name)], limit=1)
            if model:
                model_id = model.id
        return model_id

    @api.model
    def _get_default_huf_currency(self):
        return self.env.ref('base.HUF')

    @api.model
    def _get_default_partner(self):
        if self._context.get('active_model') and self._context['active_model'] == 'res.partner':
            partner_ids = self._context.get('active_ids', [])
        elif self._context.get('wizard_account_move_ids'):
            partner_ids = self._context.get('wizard_partner_ids', [])
        else:
            partner_ids = []
        return [(4, x, 0) for x in partner_ids]

    @api.model
    def _get_selection_accounting_nav_payment_method(self):
        return self.env['account.payment.term'].l10n_hu_get_nav_method_selection()

    # Field declarations
    ## COMMON
    action_execute_visible = fields.Boolean(
        default=True,
        string="Action Execute Visible",
    )
    action_type = fields.Selection(
        selection=[
            ('account_move', "Account Move"),
            ('api', "API"),
            ('configuration', "Configuration"),
            ('partner', "Partner"),
            ('technical', "Technical"),
        ],
        string="Action Type",
    )
    action_type_editable = fields.Boolean(
        default=False,
        string="Action Type Editable",
    )
    action_type_visible = fields.Boolean(
        default=False,
        string="Action Type Visible",
    )
    active_model = fields.Many2one(
        comodel_name='ir.model',
        default=_get_default_active_model,
        string="Active Model",
    )
    active_model_id = fields.Integer(
        related='active_model.id',
        string="Active Model ID",
    )
    active_model_name = fields.Char(
        related='active_model.model',
        string="Active Model Name",
    )
    company = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.company.id,
        index=True,
        readonly=True,
        string="Company",
    )
    company_currency = fields.Many2one(
        related='company.currency_id',
        string="Company Currency",
    )
    company_currency_name = fields.Char(
        related='company.currency_id.name',
        string="Company Currency Name",
    )
    error_text = fields.Text(
        copy=False,
        readonly=True,
        string="Error Text",
    )
    huf_currency = fields.Many2one(
        comodel_name='res.currency',
        default=_get_default_huf_currency,
        string="HUF Currency",
    )
    info_text = fields.Text(
        copy=False,
        readonly=True,
        string="Info Text",
    )
    success_text = fields.Text(
        copy=False,
        readonly=True,
        string="Success Text",
    )
    warning_text = fields.Text(
        copy=False,
        readonly=True,
        string="Warning Text",
    )
    ## ACCOUNT MOVE
    account_move = fields.Many2many(
        comodel_name='account.move',
        column1='wizard',
        column2='account_move',
        default=_get_default_account_move,
        relation='l10n_hu_plus_wizard_account_move_rel',
        string="Account Move",
    )
    account_move_action = fields.Selection(
        selection=[
            ('check_status', "Check status"),
            ('update_fields', "Update fields"),
        ],
        string="Account Move Action",
    )
    account_move_action_editable = fields.Boolean(
        default=False,
        string="Account Move Action Editable",
    )
    account_move_action_visible = fields.Boolean(
        default=False,
        string="Account Move Action Visible",
    )
    account_move_count = fields.Integer(
        compute='_compute_account_move_count',
        string="Account Move Count",
    )
    account_move_plus_overview = fields.Html(
        copy=False,
        readonly=True,
        string="Account Move HU+ Overview",
    )
    account_move_visible = fields.Boolean(
        default=False,
        string="Account Move Visible",
    )
    ## ACCOUNTING
    accounting_cash_enabled = fields.Boolean(
        default=False,
        string="Cash Accounting Enabled",
    )
    accounting_cash_visible = fields.Boolean(
        default=False,
        string="Cash Accounting Visible",
    )
    accounting_date = fields.Date(
        string="Accounting Date",
    )
    accounting_delivery_date = fields.Date(
        string="Accounting Delivery Date",
    )
    accounting_delivery_period_enabled = fields.Boolean(
        string="Accounting Delivery Period Enabled",
    )
    accounting_delivery_period_end = fields.Date(
        string="Accounting Delivery Period End",
    )
    accounting_delivery_period_legal = fields.Text(
        readonly=True,
        string="Accounting Delivery Period Legal",
    )
    accounting_delivery_period_start = fields.Date(
        string="Accounting Delivery Period Start",
    )
    accounting_document_rate_amount = fields.Float(
        readonly=True,
        string="Accounting Document Rate Amount",
    )
    accounting_document_rate_visible = fields.Boolean(
        default=False,
        string="Accounting Document Rate Visible",
    )
    accounting_document_type = fields.Many2one(
        comodel_name='l10n.hu.plus.tag',
        domain=[('tag_type', '=', 'document_type')],
        string="Accounting Document Type",
    )
    accounting_document_vat_huf = fields.Monetary(
        copy=False,
        currency_field='huf_currency',
        help="VAT amount in HUF as indicated on the invoice document",
        string="Document VAT HUF",
    )
    accounting_journal = fields.Many2one(
        comodel_name='account.journal',
        string="Accounting Journal",
    )
    accounting_hu_plus_notes = fields.Char(
        string="HU+ Notes",
    )
    accounting_hu_plus_status = fields.Selection(
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
    accounting_hu_plus_tag = fields.Many2many(
        comodel_name='l10n.hu.plus.tag',
        column1='wizard',
        column2='tag',
        domain=[('tag_type', 'in', ['account_move', 'general'])],
        relation='l10n_hu_plus_wizard_hu_plus_tag_rel',
        string="HU+ Tag",
    )
    accounting_move_currency = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_accounting_move_currency',
        string="Accounting Move Currency",
    )
    accounting_move_currency_name = fields.Char(
        related='accounting_move_currency.name',
        string="Accounting Move Currency Name",
    )
    accounting_move_type = fields.Char(
        compute='_compute_accounting_move_type',
        string="Accounting Move Type",
    )
    accounting_nav_payment_method = fields.Selection(
        selection=_get_selection_accounting_nav_payment_method,
        string="Accounting NAV Payment Method",
    )
    accounting_origin = fields.Char(
        string="Accounting Origin",
    )
    accounting_vat_date = fields.Date(
        string="Accounting VAT Date",
    )
    accounting_vat_status = fields.Selection(
        selection=[
            ('to_declare', "To Declare"),
            ('postponed', "Postponed"),
            ('declared', "Declared"),
            ('excluded', "Excluded"),
            ('out_of_scope', "Out of Scope"),
            ('legacy', "Legacy"),
        ],
        string="Accounting VAT Status",
    )
    ## API
    api_action = fields.Selection(
        selection=[
            ('check_registration', "Check registration"),
            ('create_registration', "Create registration"),
            ('delete_registration', "Delete registration"),
            ('download_objects', "Download objects"),
            ('view_api_data', "View API data"),
        ],
        string="API Action",
    )
    api_action_editable = fields.Boolean(
        default=False,
        string="API Action Editable",
    )
    api_data_display = fields.Text(
        readonly=True,
        string="API Data Display",
    )
    api_details = fields.Text(
        readonly=True,
        string="API Details",
    )
    api_key = fields.Char(
        string="API Key",
    )
    api_license_code = fields.Char(
        string="API License Code",
    )
    api_url = fields.Char(
        string="API URL",
    )
    ## CONFIGURATION
    configuration_audit_trail = fields.Boolean(
        default=True,
        string="Configuration Audit Trail",
    )
    configuration_document_types = fields.Boolean(
        default=True,
        string="Configuration Document Types",
    )
    configuration_enabled_journals = fields.Many2many(
        comodel_name='account.journal',
        column1='wizard',
        column2='journal',
        relation='l10n_hu_plus_wizard_configuration_journal_rel',
        string="Configuration Enabled Journals",
    )
    ## CURRENCY
    company_currency_rate = fields.Many2one(
        comodel_name='res.currency.rate',
        string="Company Currency Rate",
    )
    company_currency_rate_amount = fields.Float(
        related='company_currency_rate.company_rate',
        string="Company Currency Rate Amount",
    )
    company_currency_rate_date = fields.Date(
        related='company_currency_rate.name',
        string="Company Currency Rate Date",
    )
    company_currency_rate_inverse_amount = fields.Float(
        related='company_currency_rate.inverse_company_rate',
        string="Company Currency Rate Inverse Amount",
    )
    company_currency_rate_inverse_visible = fields.Boolean(
        default=True,
        string="Company Currency Rate Inverse Invisible",
    )
    ## PARTNER
    partner = fields.Many2many(
        comodel_name='res.partner',
        column1='wizard',
        column2='partner',
        default=_get_default_partner,
        relation='l10n_hu_plus_wizard_partner_rel',
        string="Partner",
    )
    partner_action = fields.Selection(
        default='list',
        selection=[
            ('list', "List partners"),
        ],
        string="Partner Action",
    )
    partner_action_editable = fields.Boolean(
        default=True,
        string="Partner Action Editable",
    )
    partner_action_summary = fields.Text(
        readonly=True,
        string="Partner Action Summary",
    )
    partner_visible = fields.Boolean(
        default=False,
        string="Partner Visible",
    )
    ## TECHNICAL
    technical_action = fields.Selection(
        selection=[
            ('view_data', "View data"),
        ],
        string="Technical Action",
    )
    technical_action_editable = fields.Boolean(
        default=False,
        string="Technical Action Editable",
    )
    technical_data_display = fields.Text(
        readonly=True,
        string="Technical Data Display",
    )

    # Compute and search fields, in the same order of field declarations
    def _compute_accounting_move_type(self):
        for record in self:
            accounting_move_types = []
            for account_move in record.account_move:
                if account_move.move_type not in accounting_move_types:
                    accounting_move_types.append(account_move.move_type)
            if len(accounting_move_types) == 1:
                record.accounting_move_type = accounting_move_types[0]
            else:
                record.accounting_move_type = None

    def _compute_accounting_move_currency(self):
        for record in self:
            move_currencies = []
            for account_move in record.account_move:
                if account_move.currency_id not in move_currencies:
                    move_currencies.append(account_move.currency_id)
            if len(move_currencies) == 1:
                record.accounting_move_currency = move_currencies[0]
            else:
                record.accounting_move_currency = None

    def _compute_account_move_count(self):
        for record in self:
            record.account_move_count = len(record.account_move)

    # Constraints and onchanges
    @api.onchange('accounting_delivery_period_end', 'accounting_delivery_period_start')
    def onchange_accounting_delivery_period(self):
        # Check delivery date sanity
        if (self.accounting_delivery_period_enabled and self.accounting_delivery_period_end
                and self.accounting_delivery_period_start
                and self.accounting_delivery_period_end < self.accounting_delivery_period_start):
            raise exceptions.ValidationError(_("Period end date must be after period start date!"))
        else:
            pass

        # Recompute delivery date (when only one record in account_move m2m and action is reasonable)
        if (self.account_move and len(self.account_move) == 1 and self.action_type == 'account_move'
                and self.account_move[0].move_type in ['out_invoice', 'out_refund']
                and self.accounting_delivery_period_enabled and self.accounting_delivery_period_end
                and self.accounting_delivery_period_start and self.account_move_action == 'update_fields'):
            # Get delivery data
            delivery_data = self.account_move[0].l10n_hu_plus_get_delivery_data({
                'l10n_hu_delivery_period_end': self.accounting_delivery_period_end,
                'l10n_hu_delivery_period_start': self.accounting_delivery_period_start,
            })
            # raise exceptions.ValidationError(str(delivery_data))
            self.accounting_date = delivery_data.get('delivery_date', None)
            self.accounting_delivery_date = delivery_data.get('delivery_date', None)
            self.accounting_delivery_period_legal = delivery_data.get('period_legal', None)
        else:
            pass

    @api.onchange('accounting_document_vat_huf')
    def onchange_accounting_document_vat_huf(self):
        document_rate = self.accounting_document_rate_amount
        if self.account_move and len(self.account_move) == 1:
            document_values = {'l10n_hu_document_vat_huf': self.accounting_document_vat_huf}
            document_data = self.account_move[0].l10n_hu_plus_get_document_data(document_values)
            document_rate = document_data.get('l10n_hu_document_rate', 0.0)
        self.accounting_document_rate_amount = document_rate

    @api.onchange('account_move')
    def onchange_account_move(self):
        # When only one record in account_move m2m and action is reasonable
        if (self.account_move and len(self.account_move) == 1 and self.action_type == 'account_move'
                and self.account_move_action in ['check_status', 'update_fields']):
            # Set account_move
            account_move = self.account_move[0]

            # Set fields from account_move
            self.accounting_date = account_move.date
            self.accounting_move_currency = account_move.currency_id
            self.accounting_move_type = account_move.move_type
            self.accounting_origin = account_move.invoice_origin
            self.accounting_hu_plus_notes = account_move.l10n_hu_plus_notes
            self.accounting_hu_plus_status = account_move.l10n_hu_plus_status
            self.accounting_hu_plus_tag = account_move.l10n_hu_plus_tag

            # Set fields from HU+ data
            data_result = account_move.l10n_hu_plus_get_data({})
            # raise exceptions.UserError(str(data_result))
            field_values = data_result.get('field_values', {})
            # raise exceptions.UserError(str(field_values))
            self.accounting_cash_enabled = field_values.get('l10n_hu_cash_accounting', False)
            self.accounting_delivery_date = field_values.get('delivery_date', account_move.delivery_date)
            self.accounting_delivery_period_end = field_values.get('l10n_hu_delivery_period_end')
            self.accounting_delivery_period_start = field_values.get('l10n_hu_delivery_period_start')
            self.accounting_document_rate_amount = field_values.get('l10n_hu_document_rate', 0.0)
            self.accounting_document_type = field_values.get('l10n_hu_document_type')
            self.accounting_document_vat_huf = field_values.get('l10n_hu_document_vat_huf')
            self.accounting_nav_payment_method = field_values.get('l10n_hu_payment_mode')
            self.accounting_vat_date = field_values.get('l10n_hu_vat_date')
            self.accounting_vat_status = field_values.get('l10n_hu_vat_status')

            # accounting_cash_visible
            if account_move.move_type in ['in_invoice', 'in_refund']:
                self.accounting_cash_visible = True

            # accounting_delivery_period_enabled
            if self.accounting_delivery_period_start and self.accounting_delivery_period_end:
                self.accounting_delivery_period_enabled = True

            # accounting_document_rate_visible
            if (self.action_type == 'account_move' and self.account_move_action == 'update_fields'
                    and account_move.currency_id != account_move.company_currency_id
                    and account_move.move_type in ['in_invoice', 'in_refund']):
                self.accounting_document_rate_visible = True
        else:
            pass

    @api.onchange('partner')
    def onchange_partner(self):
        self.partner_action_summary = self.get_partner_summary()

    # CRUD methods (and display_name, name_search, ...) overrides

    # Action methods
    def action_execute(self):
        # Ensure one
        self.ensure_one()

        # Process actions
        ## ACCOUNT MOVE
        if self.action_type == 'account_move' and self.account_move:
            # check_status
            if self.account_move_action == 'check_status':
                if len(self.account_move) != 1:
                    raise exceptions.UserError(_("Action only allowed on one invoice!"))

            # update_fields
            if self.account_move_action == 'update_fields':
                if len(self.account_move) != 1:
                    raise exceptions.UserError(_("Action only allowed on one invoice!"))
                if self.account_move[0].state != 'draft':
                    raise exceptions.UserError(_("Action only allowed for draft invoices!"))

            # Manage
            manage_result = self.manage_account_move()
            if self.account_move_action in ['check_status', 'update_fields']:
                return {'type': 'ir.actions.act_window_close'}
            elif manage_result.get('account_move_ids') and len(manage_result['account_move_ids']) == 1:
                return {
                    'name': _("Account Move"),
                    'res_id': manage_result['account_move_ids'][0],
                    'res_model': 'account.move',
                    'target': 'current',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form,list',
                }
            elif manage_result.get('account_move_ids'):
                return {
                    'name': _("Account Moves"),
                    'domain': [('id', 'in', manage_result['account_move_ids'])],
                    'res_model': 'account.move',
                    'target': 'current',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'list,form',
                }
            else:
                raise exceptions.UserError("account move action error!")
        ## API
        elif self.action_type == 'api':
            # Update company API data
            try:
                technical_data = json.loads(self.company.l10n_hu_plus_technical_data)
                api_data = technical_data.get('hu_plus_api', {})
            except:
                technical_data = {}
                api_data = {}
            if self.api_key:
                api_data.update({'api_key': self.api_key})
            if self.api_url:
                api_data.update({'api_url': self.api_url})
            if self.api_license_code:
                api_data.update({'license_code': self.api_license_code})
            technical_data.update({'hu_plus_api': api_data})
            self.company.write({'l10n_hu_plus_technical_data': json.dumps(technical_data, default=str)})

            # Manage result
            manage_result = self.manage_api()

            # Wizard result
            if self.api_action in ['check_registration', 'create_registration', 'delete_registration']:
                result = {
                    'name': _("Company"),
                    'res_id': self.company.id,
                    'res_model': 'res.company',
                    'target': 'current',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form,list',
                }
                return result
            elif manage_result.get('object_ids') and len(manage_result['object_ids']) == 1:
                result = {
                    'name': _("HU+ Object"),
                    'res_id': manage_result['object_ids'][0],
                    'res_model': 'l10n.hu.plus.object',
                    'target': 'current',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form,list',
                }
                return result
            elif manage_result.get('object_ids'):
                result = {
                    'name': _("HU+ Objects"),
                    'domain': [('id', 'in', manage_result['object_ids'])],
                    'res_model': 'l10n.hu.plus.object',
                    'target': 'current',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'list,form',
                }
                return result
            elif manage_result.get('log_ids') and len(manage_result['log_ids']) == 1:
                result = {
                    'name': _("HU+ Log"),
                    'res_id': manage_result['log_ids'][0],
                    'res_model': 'l10n.hu.plus.log',
                    'target': 'current',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form,list',
                }
                return result
            elif manage_result.get('log_ids'):
                result = {
                    'name': _("HU+ Logs"),
                    'domain': [('id', 'in', manage_result['log_ids'])],
                    'res_model': 'l10n.hu.plus.log',
                    'target': 'current',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'list,form',
                }
                return result
            else:
                raise exceptions.UserError("api action error!")
        ## CONFIGURATION
        elif self.action_type == 'configuration':
            manage_result = self.manage_configuration()
            return {
                'name': _("HU+ Wizard"),
                'context': {
                    'default_action_execute_visible': False,
                    'default_error_text': manage_result.get('error_text', None),
                    'default_info_text': manage_result.get('info_text', None),
                    'default_success_text': manage_result.get('success_text', None),
                    'default_warning_text': manage_result.get('warning_text', None),
                },
                'res_model': 'l10n.hu.plus.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
            }
        ## PARTNER
        elif self.action_type == 'partner':
            ### list
            if self.partner_action == 'list':
                # Check input
                if not self.partner:
                    raise exceptions.UserError(_("No partner selected!"))

                # Manage
                manage_result = self.manage_partner()
                if manage_result.get('partner_ids'):
                    return {
                        'name': _("Partner"),
                        'domain': [('id', 'in', manage_result['partner_ids'])],
                        'res_model': 'res.partner',
                        'target': 'current',
                        'type': 'ir.actions.act_window',
                        'view_mode': 'list,form',
                    }
                else:
                    raise exceptions.UserError("partner_delete error!")
            ### else
            else:
                raise exceptions.UserError("invalid partner action!")
        ## TECHNICAL
        elif self.action_type == 'technical':
            # Manage
            manage_result = self.manage_technical()
            if manage_result.get('record_ids') and len(manage_result['record_ids']) == 1 and manage_result.get('model_name'):
                return {
                    'name': _("HU+ Technical"),
                    'res_id': manage_result['record_ids'][0],
                    'res_model': manage_result['model_name'],
                    'target': 'current',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form,list',
                }
            elif manage_result.get('record_ids'):
                return {
                    'name': _("HU+ Technical"),
                    'domain': [('id', 'in', manage_result['record_ids'])],
                    'res_model': manage_result['model_name'],
                    'target': 'current',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'list,form',
                }
            else:
                return {'type': 'ir.actions.act_window_close'}
        ## Else
        else:
            pass

        # Return result
        return

    # Business methods
    ## HELPER
    @api.model
    def get_partner_summary(self):
        """ Get summary for the selected partners

        :return: string
        """
        # Initialize variables
        result = ""

        # Process scenarios
        if self.action_type == 'partner' and self.partner:
            # Partner count
            partner_count = len(self.partner)
            result += _("Selected") + ": " + str(partner_count)
            # Partner details
            no_company_partners = []
            for partner in self.partner:
                if not partner.company_id:
                    no_company_partners.append(partner)
            # Summary
            result += "\n" + _("No Company") + ": " + str(len(no_company_partners))
        else:
            pass

        # Return result
        return result

    ## MANAGE
    @api.model
    def manage_account_move(self):
        """ Manage account move actions

        NOTE:
        - We may iterate because account move field is m2m to support mass management

        :return: dictionary
        """
        # Initialize variables
        account_move_ids = []
        error_list = []
        result = {}

        # Process scenarios
        if self.action_type == 'account_move':
            if self.account_move_action == 'check_status':
                for account_move in self.account_move:
                    account_move.write({
                        'l10n_hu_plus_notes': self.accounting_hu_plus_notes,
                        'l10n_hu_plus_status': self.accounting_hu_plus_status,
                        'l10n_hu_plus_tag': [fields.Command.set( self.accounting_hu_plus_tag.ids)]
                    })
                    account_move_ids.append(account_move.id)
            elif self.account_move_action == 'update_fields':
                for account_move in self.account_move:
                    # Prepare parameters
                    data_parameters = {
                        'delivery_date': self.accounting_delivery_date,
                        'invoice_origin': self.accounting_origin,
                        'l10n_hu_cash_accounting': self.accounting_cash_enabled,
                        'l10n_hu_delivery_period_end': self.accounting_delivery_period_end,
                        'l10n_hu_delivery_period_start': self.accounting_delivery_period_start,
                        'l10n_hu_document_type': self.accounting_document_type,
                        'l10n_hu_document_vat_huf': self.accounting_document_vat_huf,
                        'l10n_hu_vat_date': self.accounting_vat_date,
                        'l10n_hu_vat_status': self.accounting_vat_status,
                    }
                    if self.accounting_cash_visible:
                        data_parameters.update({'l10n_hu_cash_accounting': self.accounting_cash_enabled})
                    if self.accounting_document_rate_visible:
                        data_parameters.update({'l10n_hu_document_rate': self.accounting_document_rate_amount})
                    data_result = account_move.l10n_hu_plus_get_data(data_parameters)
                    # raise exceptions.ValidationError(str(values_result))

                    # Write when necessary
                    if len(data_result.get('error_list')) == 0 and len(data_result.get('field_values')) > 0:
                        # Do write
                        write_values = data_result['field_values']
                        write_values.update({
                            'date': self.accounting_date,
                            'l10n_hu_plus_notes': self.accounting_hu_plus_notes,
                            'l10n_hu_plus_tag': [fields.Command.set(self.accounting_hu_plus_tag.ids)]
                        })
                        account_move.write(write_values)

                        # Update HU+ status
                        account_move.action_l10n_hu_update_plus_status()
                    else:
                        error_list += data_result.get('error_list', [])

                    # Append to list
                    account_move_ids.append(account_move.id)
            else:
                pass
        else:
            pass

        # Update result
        result.update({'account_move_ids': account_move_ids, 'error_list': error_list})

        # Return result
        # raise exceptions.UserError(str(result))
        return result

    @api.model
    def manage_api(self):
        """ Manage API actions

        :return: dictionary
        """
        # Initialize variables
        api_result = {}
        debug_list = []
        error_list = []
        info_list = []
        log_ids = []
        object_ids = []
        result = {}
        warning_list = []

        # Process scenarios
        if self.action_type == 'api':
            debug_list.append("processing api action_type")
            if self.api_action == 'check_registration':
                debug_list.append("processing check_registration api_action")
                api_values = {'request_type': 'get_registration'}
                api_result = self.company.l10n_hu_plus_api_registration_request(api_values)
            ## Create registration
            elif self.api_action == 'create_registration':
                debug_list.append("processing create_registration api_action")
                api_values = {'request_type': 'post_registration'}
                api_result = self.company.l10n_hu_plus_api_registration_request(api_values)
            ## Delete registration
            elif self.api_action == 'delete_registration':
                debug_list.append("processing delete_registration api_action")
                api_values = {'request_type': 'delete_registration'}
                api_result = self.company.l10n_hu_plus_api_registration_request(api_values)
            ## Get objects
            elif self.api_action == 'download_objects':
                debug_list.append("processing download_objects api_action")
                api_values = {'request_type': 'get_object'}
                object_class = self.env['l10n.hu.plus.object']
                api_result = object_class.api_object_request(api_values)
            else:
                error_list.append("invalid api_action")
        else:
            error_list.append("invalid action_type")

        # Append to lists
        if api_result.get('l10n_hu_plus_log'):
            log_ids.append(api_result['l10n_hu_plus_log'].id)
        if api_result.get('l10n_hu_plus_object'):
            object_ids.append(api_result['l10n_hu_plus_object'].id)

        # Update result
        result.update({
            'api_result': api_result,
            'debug_list': debug_list,
            'error_list': error_list,
            'info_list': info_list,
            'log_ids': log_ids,
            'object_ids': object_ids,
            'warning_list': warning_list,
        })

        # Return result
        # raise exceptions.UserError(str(result))
        return result

    @api.model
    def manage_configuration(self):
        """ Manage configuration actions

        :return: dictionary
        """
        # Initialize variables
        configuration_result = {}
        debug_list = []
        error_list = []
        error_text = ""
        info_list = []
        info_text = ""
        result = {}
        success_list = []
        success_text = ""
        warning_list = []
        warning_text = ""

        # Process scenarios
        if self.action_type == 'configuration':
            debug_list.append("processing configuration action_type")
            configuration_values = {
                'audit_trail': self.configuration_audit_trail,
                'document_types': self.configuration_document_types,
                'enabled_journals': self.configuration_enabled_journals,
            }
            configuration_result = self.company.l10n_hu_plus_apply_configuration(configuration_values)
            error_list += configuration_result.get('error_list', [])
            if configuration_result.get('error_list'):
                for error_item in configuration_result['error_list']:
                    error_text += str(error_item) + "\n"
            info_list += configuration_result.get('info_list', [])
            if configuration_result.get('info_list'):
                for info_item in configuration_result['info_list']:
                    info_text += str(info_item) + "\n"
            success_list += configuration_result.get('success_list', [])
            if configuration_result.get('success_list'):
                for success_item in configuration_result['success_list']:
                    success_text += str(success_item) + "\n"
            warning_list += configuration_result.get('warning_list', [])
            if configuration_result.get('warning_list'):
                for warning_item in configuration_result['warning_list']:
                    warning_text += str(warning_item) + "\n"
        else:
            error_list.append("invalid action_type")

        # Update result
        result.update({
            'configuration_result': configuration_result,
            'debug_list': debug_list,
            'error_list': error_list,
            'error_text': error_text,
            'info_list': info_list,
            'info_text': info_text,
            'success_list': success_list,
            'success_text': success_text,
            'warning_list': warning_list,
            'warning_text': warning_text,
        })

        # Return result
        # raise exceptions.UserError(str(result))
        return result

    @api.model
    def manage_partner(self):
        """ Manage partner actions

        We iterate because partner field is m2m to support mass management

        :return: dictionary
        """
        # Initialize variables
        partners = []
        partner_ids = []
        result = {}

        # Iterate partners
        for partner in self.partner:
            # Process scenarios
            ## LIST
            if self.action_type == 'partner' and self.partner_action == 'list':
                partner_ids.append(partner.id)
            else:
                pass

        # Update result
        result.update({
            'partners': partners,
            'partner_ids': partner_ids,
        })

        # Return result
        # raise exceptions.UserError(str(result))
        return result

    @api.model
    def manage_technical(self):
        """ Manage technical actions

        :return: dictionary
        """
        # Initialize variables
        api_result = {}
        debug_list = []
        error_list = []
        info_list = []
        model_name = None
        record_ids = []
        result = {}
        warning_list = []

        # Process scenarios
        if self.action_type == 'technical':
            debug_list.append("processing technical action_type")
        else:
            error_list.append("invalid action_type")

        # Update result
        result.update({
            'api_result': api_result,
            'debug_list': debug_list,
            'error_list': error_list,
            'info_list': info_list,
            'model_name': model_name,
            'record_ids': record_ids,
            'warning_list': warning_list,
        })

        # Return result
        # raise exceptions.UserError(str(result))
        return result
