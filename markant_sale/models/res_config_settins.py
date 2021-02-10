# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    project_disc_default_product_id = fields.Many2one(
        'product.product',
        'Product used for Project Discount',
        domain="[('type', '=', 'service')]",
        config_parameter='sale.project_disc_default_product_id',
        help='Default product used for Project Discount')

    admin_cost_default_product_id = fields.Many2one(
        'product.product',
        'Product used for Minimum Adminstrative Cost',
        domain="[('type', '=', 'service')]",
        config_parameter='sale.admin_cost_default_product_id',
        help='Product used for Minimum Adminstrative Cost')

    admin_cost_default_min_amount = fields.Float(string='Minimum Amount',
        config_parameter='sale.admin_cost_default_min_amount')
    admin_cost_default_admin_amount = fields.Float(string='Admin Amount',
        config_parameter='sale.admin_cost_default_admin_amount')

    enable_lock_sales_automatic = fields.Boolean(string="Lock Sales Automatically",
        config_parameter='sale.enable_lock_sales_automatic',
        help="Enable/Disable Auto locking on sales.")
    time_needed_lock_sales = fields.Integer(string='Lock Time',
        config_parameter='sale.time_needed_lock_sales',
        help='Time needed to lock the confirmed SO automatically.', default=24)

    sale_notes = fields.Html('Terms and conditions',
                             related='company_id.sale_notes',
                             readonly=False)


class ResCompany(models.Model):
    _inherit = "res.company"

    sale_notes = fields.Html(string='Default Terms and Conditions',
                             translate=True)
