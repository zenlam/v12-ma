from odoo import api, fields, models, _


class VoipPhonecallCategory(models.Model):
    _name = 'markant.voip.phonecall.category'
    _description = 'Markant Voip Phonecall Category'

    name = fields.Char(string='Name', required=True)
