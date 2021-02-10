from odoo import models, fields


class SaleProductConfigurator(models.TransientModel):
    _inherit = 'sale.product.configurator'
    _description = 'Sale Product Configurator'

    product_template_id = fields.Many2one(
        'product.template', string='Product',
        required=True, domain=[('sale_ok', '=', True), '|', '|',
                               ('configurable_ok', '!=', False),
                               ('attribute_line_ids.value_ids', '!=', False),
                               ('optional_product_ids', '!=', False)])
    product_d_number = fields.Char(string='D-Number')
