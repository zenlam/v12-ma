from odoo import api, fields, models, _


class AutoInvoiceMail(models.Model):
    _name = 'auto.invoice.mail'
    _description = 'Auto Invoice Mail'
    _rec_name = 'user_id'

    user_id = fields.Many2one('res.users', string='Contact', required=True)
    email = fields.Char(string='Email', required=True)

    @api.onchange('user_id')
    def onchange_user_id(self):
        if self.user_id:
            self.email = self.user_id.partner_id.email
