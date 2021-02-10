# -*- coding: utf-8 -*-

from odoo import api, fields, models


class BaseCrmConfigSettings(models.TransientModel):
    """
    Purpose of this model : Allow user to configure the setting of API to connect to BaseCrm
    """
    _inherit = 'res.config.settings'

    base_access_token = fields.Char(string='AS400 URL')
    base_sync_active = fields.Boolean(string='Active')
    base_owner_id = fields.Many2one('res.users', string='Base Owner')
    module_markant_base_sync = fields.Boolean(string="Markant Base CRM")

    @api.model
    def get_values(self):
        res = super(BaseCrmConfigSettings, self).get_values()
        Params = self.env['ir.config_parameter']
        base_access_token = Params.get_param('base_access_token', default='')
        base_sync_active = Params.get_param('base_sync_active', default='')
        base_owner_id = Params.get_param('base_owner_id', default=False)
        if base_owner_id:
            base_owner_id = int(base_owner_id)
        res.update({
            'base_access_token': base_access_token,
            'base_sync_active': base_sync_active,
            'base_owner_id': base_owner_id
        })
        return res

    @api.one
    def set_values(self):
        super(BaseCrmConfigSettings, self).set_values()
        Params = self.env['ir.config_parameter']
        Params.set_param('base_access_token', self.base_access_token or '')
        Params.set_param('base_sync_active', self.base_sync_active or '')
        Params.set_param('base_owner_id', self.base_owner_id and self.base_owner_id.id or '')
