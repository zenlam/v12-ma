# -*- coding: utf-8 -*-

from odoo import fields, models


class Employee(models.Model):
    _inherit = 'hr.employee'

    approver_user_ids = fields.Many2many('res.users', 'rel_emp_user_approver', string='Leave Approve By')
    validator_user_ids = fields.Many2many('res.users', 'rel_emp_user_validator', string='Leave Validate By')

    is_hr_manager = fields.Boolean('Is Manager ?', compute="_compute_is_hr_manager")

    def _compute_is_hr_manager(self):
        if self.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
            for rec in self:
                rec.is_hr_manager = True
