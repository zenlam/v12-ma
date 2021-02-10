# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    default_caln_factor_product = fields.Many2one('product.product',
                                                  'Caln Factor Product',
                                                  domain=
                                                  "[('landed_cost_ok',"
                                                  " '=', True)]")
    default_lcost_journal = fields.Many2one('account.journal',
                                            'Landed Cost Journal')
