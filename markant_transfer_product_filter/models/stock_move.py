# -*- coding: utf-8 -*-

from odoo import fields, models, api

class StockMove(models.Model):
    _inherit = "stock.move"

    @api.onchange('product_id')
    def _onchange_product_id_picking_location(self):
        if self.picking_type_id.code == 'internal':
            product_list = []
            quant_ids = self.env['stock.quant'].search([('location_id', '=', self.location_id.id)])
            for quant in quant_ids:
            	if quant.quantity - quant.reserved_quantity > 0:
                	product_list.append(quant.product_id.id)
            return {'domain':{'product_id': [('id', 'in', product_list)]}}
