# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    interim_account_journal_id = fields.Many2one(
        'account.journal',
        string="Interim Journal",
        config_parameter='markant_account.interim_account_journal_id'
    )
