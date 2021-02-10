from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def variant_create_reordering(self):
        self.ensure_one()

        variant_reordering = self.env['stock.warehouse.orderpoint']

        reordering_vals = {
            'product_id': self.id,
            'product_min_qty': 0.0,
            'product_max_qty': 0.0,
        }

        reordering = variant_reordering.create(reordering_vals)
        return reordering

    @api.model_create_multi
    def create(self, vals_list):
        res = super(ProductProduct, self).create(vals_list)

        manuf_id = self.env.ref('mrp.route_warehouse0_manufacture').id
        buy_id = self.env.ref('purchase_stock.route_warehouse0_buy').id
        make_order_id = self.env.ref('stock.route_warehouse0_mto').id

        for prod in res:
            reordering = self.env['stock.warehouse.orderpoint'] \
                .search([('product_id', '=', prod.id)], limit=1)
            if (buy_id in prod.route_ids.ids or manuf_id in prod.route_ids.ids) \
                    and make_order_id not in prod.route_ids.ids \
                    and not reordering:
                prod.variant_create_reordering()

        return res


class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.multi
    def create_products_for_bom(self, new_prod_attr_vals_lst, conf_line):
        res = super(StockRule, self).create_products_for_bom(
            new_prod_attr_vals_lst, conf_line)

        manuf_id = self.env.ref('mrp.route_warehouse0_manufacture').id
        buy_id = self.env.ref('purchase_stock.route_warehouse0_buy').id
        make_order_id = self.env.ref('stock.route_warehouse0_mto').id

        for prod in res:
            reordering = self.env['stock.warehouse.orderpoint'] \
                .search([('product_id', '=', prod.id)], limit=1)
            if (buy_id in prod.route_ids.ids or manuf_id in prod.route_ids.ids) \
                    and make_order_id not in prod.route_ids.ids \
                    and not reordering:
                prod.variant_create_reordering()

        return res
