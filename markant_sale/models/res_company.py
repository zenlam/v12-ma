# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    inst_notification_email = fields.Char(string='IF Notification Email')
