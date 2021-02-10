from odoo import api, fields, models, tools, _


class Company(models.Model):
    _inherit = "res.company"

    media_bank_start_url = fields.Char(string='Image URL', required=True,
                                       help='Do not put last / sign')
    media_bank_end_url = fields.Char(string='Image Extension', required=True,
                                     help='Example \n'
                                          ' * jpg \n'
                                          ' * png \n\n'
                                          'Do not use . notation')
