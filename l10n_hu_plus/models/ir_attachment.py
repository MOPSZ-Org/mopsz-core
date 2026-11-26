# -*- coding: utf-8 -*-
# 1 : imports of python lib
import os

# 2 : imports of odoo
from odoo import _, api, exceptions, fields, models  # alphabetically ordered

# 3 : imports from odoo modules
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.misc import format_date

# 4 : variable declarations


# Class
class L10nHuPlusIrAttachment(models.Model):
    # Private attributes
    _inherit = 'ir.attachment'

    # Default methods

    # Field declarations

    # Compute and search fields, in the same order of field declarations

    # Constraints and onchanges

    # CRUD methods (and display_name, name_search, ...) overrides

    # Action methods

    # Business methods
    @api.ondelete(at_uninstall=True)
    def _l10n_hu_plus_except_audit_trail(self):
        """ Inspired by: https://github.com/odoo/odoo/blob/1b8f8908d31df67604413b3aa764f16ffe18d312/addons/l10n_de/models/ir_attachment.py#L14 """
        # HU / restrictive_audit_trail checks before reading attachment.raw (HU-7)
        audit_trail_attachments = self.filtered(lambda attachment:
            attachment.res_model == 'account.move'
            and attachment.res_id
            and attachment.company_id
            and attachment.company_id.account_fiscal_country_id.code == 'HU'
            and attachment.company_id.restrictive_audit_trail
            and attachment.raw
            and guess_mimetype(attachment.raw) in (
                'application/pdf',
                'application/xml',
            )
        )
        id2move = self.env['account.move'].browse(set(audit_trail_attachments.mapped('res_id'))).exists().grouped('id')
        for attachment in audit_trail_attachments:
            move = id2move.get(attachment.res_id)
            if move and move.posted_before and move.checked:
                ue = exceptions.UserError(_("You cannot remove parts of the audit trail."))
                ue._audit_trail = True
                raise ue

    def write(self, vals):
        """ Inspired by: https://github.com/odoo/odoo/blob/1b8f8908d31df67604413b3aa764f16ffe18d312/addons/l10n_de/models/ir_attachment.py#L34 """
        if vals.keys() & {'res_id', 'res_model', 'raw', 'datas', 'store_fname', 'db_datas', 'company_id'}:
            try:
                self._l10n_hu_plus_except_audit_trail()
            except exceptions.UserError as e:
                if (
                    not hasattr(e, '_audit_trail')
                    or vals.get('res_model') != 'documents.document'
                    or vals.keys() & {'raw', 'datas', 'store_fname', 'db_datas'}
                ):
                    raise  # do not raise if trying to version the attachment through a document
                vals.pop('res_model', None)
                vals.pop('res_id', None)
        return super().write(vals)

    def unlink(self):
        """ Inspired by: https://github.com/odoo/odoo/blob/1b8f8908d31df67604413b3aa764f16ffe18d312/addons/l10n_de/models/ir_attachment.py#L49 """
        invoice_pdf_attachments = self.filtered(lambda attachment:
            attachment.res_model == 'account.move'
            and attachment.res_id
            and attachment.res_field in ('invoice_pdf_report_file', 'ubl_cii_xml_file')
            and attachment.company_id.restrictive_audit_trail
            and attachment.company_id.account_fiscal_country_id.code == 'HU'
        )
        if invoice_pdf_attachments:
            # only detach the document from the field, but keep it in the database for the audit trail
            # it shouldn't be an issue as there aren't any security group on the fields as it is the public report
            invoice_pdf_attachments.res_field = False
            today = format_date(self.env, fields.Date.context_today(self))
            for attachment in invoice_pdf_attachments:
                # raise exception if checked
                account_move = self.env['account.move'].browse([attachment.res_id])
                if account_move.checked:
                    raise exceptions.UserError(_("Invoice is checked, can not detach invoice pdf!"))

                # rename attachment
                attachment_name, attachment_extension = os.path.splitext(attachment.name)
                attachment.name = _(
                    '%(attachment_name)s (detached by %(user)s on %(date)s)%(attachment_extension)s',
                    attachment_name=attachment_name,
                    attachment_extension=attachment_extension,
                    user=self.env.user.name,
                    date=today,
                )

                # post message
                message_body = _("Invoice pdf detached")
                account_move.message_post(body=message_body)
        return super(L10nHuPlusIrAttachment, self - invoice_pdf_attachments).unlink()
