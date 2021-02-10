from odoo import models, fields, api, _


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.onchange('partner_type')
    def _onchange_partner_type(self):
        self.ensure_one()
        res = super(AccountPayment, self)._onchange_partner_type()
        if self.partner_type and res.get('domain') and res['domain']['partner_id']:
            res['domain']['partner_id'].insert(0, '|')
            res['domain']['partner_id'].append(('end_user', '=', True))
        return res
