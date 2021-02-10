# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.multi
    def _prepare_purchase_order(self, product_id, product_qty, product_uom,
                                origin, values, partner):
        """
        Inherit this function to pass landed cost fields to PO when we create
        PO from SO, based on vendor in SO
        """
        res = super(StockRule, self)._prepare_purchase_order(product_id,
                                                             product_qty,
                                                             product_uom,
                                                             origin, values,
                                                             partner)
        res.update({'is_caln_factor': partner.landed_cost_factor,
                    'caln_factor': partner.landed_cost_factor})
        return res
