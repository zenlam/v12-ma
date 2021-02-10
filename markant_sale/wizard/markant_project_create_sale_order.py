# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectCreateSalesOrder(models.TransientModel):
    _inherit = 'project.create.sale.order'

    so_commitment_date = fields.Datetime('SO Commitment Date')

    @api.multi
    def action_create_sale_order(self):
        # if project linked to SO line or at least on tasks with SO line, then we consider project as billable.
        if self.project_id.sale_line_id:
            raise UserError(_("The project is already linked to a sales order item."))

        if self.billable_type == 'employee_rate':
            # at least one line
            if not self.line_ids:
                raise UserError(_("At least one line should be filled."))

            # all employee having timesheet should be in the wizard map
            timesheet_employees = self.env['account.analytic.line'].search(
                [('task_id', 'in', self.project_id.tasks.ids)]).mapped('employee_id')
            map_employees = self.line_ids.mapped('employee_id')
            missing_meployees = timesheet_employees - map_employees
            if missing_meployees:
                raise UserError(_(
                    'The Sales Order cannot be created because you did not enter some employees that entered timesheets on this project. Please list all the relevant employees before creating the Sales Order.\nMissing employee(s): %s') % (
                                    ', '.join(missing_meployees.mapped('name'))))

        # check here if timesheet already linked to SO line
        timesheet_with_so_line = self.env['account.analytic.line'].search_count(
            [('task_id', 'in', self.project_id.tasks.ids), ('so_line', '!=', False)])
        if timesheet_with_so_line:
            raise UserError(_(
                'The sales order cannot be created because some timesheets of this project are already linked to another sales order.'))

        # create SO
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'analytic_account_id': self.project_id.analytic_account_id.id,
            'client_order_ref': self.project_id.name,
            'commitment_date': self.so_commitment_date
        })
        sale_order.onchange_partner_id()
        sale_order.onchange_partner_shipping_id()

        # create the sale lines, the map (optional), and assign existing timesheet to sale lines
        if self.billable_type == 'project_rate':
            self._make_billable_at_project_rate(sale_order)
        else:
            self._make_billable_at_employee_rate(sale_order)

        # confirm SO
        sale_order.action_confirm()

        view_form_id = self.env.ref('sale.view_order_form').id
        action = self.env.ref('sale.action_orders').read()[0]
        action.update({
            'views': [(view_form_id, 'form')],
            'view_mode': 'form',
            'name': sale_order.name,
            'res_id': sale_order.id,
        })
        return action


class ProjectCreateSalesOrderLine(models.TransientModel):
    _inherit = 'project.create.sale.order.line'

    so_commitment_date = fields.Datetime('SO Commitment Date')
