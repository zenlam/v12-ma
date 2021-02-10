# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _create_returns(self):
        """
        Inherit this to untick is_caln_factor and set caln_factor to 0 for
        reverse picking even the PO and picking have landed cost applied
        """
        new_picking_id, picking_type_id = super(ReturnPicking,
                                                self)._create_returns()
        if new_picking_id:
            picking = self.env['stock.picking'].browse(new_picking_id)
            picking.update({
                'is_caln_factor': False,
                'caln_factor': 0.0,
            })
        return new_picking_id, picking_type_id
