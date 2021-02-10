from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    qty_signed_total = fields.Float(string="Total Forecast Qty",
                                    compute='_compute_total_forecast',
                                    digits=dp.get_precision(
                                        'Product Unit of Measure'),
                                    default=0.0)

    @api.multi
    def _compute_total_forecast(self):
        for record in self:
            product_ids = record.product_variant_ids.ids
            moves = self.env['stock.move'].search(
                [('product_id', 'in', product_ids)])
            for move in moves:
                record.qty_signed_total += move.qty_signed

    def show_forecast_move(self):
        product_tree_view = self.env.ref(
            'markant_forecasted.stock_view_move_tree_inherit_sum_quantity')
        product_form_view = self.env.ref('stock.view_move_form')
        product_pivot_view = self.env.ref('stock.view_move_pivot')
        product_graph_view = self.env.ref('stock.view_move_graph')
        product_kanban_view = self.env.ref('stock.view_move_kandan')
        product_ids = self.env['product.product'].search(
            [('product_tmpl_id', '=', self.id)])
        domain = [('product_id', 'in', product_ids.ids)]
        return {
            'name': _('Forecast Move'),
            'domain': domain,
            'view_type': 'form',
            'view_mode': 'tree,form,pivot,graph,kanban',
            'res_model': 'stock.move',
            'type': 'ir.actions.act_window',
            'views': [(product_tree_view.id, 'tree'),
                      (product_form_view.id, 'form'),
                      (product_pivot_view.id, 'pivot'),
                      (product_graph_view.id, 'graph'),
                      (product_kanban_view.id, 'kanban')],
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    qty_signed_total = fields.Float(string="Total Forecast Qty",
                                    compute='_compute_total_forecast',
                                    digits=dp.get_precision(
                                        'Product Unit of Measure'),
                                    default=0.0)

    @api.multi
    def _compute_total_forecast(self):
        for record in self:
            moves = self.env['stock.move'].search(
                [('product_id', '=', record.id)])
            for move in moves:
                record.qty_signed_total += move.qty_signed

    def show_forecast_move(self):
        product_tree_view = self.env.ref(
            'markant_forecasted.stock_view_move_tree_inherit_sum_quantity')
        product_form_view = self.env.ref('stock.view_move_form')
        product_pivot_view = self.env.ref('stock.view_move_pivot')
        product_graph_view = self.env.ref('stock.view_move_graph')
        product_kanban_view = self.env.ref('stock.view_move_kandan')
        domain = [('product_id', '=', self.id)]
        return {
            'name': _('Forecast Move'),
            'domain': domain,
            'view_type': 'form',
            'view_mode': 'tree,form,pivot,graph,kanban',
            'res_model': 'stock.move',
            'type': 'ir.actions.act_window',
            'views': [(product_tree_view.id, 'tree'),
                      (product_form_view.id, 'form'),
                      (product_pivot_view.id, 'pivot'),
                      (product_graph_view.id, 'graph'),
                      (product_kanban_view.id, 'kanban')],
        }


class StockMove(models.Model):
    _inherit = 'stock.move'

    qty_signed = fields.Float(string='Forecast Quantity',
                              compute='_compute_qty_signed',
                              digits=dp.get_precision(
                                  'Product Unit of Measure'),
                              help='Quantity with +/- sign to indicate '
                                   'outgoing or incoming quantity',
                              store=True)

    @api.depends('product_qty', 'state')
    def _compute_qty_signed(self):
        Product = self.env['product.product']
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = \
            Product._get_domain_locations()
        domain_move_in = [('state', 'not in',
                           ('draft', 'cancel'))] + domain_move_in_loc
        domain_move_out = [('state', 'not in',
                            ('draft', 'cancel'))] + domain_move_out_loc
        incoming_moves = self.env['stock.move'].search(domain_move_in)
        outgoing_moves = self.env['stock.move'].search(domain_move_out)

        for move in incoming_moves:
            move.qty_signed = move.product_qty

        for move in outgoing_moves:
            move.qty_signed = -move.product_qty

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None,
                   orderby=False, lazy=True):
        """
        Inherit this function to show total for qty_signed column in group by
        """
        res = super(StockMove, self).read_group(domain, fields, groupby,
                                                offset, limit=limit,
                                                orderby=orderby, lazy=lazy)
        if 'qty_signed' in fields:
            for line in res:
                if '__domain' in line:
                    lines = self.search(line['__domain'])
                    qty = 0.0
                    for record in lines:
                        qty += record.qty_signed
                    line['qty_signed'] = qty
        return res
