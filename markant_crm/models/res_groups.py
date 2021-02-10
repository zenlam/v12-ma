from odoo import api, fields, models


class ResGroups(models.Model):
    _inherit = 'res.groups'

    @api.multi
    def name_get(self):
        result = []
        for group in self:
            result.append((group.id, group.name or ''))
        return result
