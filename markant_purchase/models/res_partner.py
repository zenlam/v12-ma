from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    purchase_user_id = fields.Many2one(
        'res.users', string='Purchaser',
        domain=lambda self: [
            ('groups_id', 'in',
             [self.env.ref('purchase.group_purchase_user').id,
              self.env.ref('purchase.group_purchase_manager').id])
        ])
