from odoo import api, fields, models, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _default_groups(self):
        """
        add default group for create new user: 'call visit report - sale group'
        :return:
        """
        default_user = self.env.ref('base.default_user',
                                    raise_if_not_found=False)
        groups_id = (default_user or self.env['res.users']).sudo().groups_id
        call_visit_sale_group = self.env['res.groups'].browse(
            self.env.ref('markant_crm.group_call_visit_sales').id)
        groups_id |= call_visit_sale_group
        return groups_id

    groups_id = fields.Many2many('res.groups', 'res_groups_users_rel',
                                 'uid', 'gid',
                                 string='Groups', default=_default_groups)

    @api.model
    def send_mail_to_sale_person(self):
        """
        send email when opp, child opp today = date_deadline,
        next_action_date, activity date
        only send one email for all opp
        :return:
        """
        template = self.env.ref(
            'markant_crm.email_template_markant_sale_person')
        CrmLead = self.env['crm.lead']
        today = fields.Date.today()

        common_dom = [
            ('type', '=', 'opportunity'),
        ]

        all_leads = CrmLead.search(
            common_dom + [('date_deadline', '=', today)])
        all_leads |= CrmLead.search(
            common_dom + [('activity_ids.date_deadline', '=', today)])
        all_leads |= CrmLead.search(
            common_dom + [
                ('dealer_oppor_info_ids.activity_ids.date_deadline', '=',
                 today)])
        all_leads |= CrmLead.search(
            common_dom + [('next_action_date', '=', today)])
        all_leads |= CrmLead.search(
            common_dom + [
                ('dealer_oppor_info_ids.next_action_date', '=', today)])
        for user in all_leads.mapped('user_id').filtered(lambda r: r.active):
            template.with_context(all_lead_ids=all_leads.ids).send_mail(
                user.id, force_send=True)
        return True
