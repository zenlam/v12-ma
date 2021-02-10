# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = "res.company"

    purchase_note = fields.Html(string='Default Terms and Conditions',
                                translate=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    purchase_note = fields.Html(related='company_id.purchase_note',
                                string="Terms & Conditions",
                                readonly=False)
    use_purchase_note = fields.Boolean(
        string="Default Terms & Conditions",
        config_parameter='markant_purchase.use_purchase_note'
    )
