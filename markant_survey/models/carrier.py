from odoo import api, fields, models, _


class Carrier(models.Model):
    _name = 'carrier'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name')
    active = fields.Boolean(string='Active', default=True,
                            track_visibility='always')
    installation_link = fields.Boolean(string='Installation Form Link',
                                       default=False,
                                       copy=False,
                                       track_visibility='always')
