# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    incoterm_id = fields.Many2one('account.incoterms', 'Incoterm')
