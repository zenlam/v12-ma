# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    purchase_order_id = fields.Many2one(comodel_name="purchase.order",
                                        string="Purchase Order")

    @api.multi
    def action_view_journal_item(self):
        self.ensure_one()
        action = self.env.ref(
            'account.action_account_moves_all_a').read()[0]
        action['domain'] = [('move_id', '=', self.account_move_id.id)]
        return action

    def get_valuation_lines(self):
        """
        Remove valuation line that the quantity is zero, else will cause
        division with zero error
        """
        lines = super(StockLandedCost, self).get_valuation_lines()
        lines = [line for line in lines if line.get('quantity')]
        return lines

    @api.model
    def _update_ref_in_old_data(self):
        for lc in self.sudo().search([]):
            if lc.purchase_order_id and lc.account_move_id:
                for mv_line in self.env['account.move.line'].sudo().search([
                    ('move_id', '=', lc.account_move_id.id)]):
                    so_po = lc.purchase_order_id.name
                    partner = lc.purchase_order_id.partner_id.id
                    mv_line.so_po_ref = so_po or ''
                    mv_line.partner_id = partner or False


class AdjustmentLines(models.Model):
    _inherit = 'stock.valuation.adjustment.lines'

    # Override method
    def _create_account_move_line(self, move, credit_account_id, debit_account_id, qty_out, already_out_account_id):
        """
        Generate the account.move.line values to track the landed cost.
        Afterwards, for the goods that are already out of stock, we should create the out moves
        """
        AccountMoveLine = []

        base_line = {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': 0,
        }
        debit_line = dict(base_line, account_id=debit_account_id)
        credit_line = dict(base_line, account_id=credit_account_id)

        if self.move_id and self.move_id.picking_id and \
                self.move_id.picking_id.purchase_id_stored:
            so_po = self.move_id.picking_id.purchase_id_stored.name
            debit_line['so_po_ref'] = so_po
            credit_line['so_po_ref'] = so_po

            partner = \
                self.move_id.picking_id.purchase_id_stored.partner_id.id
            debit_line['partner_id'] = partner
            credit_line['partner_id'] = partner

        diff = self.additional_landed_cost
        if diff > 0:
            debit_line['debit'] = diff
            credit_line['credit'] = diff
        else:
            # negative cost, reverse the entry
            debit_line['credit'] = -diff
            credit_line['debit'] = -diff
        AccountMoveLine.append([0, 0, debit_line])
        AccountMoveLine.append([0, 0, credit_line])

        # Create account move lines for quants already out of stock
        if qty_out > 0:
            debit_line = dict(base_line,
                              name=(self.name + ": " + str(qty_out) + _(' already out')),
                              quantity=0,
                              account_id=already_out_account_id)
            credit_line = dict(base_line,
                               name=(self.name + ": " + str(qty_out) + _(' already out')),
                               quantity=0,
                               account_id=debit_account_id)

            if self.move_id and self.move_id.picking_id and \
                    self.move_id.picking_id.purchase_id_stored:
                so_po = self.move_id.picking_id.purchase_id_stored.name
                debit_line['so_po_ref'] = so_po
                credit_line['so_po_ref'] = so_po

                partner = \
                    self.move_id.picking_id.purchase_id_stored.partner_id.id
                debit_line['partner_id'] = partner
                credit_line['partner_id'] = partner

            diff = diff * qty_out / self.quantity
            if diff > 0:
                debit_line['debit'] = diff
                credit_line['credit'] = diff
            else:
                # negative cost, reverse the entry
                debit_line['credit'] = -diff
                credit_line['debit'] = -diff
            AccountMoveLine.append([0, 0, debit_line])
            AccountMoveLine.append([0, 0, credit_line])

            # TDE FIXME: oh dear
            if self.env.user.company_id.anglo_saxon_accounting:
                debit_line = dict(base_line,
                                  name=(self.name + ": " + str(qty_out) + _(' already out')),
                                  quantity=0,
                                  account_id=credit_account_id)
                credit_line = dict(base_line,
                                   name=(self.name + ": " + str(qty_out) + _(' already out')),
                                   quantity=0,
                                   account_id=already_out_account_id)

                if self.move_id and self.move_id.picking_id and \
                        self.move_id.picking_id.purchase_id_stored:
                    so_po = self.move_id.picking_id.purchase_id_stored.name
                    debit_line['so_po_ref'] = so_po
                    credit_line['so_po_ref'] = so_po

                    partner = \
                        self.move_id.picking_id.purchase_id_stored.\
                        partner_id.id
                    debit_line['partner_id'] = partner
                    credit_line['partner_id'] = partner

                if diff > 0:
                    debit_line['debit'] = diff
                    credit_line['credit'] = diff
                else:
                    # negative cost, reverse the entry
                    debit_line['credit'] = -diff
                    credit_line['debit'] = -diff
                AccountMoveLine.append([0, 0, debit_line])
                AccountMoveLine.append([0, 0, credit_line])
        return AccountMoveLine
