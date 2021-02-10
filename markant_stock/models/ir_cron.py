# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import api, fields, models, _
from datetime import timedelta
from odoo.exceptions import ValidationError
from datetime import datetime

_logger = logging.getLogger(__name__)


class ir_cron(models.Model):
    _inherit = "ir.cron"

    procurement_scheduler = fields.Boolean('Procurement Scheduler')

    @api.constrains('procurement_scheduler')
    def _check_duplicate_procurement_scheduler(self):
        for cron in self:
            ir_cron = self.search([
                ('procurement_scheduler', '=', cron.procurement_scheduler),
                ('id', '!=', cron.id)])
            if cron.procurement_scheduler and ir_cron:
                raise ValidationError(_('You can only have 1 procurement scheduler'))

    @api.model
    def _do_start_procurement_scheduler_cron(self):
        cr = self.env.cr
        scheduler_cron = self.env['ir.cron'].search([('procurement_scheduler', '=', True), ('active', '=', False)])
        next_date = fields.Datetime.now() + timedelta(minutes=5)
        if scheduler_cron:
            cr.execute("UPDATE ir_cron SET nextcall=%s, active=%s WHERE id=%s", (next_date, True, scheduler_cron.id))
        return True

    @api.model
    def _do_stop_procurement_scheduler_cron(self):
        cr = self.env.cr
        scheduler_cron = self.env['ir.cron'].search([('procurement_scheduler', '=', True), ('active', '=', True)])
        if scheduler_cron:
            cr.execute("UPDATE ir_cron SET active=%s WHERE id=%s", (False, scheduler_cron.id))
        return True
