# -*- coding: utf-8 -*-
# author: Online ERP
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

_PORTAL_ACL_XML_NAMES = (
    "l10n_hu_plus_object_portal_access",
    "l10n_hu_plus_log_portal_access",
    "l10n_hu_plus_tag_portal_access",
)


def migrate(cr, version):
    """Remove legacy portal ACL rows left from previous module versions."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Imd = env["ir.model.data"].sudo()
    Access = env["ir.model.access"].sudo()
    removed = 0
    for xml_name in _PORTAL_ACL_XML_NAMES:
        imd = Imd.search([
            ("module", "=", "l10n_hu_plus"),
            ("name", "=", xml_name),
            ("model", "=", "ir.model.access"),
        ], limit=1)
        if not imd:
            continue
        Access.browse(imd.res_id).exists().unlink()
        imd.unlink()
        removed += 1
    _logger.info("POST removed %s legacy HU+ portal ACL row(s)", removed)
