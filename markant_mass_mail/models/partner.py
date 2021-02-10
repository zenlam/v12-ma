from odoo import api, fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    mass_mail_count = fields.Integer('Mass Mail Count',
                                     compute="_compute_mass_mail_count")
    partner_unique_tag = fields.Char('Partner Unique Tag')

    def _compute_mass_mail_count(self):
        Statistics = self.env['mail.mail.statistics']
        for partner in self:
            partner.mass_mail_count = Statistics.search_count(
                [('partner_id', '=', partner.id)])

    @api.model
    def create(self, vals):
        partner = super(Partner, self).create(vals)
        statistics = self.env['mail.mail.statistics'].search(
            [('email_to', 'like', partner.email)])
        statistics.write({'partner_id': partner.id})
        return partner
