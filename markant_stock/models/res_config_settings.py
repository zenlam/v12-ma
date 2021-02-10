# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    revaluation_posting_journal_id = fields.Many2one(
        'account.journal',
        string="Revaluation Posting Journal",
        config_parameter='markant_stock.revaluation_posting_journal_id')
    revaluation_account_id = fields.Many2one(
        'account.account',
        string="Revaluation Account",
        config_parameter='markant_stock.revaluation_account_id'
    )
