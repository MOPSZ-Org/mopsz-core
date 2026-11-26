# -*- coding: utf-8 -*-
# 1 : imports of python lib
import datetime
import json
import random
import string
import uuid

import requests

# 2 : imports of odoo
from odoo import _, api, exceptions, fields, models, tools  # alphabetically ordered

# 3 : imports from odoo modules
from odoo.tools.translate import html_translate

# 4 : variable declarations
_HTTP_TIMEOUT = (5, 30)


# Class
class L10nHuPlusObject(models.Model):
    # Private attributes
    _name = 'l10n.hu.plus.object'
    _description = "HU+ Object"
    _inherit = ['image.mixin', 'mail.activity.mixin', 'mail.thread']
    _order = 'priority asc, name asc, id desc'

    # Default methods

    # Field declarations
    active = fields.Boolean(
        default=True,
        string="Active",
    )
    category_tag = fields.Many2one(
        comodel_name='l10n.hu.plus.tag',
        domain=[('tag_type', '=', 'object_category')],
        index=True,
        string="Category",
    )
    category_technical_name = fields.Char(
        related='category_tag.technical_name',
        string="Category Technical Name",
    )
    code = fields.Char(
        copy=False,
        string="Code",
    )
    collection_tag = fields.Many2one(
        comodel_name='l10n.hu.plus.tag',
        domain=[('tag_type', '=', 'object_collection')],
        index=True,
        store=True,
        string="Collection",
    )
    collection_technical_name = fields.Char(
        related='collection_tag.technical_name',
        string="Collection Technical Name",
    )
    color = fields.Integer(
        string="Color",
    )
    company = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.company.id,
        index=True,
        readonly=True,
        string="Company",
    )
    description = fields.Text(
        copy=False,
        string="Description",
    )
    external_id = fields.Char(
        copy=False,
        string="External ID",
    )
    html_content = fields.Html(
        copy=False,
        index="trigram",
        sanitize_attributes=False,
        sanitize_form=False,
        string="HTML Content",
        translate=html_translate,
    )
    html_visible = fields.Boolean(
        default=False,
        string="HTML Visible",
    )
    key = fields.Char(
        copy=False,
        index=True,
        string="Key",
        tracking=True,
    )
    locked = fields.Boolean(
        default=False,
        string="Locked",
        tracking=True,
    )
    name = fields.Char(
        copy=False,
        index="trigram",
        string="Name",
        translate=True,
    )
    priority = fields.Integer(
        copy=False,
        index=True,
        string="Priority",
    )
    reference = fields.Char(
        copy=False,
        readonly=True,
        index=True,
        string="Reference",
    )
    status_tag = fields.Many2one(
        comodel_name='l10n.hu.plus.tag',
        domain=[('tag_type', '=', 'object_status')],
        index=True,
        string="Object Status",
    )
    status_technical_name = fields.Char(
        related='status_tag.technical_name',
        string="Status Technical Name",
    )
    tag = fields.Many2many(
        comodel_name='l10n.hu.plus.tag',
        column1='object',
        column2='tag',
        domain=[('tag_type', 'in', ['general', 'object', 'technical'])],
        index=True,
        relation='l10n_hu_plus_object_tag_rel',
        string="Tag",
    )
    type_tag = fields.Many2one(
        comodel_name='l10n.hu.plus.tag',
        domain=[('tag_type', '=', 'object_type')],
        index=True,
        string="Object Type",
        tracking=True,
    )
    type_key_enabled = fields.Boolean(
        related='type_tag.key_enabled',
        string="Type Key Enabled",
    )
    type_key_method = fields.Selection(
        related='type_tag.key_method',
        string="Type Key Method",
    )
    type_technical_name = fields.Char(
        related='type_tag.technical_name',
        index=True,
        store=True,
        string="Type Technical Name",
    )
    url = fields.Char(
        copy=False,
        index=True,
        size=1024,
        string="Url",
    )
    ## API
    api_enabled = fields.Boolean(
        default=False,
        string="API Enabled",
    )
    api_data = fields.Json(
        copy=False,
        readonly=True,
        string="API Data",
    )
    api_timestamp = fields.Datetime(
        copy=False,
        readonly=True,
        string="API Timestamp",
    )
    ## LINKED
    linked_model_name = fields.Char(
        copy=False,
        index=True,
        string="Linked Model Name",
    )
    linked_record_id = fields.Integer(
        copy=False,
        index=True,
        string="Linked Record ID",
    )
    linked_record_name = fields.Char(
        compute='_compute_linked_record_name',
        string="Linked Record Name",
    )
    ## TECHNICAL
    technical_data = fields.Json(
        copy=False,
        string="Technical Data",
    )
    technical_name = fields.Char(
        copy=False,
        index=True,
        string="Technical Name",
        tracking=True,
    )
    technical_timestamp = fields.Datetime(
        copy=False,
        default=fields.Datetime.now(),
        readonly=True,
        string="Technical Timestamp",
    )

    # Compute and search fields, in the same order of field declarations
    def _compute_linked_record_name(self):
        for record in self:
            if record.linked_model_name and record.linked_record_id:
                linked_record = self.env[record.linked_model_name].browse(record.linked_record_id).exists()
                if linked_record:
                    record.linked_record_name = linked_record.display_name
                else:
                    record.linked_record_name = None
            else:
                record.linked_record_name = None

    # Constraints and onchanges

    # CRUD methods (and display_name, name_search, ...) overrides
    def _compute_display_name(self):
        for record in self:
            if record.name:
                display_name = record.name
            else:
                display_name = str(record.id)
            record.display_name = display_name

    # Action methods
    def action_generate_key(self):
        # Ensure one record in self
        self.ensure_one()

        # Get
        if self.type_tag and self.type_tag.key_enabled and self.type_tag.key_method == 'uuid4':
            self.key = self.get_uuid4()
        else:
            return

    def action_view_api_data(self):
        # Ensure one
        self.ensure_one()

        # api_data_display
        if self.api_data:
            api_data_display = json.dumps(self.api_data, default=str, indent=4)
            context = {
                'default_action_type': 'api',
                'default_api_action': 'view_api_data',
                'default_api_data_display': api_data_display,
            }
            result = {
                'name': _("HU+ Wizard"),
                'context': context,
                'res_model': 'l10n.hu.plus.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
            }
            return result
        else:
            raise exceptions.UserError(_("API data is empty!"))

    def action_view_linked_record(self):
        # Ensure one
        self.ensure_one()

        # Check
        if not self.linked_model_name or not self.linked_record_id:
            raise exceptions.UserError(_("Linked model name and record ID are both required!"))

        model = self.env['ir.model'].search([('model', '=', self.linked_model_name)])

        # Result
        result = {
            'name': model.display_name,
            'res_id': self.linked_record_id,
            'res_model': self.linked_model_name,
            'target': 'current',
            'type': 'ir.actions.act_window',
            'view_mode': 'form,list',
        }

        # Return result
        return result

    def action_view_technical_data(self):
        # Ensure one
        self.ensure_one()

        # Return
        if self.technical_data:
            data_display = json.dumps(self.api_data, default=str, indent=4)
            context = {
                'default_action_type': 'technical',
                'default_techical_action': 'view_data',
                'default_technical_data_display': data_display,
            }
            result = {
                'name': _("HU+ Wizard"),
                'context': context,
                'res_model': 'l10n.hu.plus.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
            }
            return result
        else:
            raise exceptions.UserError(_("Technical data is empty!"))

    # Business methods
    ## API
    @api.model
    def api_object_request(self, values):
        """ Make a request to API and process the response

        NOTE:
        - simple python request implementation to manage API
        - currency we only support GET

        :param values: dictionary

        :return: dictionary
        """
        # raise exceptions.UserError("object_api_request_response BEGIN" + str(values))

        # Initialize variables
        debug_list = []
        error_list = []
        info_list = []
        request_type = ""
        result = {}
        warning_list = []

        # request_data
        if values.get('request_data') and application:
            request_data = values['request_data']
            # debug_list.append("request_data: " + str(request_data))
            # raise exceptions.UserError("get_registration request_data" + str(request_data))
            request_data.update({
                'environment': application.environment_type,
                'operation': request_type,
            })
        else:
            request_data = {}
            error_list.append("request_data not found in values")

        # request_url
        if values.get('request_url'):
            request_url = values['request_url']
            debug_list.append("request_url found in values: " + str(request_url))
        else:
            request_url = False
            error_list.append("request_url not found in values")

        # Create log
        log_values = {
            'application': application_id,
            'direction': 'outgoing',
            'request_method': 'GET',
            'request_type': request_type,
        }
        log = self.env['l10n.hu.log'].sudo().create(log_values)

        # Request-Response
        # request_headers
        request_headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
                "X-Api-Key": api_data['api_key'],
        }

        # request_method
        if message and message.request_method in ['GET', 'POST', 'PUT', 'DELETE']:
            request_method = message.request_method
        else:
            request_method = False
            error_list.append("invalid request_method")

        # request_url
        if values.get('request_url'):
            request_url = values['request_url']
        else:
            request_url = False
            error_list.append("request_url not found in values")

        # request_type
        if values.get('request_type'):
            request_type = values['request_type']
        else:
            request_type = False
            error_list.append("request_type not found in values")

        # request_data
        if values.get('request_data'):
            # request_data = {'params': values['request_data']}
            request_data = json.dumps(values['request_data'], default=str)
        else:
            request_data = False
            error_list.append("request_type not found in values")

        # debug_exception
        debug_exception = "\n" + str(request_url)
        debug_exception += "\n" + str(request_headers)
        debug_exception += "\n" + str(request_data)
        # raise exceptions.UserError("debug_exception" + debug_exception)

        # Make request and process response
        if len(error_list) == 0:
            # Make request
            if request_method == 'DELETE':
                response = requests.delete(request_url, headers=request_headers, data=request_data, timeout=_HTTP_TIMEOUT)
            elif request_method == 'GET':
                response = requests.get(request_url, headers=request_headers, data=request_data, timeout=_HTTP_TIMEOUT)
            elif request_method == 'POST':
                response = requests.post(request_url, headers=request_headers, data=request_data, timeout=_HTTP_TIMEOUT)
            else:
                pass
            # raise exceptions.UserError(str(response.text))

            # Process response
            # response_status_code
            if response_details.get('response_status_code') in [200, 201, 204]:
                response_status_code_type = 'success'
            elif response_details.get('response_status_code') in [400, 401, 402, 403, 404, 422]:
                response_status_code_type = 'error'
            elif response_details.get('response_status_code') in [500]:
                response_status_code_type = 'server_error'
            else:
                response_status_code_type = 'unknown'
        else:
            # Processing result
            processing_result = {
                'response_success': False,
                'response_type': 'error',
                'status': 'error',
            }
            debug_list.append("request sending skipped due to previous errors")

        write_info = {
            'message': message,
            'processing_parameters': processing_parameters,
            'processing_result': processing_result,
            'request_info': {
                'request_data': request_data,
                'request_headers': request_headers,
                'request_path': request_url,
            },
            'response_info': {
                'response_json': response_result.get('payload', {}),
                'response_success': processing_result.get('response_success', False),
                'response_type': processing_result.get('response_type', False),
            },
        }

        # Update result
        result.update({
            'debug_list': debug_list,
            'error_list': error_list,
            'info_list': info_list,
            'message': message,
            'processing_result': processing_result,
            'warning_list': warning_list,
        })

        # raise exceptions.UserError("application_get_registration_request END" + str(result))

        # Return result
        return result

    @api.model
    def api_object_response(self, values):
        """ Process application_get_registration response

        :param values: dictionary

        :return: dictionary
        """
        # raise exceptions.UserError("application_get_registration_response BEGIN" + str(values))

        # Initialize variables
        debug_list = []
        error_list = []
        info_list = []
        processing_log = ""
        processing_result = {}
        result = {}
        warning_list = []

        # Get message
        if values.get('message'):
            message = values['message']
        else:
            message = False

        # Get response_json
        if values.get('response_json'):
            response_json = values['response_json']
        else:
            response_json = {}

        # Process
        if message \
                and message.application \
                and message.request_method == 'GET' \
                and message.request_type == 'application_get_registration' \
                and response_json.get('result'):
            response_json_result = response_json.get('result')
            response_payload = response_json_result.get('payload')

            # Response details processing
            processing_values = {
                'api_message': message,
                'api_payload': response_payload,
            }
            response_processing_result = message.application.api_get_registration_response(processing_values)
            # raise exceptions.UserError("response_processing_result" + str(response_processing_result))
            error_list += response_processing_result['error_list']

            if len(error_list) == 0:
                processing_result.update({
                    'registration_data': response_processing_result.get('registration_data', {}),
                    'result_messages': response_processing_result.get('result_messages', []),
                    'response_success': True,
                    'response_type': 'application_get_registration',
                    'status': 'done',
                })
        else:
            processing_result.update({
                'response_success': False,
                'response_type': 'application_get_registration_error',
                'status': 'error',
            })

        # Update result
        result.update({
            'debug_list': debug_list,
            'error_list': error_list,
            'info_list': info_list,
            'message': message,
            'processing_log': processing_log,
            'processing_result': processing_result,
            'warning_list': warning_list,
        })

        # Return result
        # raise exceptions.UserError('application_get_registration_response END' + str(result))
        return result

    ## CRON
    @api.model
    def run_object_api_cron(self):
        """Scheduled entry point for HU+ object API sync.

        The previous implementation was non-runnable (wrong model names, unbound locals, invalid log fields) and would raise on
        every company. Object API sync is rarely used; keep the cron inactive and treat calls as a no-op so schedulers and
        manual runs neither crash nor grow the HU+ log table.

        :return: dictionary describing the skipped run
        """
        return {
            'company_count': 0,
            'company_ids': [],
            'company_results': [],
            'error_list': [],
            'skipped': True,
            'skip_reason': 'object_api_cron_disabled',
        }

    ## HELPER
    @api.model
    def get_random_string(self, values=None):
        """ Get a random string

        :param values: optional dictionary of parameters, including:
            - length: integer
            - letters: lowercase | uppercase | both | none
            - numbers: boolean
            - prefix: string
            - start_with_letter: boolean
            - suffix: string

        :return string
        """
        # Initialize variables
        result = ""

        # Set letters
        if values and values.get('letters'):
            letters = values['letters']
        elif self.object_type and self.object_type.random_name_letters:
            letters = self.object_type.random_name_letters
        else:
            letters = "both"

        # Set numbers
        if values and values.get('numbers') is not None and values.get('numbers'):
            numbers = True
        elif values and values.get('numbers') is not None and not values.get('numbers'):
            numbers = False
        elif self.object_type and self.object_type.random_name_numbers:
            numbers = True
        elif self.object_type and not self.object_type.random_name_numbers:
            numbers = False
        else:
            numbers = True

        # Set prefix
        if values and values.get('prefix'):
            result += values['prefix']
        elif self.object_type and self.object_type.random_name_prefix:
            result += self.object_type.random_name_prefix
        else:
            pass

        # Set length
        if values and values.get('length'):
            length = values['length']
        elif self.object_type and self.object_type.random_name_length:
            length = self.object_type.random_name_length
        else:
            length = 8

        # Start with letter
        if values and values.get('start_with_letter'):
            if letters == 'both' and numbers:
                result += random.choice(string.ascii_uppercase + string.ascii_lowercase)
            elif letters == 'lowercase' and numbers:
                result += random.choice(string.ascii_lowercase)
            elif letters == 'uppercase' and numbers:
                result += random.choice(string.ascii_uppercase)
            else:
                result += random.choice(string.ascii_uppercase + string.ascii_lowercase)
            length = length - 1
        elif self.object_type and self.object_type.random_name_start_with_letter:
            if letters == 'both' and numbers:
                result += random.choice(string.ascii_uppercase + string.ascii_lowercase)
            elif letters == 'lowercase' and numbers:
                result += random.choice(string.ascii_lowercase)
            elif letters == 'uppercase' and numbers:
                result += random.choice(string.ascii_uppercase)
            else:
                result += random.choice(string.ascii_uppercase + string.ascii_lowercase)
            length = length - 1
        else:
            pass

        # Iterate for random characters
        for i in range(length):
            if letters == 'both' and numbers:
                result += random.choice(string.ascii_uppercase + string.digits + string.ascii_lowercase)
            elif letters == 'lowercase' and numbers:
                result += random.choice(string.digits + string.ascii_lowercase)
            elif letters == 'uppercase' and numbers:
                result += random.choice(string.digits + string.ascii_lowercase)
            elif letters == 'none' and numbers:
                result += random.choice(string.digits + string.ascii_lowercase)
            else:
                result += random.choice(string.ascii_uppercase + string.digits + string.ascii_lowercase)

        # Set suffix
        if values and values.get('suffix'):
            result += values['suffix']
        elif self.object_type and self.object_type.random_name_suffix:
            result += self.object_type.random_name_suffix
        else:
            pass

        # Return
        return result

    @api.model
    def get_tags_by_technical_name(self):
        """ Get tags by technical name

        NOTE:
        - helper method to get available tag ids and objects organized by technical name

        :return dictionary
        """
        # raise exceptions.UserError("get_tags_by_technical_name BEGIN")

        # Initialize variables
        result = {}

        # Collect tags and update result
        tags = self.env['l10n.hu.plus.tag'].sudo().search([
            ('active', 'in', [True, False]),
        ])
        for tag in tags:
            if tag.technical_name:
                record_key = tag.technical_name + "_tag"
                record_id_key = tag.technical_name + "_tag_id"
                result[record_key] = tag
                result[record_id_key] = tag.id

        # Return result
        return result

    @api.model
    def get_uuid4(self):
        """ Get uuid4

        :return string
        """
        # Generate uuid4
        result = uuid.uuid4()

        # Return
        return result
