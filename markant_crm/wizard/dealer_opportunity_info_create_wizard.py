import threading
from odoo import api, fields, models, _


class DealerOpportunityInfoCreateWizard(models.TransientModel):
    _name = 'dealer.opportunity.info.create.wizard'
    _description = 'Dealer Opportunity Info Create Wizard'

    partner_ids = fields.Many2many('res.partner', string='Add Dealers',
                                   required=True)

    @api.multi
    def create_dealer_opportunity_info(self):
        # create dealers.opportunity.info with info from crm.lead record
        crm_lead_id = self._context.get('active_id')
        added_dealer = self._context.get('added_dealer')
        crm_lead = self.env['crm.lead'].browse(crm_lead_id)
        DealersOpportunityInfo = self.env['dealers.opportunity.info']
        exist = DealersOpportunityInfo.search(
            [('opportunity_id', '=', crm_lead_id)], limit=1)
        count = len(self.partner_ids)
        set_prefered_dealer = False
        if not exist and count == 1:
            set_prefered_dealer = True
        for dealer in self.partner_ids:
            if added_dealer and added_dealer[0] and added_dealer[0][2] \
                    and dealer.id in added_dealer[0][2]:
                continue
            opp_vals = {
                'opportunity_id': crm_lead_id,
                'name': crm_lead.name,
                'partner_id': crm_lead.partner_id.id,
                'probability': crm_lead.probability,
                'other_currency_id': crm_lead.other_currency_id.id,
                'commission_per': crm_lead.commission,
                'planned_revenue_other_currency':
                    crm_lead.planned_revenue_other_currency,
                'date_deadline': crm_lead.date_deadline,
                'email_from': crm_lead.email_from,
                'phone': crm_lead.phone,
                'user_id': crm_lead.user_id.id,
                'dealer_id': dealer.id,
                'next_action_date': crm_lead.next_action_date,
                'title_action_date': crm_lead.title_action_date,
            }
            # call onchange function to compute some field
            oop_record = DealersOpportunityInfo.with_context(
                from_popup=1).create(opp_vals)
            oop_record.onchange_planned_revenue_other_currency()
            oop_record.onchange_other_currency()
            # set preferred dealer if only have 1 dealer
            if set_prefered_dealer:
                crm_lead.preferred_dealer_id = oop_record.dealer_id.id
            self.env.cr.commit()
            if self.env.user.id != oop_record.user_id.id:
                threaded_send_mail = threading.Thread(
                    target=self.send_mail_dealer_create,
                    args=(oop_record.id, ))
                threaded_send_mail.daemon = True
                threaded_send_mail.start()

    def send_mail_dealer_create(self, dealer_opp_info_id):
        with api.Environment.manage():
            new_env = api.Environment(self.pool.cursor(),
                                      self.env.uid,
                                      self.env.context)
            dealer_opp_info = new_env['dealers.opportunity.info'].browse(
                dealer_opp_info_id)
            template = new_env.ref(
                'markant_crm.email_template_dealer_opportunity_info_created')
            template.send_mail(res_id=dealer_opp_info.id, force_send=True)

    @api.onchange('partner_ids')
    def onchange_partner_ids(self):
        """
            filter select dealer not in added dealer on customer form
        :return:
        """
        added_dealer = self._context.get('added_dealer')
        domain = [('customer', '=', True)]
        if added_dealer and added_dealer[0] and added_dealer[0][2]:
            domain.append(('id', 'not in', added_dealer[0][2]))
            return {'domain': {'partner_ids': domain}}
