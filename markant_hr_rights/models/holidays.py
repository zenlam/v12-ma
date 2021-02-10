# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Holidays(models.Model):
    _inherit = 'hr.leave'

    def _check_approval_update(self, state):
        """ Check if target state is achievable. """
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        # is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        # is_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_manager')
        is_manager = self.env.user.has_group('markant_hr_rights.group_hr_super_manager')
        user = self.env.user
        for holiday in self:
            val_type = holiday.holiday_status_id.validation_type
            if state == 'confirm':
                continue

            if state == 'draft':
                if holiday.employee_id != current_employee and not is_manager:
                    raise UserError(_('Only a Super Manager can reset other people leaves.'))
                continue

            if state == 'validate1':
                if not is_manager and user.id not in holiday.employee_id.approver_user_ids.ids:
                    raise UserError(_('Only a Super Manager or Leave Approver can approve or refuse leave requests.'))

            else:
                if not is_manager and user.id not in holiday.employee_id.validator_user_ids.ids:
                    raise UserError(_('Only a Super Manager or Leave Validators can validate leave requests.'))

            # if is_manager:
                # use ir.rule based first access check: department, members, ... (see security.xml)
                # holiday.check_access_rule('write')

            if holiday.employee_id == current_employee and not is_manager:
                raise UserError(_('Only a Super Manager can approve its own requests.'))

            if (state == 'validate1' and val_type == 'both') or (state == 'validate' and val_type == 'manager'):
                # manager = holiday.employee_id.parent_id or holiday.employee_id.department_id.manager_id
                if not is_manager and user.id not in holiday.employee_id.approver_user_ids.ids:
                    raise UserError(_('You must be either %s\'s Super manager or Leave Validator to approve this leave') % (holiday.employee_id.name))

            if state == 'validate' and val_type == 'both':
                if not is_manager and user.id not in holiday.employee_id.validator_user_ids.ids:
                    raise UserError(_('Only a Super Manager or Leave Validators can apply the second approval on leave requests.'))

    @api.model
    def create(self, vals):
        record = super(Holidays, self).create(vals)
        leave_template = self.env.ref('markant_hr_rights.email_template_markant_hr_leave_request')
        leave_template.send_mail(record.id, force_send=True)
        return record


class Allocation(models.Model):
    _inherit = 'hr.leave.allocation'

    @api.model
    def create(self, vals):
        record = super(Allocation, self).create(vals)
        leave_template = self.env.ref('markant_hr_rights.email_template_markant_hr_allocation_request')
        leave_template.send_mail(record.id, force_send=True)
        return record


# class Status(models.Model):
#     _inherit = 'hr.leave.type'

#     @api.multi
#     def get_days(self, employee_id):
#         # need to use `dict` constructor to create a dict per id
#         result = dict((id, dict(max_leaves=0, leaves_taken=0, remaining_leaves=0, virtual_remaining_leaves=0)) for id in self.ids)

#         holidays = self.env['hr.leave'].search([
#             ('employee_id', '=', employee_id),
#             ('state', 'in', ['confirm', 'validate1', 'validate']),
#             ('holiday_status_id', 'in', self.ids)
#         ])

#         for holiday in holidays:
#             status_dict = result[holiday.holiday_status_id.id]
#             if holiday.type == 'add':
#             status_dict['virtual_remaining_leaves'] += holiday.number_of_days_temp
#             if holiday.state == 'validate':
#                 note: add only validated allocation even for the virtual
#                 count; otherwise pending then refused allocation allow
#                 the employee to create more leaves than possible
#                 status_dict['max_leaves'] += holiday.number_of_days_temp
#                 status_dict['remaining_leaves'] += holiday.number_of_days_temp
#             elif holiday.type == 'remove':  # number of days is negative
#                 status_dict['virtual_remaining_leaves'] -= holiday.number_of_days_temp
#                 if holiday.state == 'validate':
#                     status_dict['leaves_taken'] += holiday.number_of_days_temp
#                     status_dict['remaining_leaves'] -= holiday.number_of_days_temp
#         return result
