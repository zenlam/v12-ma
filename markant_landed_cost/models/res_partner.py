# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    landed_cost_factor = fields.Float(string="Landed Cost Factor(%)",
                                      help="Percentage of Landed Cost "
                                           "Applied to Contact")

    @api.multi
    def write(self, vals):
        if vals.get('landed_cost_factor', False):
            if vals['landed_cost_factor'] < 0:
                raise UserError(
                    _("Landed Cost Factor should not be negative!"))
        return super(ResPartner, self).write(vals)
