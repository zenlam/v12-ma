from odoo import api, fields, models


class ReportSalesPerson(models.AbstractModel):
    _name = "report.markant_crm.report_sale_person_email_automation"

    @api.multi
    def _get_report_values(self, docids, data=None):
        users = self.env['res.users'].browse(docids)
        lead_data = {}
        CrmLead = self.env['crm.lead']
        today = fields.Date.today()
        all_lead_ids = self.env.context.get('all_lead_ids', [])

        if all_lead_ids:
            # From Cron, To Reduce search again
            leads = CrmLead.browse(all_lead_ids)
        else:
            # Direct Print from the User
            common_dom = [
                ('type', '=', 'opportunity'),
                ('user_id', 'in', docids)
            ]

            leads = CrmLead.search(common_dom + [('date_deadline', '=', today)])
            leads |= CrmLead.search(common_dom + [('activity_ids.date_deadline', '=', today)])
            leads |= CrmLead.search(common_dom + [('dealer_oppor_info_ids.activity_ids.date_deadline', '=', today)])
            leads |= CrmLead.search(common_dom + [('next_action_date', '=', today)])
            leads |= CrmLead.search(
                common_dom + [('dealer_oppor_info_ids.next_action_date', '=', today)])

        for user in users:
            lead_data.update({
                user.id: leads.filtered(lambda r: r.user_id.id == user.id),
            })

        return {
            'doc_ids': users.ids,
            'doc_model': 'res.users',
            'docs': users,
            'lead_data': lead_data,
            'today': today,
        }
