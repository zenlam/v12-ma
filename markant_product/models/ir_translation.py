from odoo import api, fields, models, _


class IrTranslation(models.Model):
    _inherit = "ir.translation"

    @api.multi
    def action_change_state_translate(self):
        for rec in self:
            if rec.value:
                rec.state = 'translated'

    @api.multi
    def action_change_state_reset(self):
        for rec in self:
            if rec.source:
                rec.value = rec.source
                rec.state = False
