# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.base.models import ir_mail_server


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    smtp_timeout = fields.Char(string="Outgoing Mail Timeout", readonly=True)
    smtp_customize_timeout = fields.Integer(string="Customizable Timeout",
                                            default=60,
                                            config_parameter='markant_smtp'
                                                             '.smtp_timeout')

    @api.onchange('smtp_customize_timeout')
    def set_smtp_timeout_values(self):
        for x in self:
            if x.smtp_customize_timeout > 0:
                ir_mail_server.SMTP_TIMEOUT = self.smtp_customize_timeout
            else:
                raise UserError(_('Negative values are not allowed.'))
