from odoo import api, fields, models, _


class DailyManagementReportWizard(models.TransientModel):
    _name = "daily.management.report.wiz"

    start_date = fields.Date('Start Date',
                             help="Left Empty if want to print all record")

    @api.multi
    def action_print(self):
        report_name = 'daily_management_report_wiz'
        report = {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'report_name': report_name,
            'context': dict(self.env.context),
            'data': {'dynamic_report': True},
        }
        return report
