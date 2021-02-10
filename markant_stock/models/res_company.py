from odoo import api, fields, models, _


class Company(models.Model):
    _inherit = 'res.company'

    no_of_packaging_prints = fields.Integer(string='No. of Packaging Prints',
                                            default=4)
