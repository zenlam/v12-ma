# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning


class OrderCycle(models.Model):
    _name = 'order.cycle'
    _description = 'Order Cycle'

    name = fields.Char(string="Order Cycle", required=True)
    description = fields.Char()
    active = fields.Boolean(default=True)
    is_default = fields.Boolean(string="Is Default ?")

    @api.one
    @api.constrains('is_default')
    def _check_is_default(self):
        if self.is_default:
            any_other_match = self.search([('is_default', '=', True)])
            any_other_match = any_other_match - self
            if any_other_match:
                raise Warning(_('You cannot set the two order cycle as default.'))


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    apply_order_cycle = fields.Boolean(string="Apply Order Cycle")
