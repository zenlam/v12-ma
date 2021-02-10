# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import Warning


class MarkantInstallationStage(models.Model):
    _name = 'markant.installation.stage'
    _description = 'Stages for Installation'
    _rec_name = 'name'
    _order = 'sequence'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=1,
                              help="Used to order stages. Lower is better.")
    enable_mail = fields.Boolean(string='Enable Send Mail Button')
    enable_preview = fields.Boolean(string='Enable Preview & Sign Button')
    enable_required = fields.Boolean(string='Enable Required Fields')
    top_lock = fields.Boolean(string='Top Lock')
    bottom_lock = fields.Boolean(string='Bottom Lock')
    cancel_stage = fields.Boolean(string='Cancel Stage')

    @api.constrains('cancel_stage')
    def _check_duplicate_stage(self):
        cancel_stage_count = self.search_count(
            [('cancel_stage', '=', True)])
        if cancel_stage_count > 1:
            raise Warning(_('You can only have 1 cancelled stage!'))
        if cancel_stage_count < 1:
            raise Warning(_('You need to define 1 cancelled stage!'))


class MarkantInstallationType(models.Model):
    _name = 'markant.installation.type'
    _description = 'Installation Type'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True, copy=False)
    require_initial_so = fields.Boolean(string='Require Initial SO')


class MarkantCalculationType(models.Model):
    _name = 'markant.calculation.type'
    _description = 'Calculation Type'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True, copy=False)
