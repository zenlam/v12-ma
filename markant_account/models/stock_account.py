from odoo import api, fields, models, _


class StockMove(models.Model):
    _inherit = "stock.move"

    def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id):
        """
        Override from stock_account base, to pass so/po ref
        """
        self.ensure_one()
        AccountMove = self.env['account.move']
        quantity = self.env.context.get('forced_quantity', self.product_qty)
        quantity = quantity if self._is_in() else -1 * quantity

        # Make an informative `ref` on the created account move to differentiate between classic
        # movements, vacuum and edition of past moves.
        ref = self.picking_id.name
        so_po = ''
        if self.picking_id.sale_id:
            so_po = self.picking_id.sale_id.name
        if self.picking_id.purchase_id_stored:
            so_po = self.picking_id.purchase_id_stored.name

        if self.env.context.get('force_valuation_amount'):
            if self.env.context.get('forced_quantity') == 0:
                ref = 'Revaluation of %s (negative inventory)' % ref
            elif self.env.context.get('forced_quantity') is not None:
                ref = 'Correction of %s (modification of past move)' % ref

        move_lines = self.with_context(forced_ref=ref)._prepare_account_move_line(quantity, abs(self.value), credit_account_id, debit_account_id)

        for move in move_lines:
            move[2].update({'so_po_ref': so_po})
        if move_lines:
            date = self._context.get('force_period_date', fields.Date.context_today(self))
            new_account_move = AccountMove.sudo().create({
                'journal_id': journal_id,
                'line_ids': move_lines,
                'date': date,
                'ref': ref,
                'stock_move_id': self.id,
                'so_po_ref': so_po
            })
            new_account_move.post()

