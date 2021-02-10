# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class LandedCostConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    factor_product = fields.Char('Caln Factor Product', readonly=True)
    caln_factor_product = fields.Many2one('product.product',
                                          'Caln Factor Product',
                                          domain=
                                          "[('landed_cost_ok', '=', True)]",
                                          related="company_id.default_"
                                                  "caln_factor_product",
                                          readonly=False)

    journal_name = fields.Char('Landed Cost Journal', readonly=True)
    account_journal_id = fields.Many2one('account.journal',
                                         'Landed Cost Journal',
                                         related="company_id.default_"
                                                 "lcost_journal",
                                         readonly=False)
