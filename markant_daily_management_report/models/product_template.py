from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_group = fields.Selection([('install', 'Installation & Repair'),
                                      ('service', 'Service Product')],
                                     string='Service Group')

class ProductProduct(models.Model):
    _inherit = "product.product"

    stored_standard_price = fields.Float(related='standard_price', store=True)
