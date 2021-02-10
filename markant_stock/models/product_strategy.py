from odoo import api, fields, models


class FixedPutAwayStrategy(models.Model):
    _inherit = 'stock.fixed.putaway.strat'

    product_tmpl_id = fields.Many2one('product.template', 'Product Template')


class PutAwayStrategy(models.Model):
    _inherit = 'product.putaway'

    product_tmpl_location_ids = fields.One2many(
        'stock.fixed.putaway.strat', 'putaway_id',
        'Fixed Locations Per Product Template',
        domain=[('product_tmpl_id', '!=', False)], copy=True)

    def _get_putaway_rule(self, product):
        if self.product_location_ids:
            put_away = self.product_location_ids.filtered(lambda x: x.product_id == product)
            if put_away:
                return put_away[0]
        if self.product_tmpl_location_ids:
            product_tmpl = product.product_tmpl_id
            put_away = self.product_tmpl_location_ids.filtered(lambda x: x.product_tmpl_id == product_tmpl)
            if put_away:
                return put_away[0]
        if self.fixed_location_ids:
            categ = product.categ_id
            while categ:
                put_away = self.fixed_location_ids.filtered(lambda x: x.category_id == categ)
                if put_away:
                    return put_away[0]
                categ = categ.parent_id
        return self.env['stock.location']
