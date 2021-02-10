from odoo import api, fields, models, _


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        self.address_id = self.employee_id.sudo().address_home_id
        self.department_id = self.employee_id.sudo().department_id
        self.user_id = self.employee_id.sudo().expense_manager_id or self.employee_id.sudo().parent_id.user_id
