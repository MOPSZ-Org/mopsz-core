# -*- coding: utf-8 -*-
# 1 : imports of python lib

# 2 : imports of odoo
from odoo import _, api, exceptions, fields, models, tools  # alphabetically ordered

# 3 : imports from odoo modules

# 4 : initialize variables


# Class
class L10nHuPlusAccountMoveReversal(models.TransientModel):
    # Private attributes
    _inherit = 'account.move.reversal'

    # Default methods

    # Field declarations
    l10n_hu_storno_enabled = fields.Boolean(
        default=False,
        help="Storno document type for refund without new invoice",
        string="HU Storno Enabled",
    )
    l10n_hu_storno_visible = fields.Boolean(
        compute='_compute_l10n_hu_storno_visible',
        string="HU Storno Visible",
    )

    # Compute and search fields, in the same order of field declarations
    @api.depends('move_ids')
    def _compute_l10n_hu_storno_visible(self):
        for record in self:
            # Initialize variables
            checked_account_move_count = 0
            compatible_account_moves = []

            # Iterate account moves
            for account_move in record.move_ids:
                checked_account_move_count += 1
                document_data = account_move.l10n_hu_plus_get_document_data({})
                if document_data.get('is_storno_allowed', False):
                    compatible_account_moves.append(account_move)

            # Set field value
            if len(compatible_account_moves) == checked_account_move_count:
                record.l10n_hu_storno_visible = True
            else:
                record.l10n_hu_storno_visible = False

    # Constraints and onchanges

    # CRUD methods (and display_name, name_search, ...) overrides

    # Action methods

    # Business methods
    ## SUPER
    def reverse_moves(self, is_modify=False):
        """Create reversals; keep original HUF rate on non-HUF company HU storno after create.

        Before ``super()``, snapshot existing linked ``out_refund`` ids, and when storno is enabled on a Hungarian fiscal
        company whose currency is not HUF, pass ``l10n_hu_storno_original_huf_rates`` so create-time compute can pick up the
        original invoice rate (same idea as ``l10n_hu_oerp`` for ``invoice_currency_rate``). After create, only newly created
        credit notes get storno/modification document-type tagging and the original stored ``l10n_hu_huf_rate`` write. Later
        draft date changes may still refresh the rate via ``_compute_l10n_hu_huf_rate``. HUF companies keep relying on
        ``l10n_hu_oerp`` for ``invoice_currency_rate`` storno.

        :param bool is_modify: whether this is a modify operation (credit note and new draft invoice)
        :returns: action to open the created reverse moves
        """
        currency_huf = self.env.ref("base.HUF")
        move_ids = self.move_ids.ids
        # snapshot linked refunds before reverse so post-create search skips older credit notes
        existing_refund_ids = self.env["account.move"].search([
            ("move_type", "=", "out_refund"),
            ("reversed_entry_id", "in", move_ids),
        ]).ids
        # non-HUF company HU storno: pass original stored HUF rates into create (oerp-style context pattern)
        if (self.l10n_hu_storno_enabled
                and self.company_id.account_fiscal_country_id.code == "HU"
                and self.company_id.currency_id != currency_huf):
            storno_huf_rates = {
                move.id: move.l10n_hu_huf_rate
                for move in self.move_ids.filtered(
                    lambda move: move.company_id == self.company_id and move.l10n_hu_huf_rate
                )
            }
            if storno_huf_rates:
                self = self.with_context(l10n_hu_storno_original_huf_rates=storno_huf_rates)
        action = super().reverse_moves(is_modify=is_modify)
        modification_document_type = self.env["l10n.hu.plus.tag"].search([
            ("company", "=", self.company_id.id),
            ("tag_type", "=", "document_type"),
            ("technical_name", "=", "invoice_modification"),
        ], limit=1)
        storno_document_type = self.env["l10n.hu.plus.tag"].search([
            ("company", "=", self.company_id.id),
            ("tag_type", "=", "document_type"),
            ("technical_name", "=", "invoice_storno"),
        ], limit=1)
        # only credit notes created by this reverse_moves call (is_modify leaves them out of new_move_ids)
        new_refunds = self.env["account.move"].search([
            ("move_type", "=", "out_refund"),
            ("reversed_entry_id", "in", move_ids),
            ("id", "not in", existing_refund_ids),
        ])
        if self.l10n_hu_storno_enabled and storno_document_type:
            for new_move in new_refunds:
                new_move.write({"l10n_hu_document_type": storno_document_type.id})
                # Run HU+ accounting automations and post it
                try:
                    new_move.action_l10n_hu_quick_accounting()
                    new_move.action_post()
                except Exception:
                    pass
                # one-shot after create: force original invoice HUF rate onto the storno (not a durable override)
                original_huf_rate = new_move.reversed_entry_id.l10n_hu_huf_rate
                if original_huf_rate and new_move.l10n_hu_huf_rate != original_huf_rate:
                    new_move.write({"l10n_hu_huf_rate": original_huf_rate})
        elif not self.l10n_hu_storno_enabled and modification_document_type:
            for new_move in new_refunds:
                new_move.write({"l10n_hu_document_type": modification_document_type.id})
        else:
            pass
        return action
