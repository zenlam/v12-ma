from odoo import api, fields, models, _


class TroubleResponsible(models.Model):
    _name = 'trouble.responsible'
    _description = 'Trouble Responsible'

    name = fields.Char(string='Name')
    active = fields.Boolean(string='Active', default=True)

    @api.model
    def create_default(self):
        self.create({'name': 'Transport Inbound'})
        self.create({'name': 'Transport Outbound'})
        self.create({'name': 'Supplier'})
        self.create({'name': 'Dealer'})
        self.create({'name': 'End User'})
        self.create({'name': 'Markant'})
