from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_image = fields.Binary(related='product_id.image_medium',
                                  attachment=True,
                                  readonly=True, string='Product Image')
    product_image_small = fields.Binary(related='product_id.image_small',
                                  attachment=True,
                                  readonly=True, string='Product Image')
