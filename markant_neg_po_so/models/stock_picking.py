from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    to_hide_column = fields.Boolean('Hide Create Negative SO/PO',
                                    compute='_compute_hide_column',
                                    invisible=True, store=True)

    @api.multi
    @api.depends('picking_type_id')
    def _compute_hide_column(self):
        """
        Hide the 'To Create Negative SO/PO' column in return picking wizard
        """
        for record in self:
            record.to_hide_column = False
            if record.picking_type_code not in ('incoming', 'outgoing'):
                record.to_hide_column = True

    @api.multi
    def action_cancel(self):
        """
        Inherit picking cancel button to cancel the negative PO/SO that is
        linked to the picking when the picking is cancelled
        """
        super(StockPicking, self).action_cancel()
        for record in self:
            neg_po = self.env['purchase.order'].search(
                [('origin_picking', '=', record.id)])
            neg_so = self.env['sale.order'].search(
                [('origin_picking', '=', record.id)])
            if neg_po:
                neg_po.button_cancel()
            elif neg_so:
                neg_so.action_cancel()
