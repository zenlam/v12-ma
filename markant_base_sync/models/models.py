# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    base_lead_ids = fields.Char(readonly=True)
    base_lead_source_id = fields.Many2one('base.lead.source', string="Source")
    base_group_ids = fields.Many2many(
                    'base.lead.group',
                    'base_lead_group_fields_rel',
                    'base_lead_group_partner_id',
                    'base_lead_group_group_id',
                    string='Groups')


class Phonecall(models.Model):
    _inherit = 'voip.phonecall'

    base_note_task_id = fields.Char(readonly=True)
    base_sync_type = fields.Selection([('note', 'Note'), ('task', 'Task'), ('email', 'Email')], readonly=True)


class ResCountry(models.Model):
    _inherit = 'res.country'

    base_country_name = fields.Char()
