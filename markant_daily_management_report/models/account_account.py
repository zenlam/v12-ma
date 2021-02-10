from odoo import api, fields, models, _


class AccountAccount(models.Model):
    _inherit = 'account.account'

    is_daily_management = fields.Boolean('For Daily Management Report',
                                         default=False)
