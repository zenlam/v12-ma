# -*- coding: utf-8 -*-
from odoo import fields, models, api


class PoLineScheduleDateChangeWizard(models.TransientModel):
    _name = 'po.line.schedule.date.change.wizard'

    date = fields.Date(string="Schedule Date")
    update_ex_works_date = fields.Date(string="Ex Works Date")
    update_confirmation_date = fields.Date(string="Confirmation Date")

    @api.multi
    def update_schedule_date(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        for record in self.env['purchase.order.line'].browse(active_ids):
            record.write({'date_planned': self.date})
            if self.update_ex_works_date:
                record.write({'ex_works_date': self.update_ex_works_date})
            if self.update_confirmation_date:
                record.write({'confirmation_date': self.update_confirmation_date})
        return {'type': 'ir.actions.act_window_close'}
