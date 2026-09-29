# -*- coding: utf-8 -*-
# 1 : imports of python lib
import logging

# 2 : imports of odoo
from odoo import api, SUPERUSER_ID

# 3 : imports from odoo modules

# 4 : variable declarations
_logger = logging.getLogger(__name__)


# UPGRADE
def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    updated_count = env["account.move"]._l10n_hu_migrate_huf_rates()
    _logger.info("Migrated l10n_hu_huf_rate on %s account.move record(s)", updated_count)
