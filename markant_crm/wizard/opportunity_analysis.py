from odoo import api, fields, models


class OpportunityAnalysis(models.TransientModel):
    _name = 'opportunity.analysis'
    _description = 'Opportunity Analysis'

    user_id = fields.Many2one('res.users', 'Salesperson')
    dealer_id = fields.Many2one('res.partner',
                                string='Dealer',
                                domain=[('customer', '=', True)])
    influencer_id = fields.Many2one(
        'res.partner',
        string='Influencer',
        domain=[('influencer', '=', True)])
    other_currency_id = fields.Many2one('res.currency', 'Currency')
    in_base_currency = fields.Boolean('In Base Currency')
    expected_revenue_from = fields.Float('Expected Revenue')
    expected_revenue_to = fields.Float('To')
    date_action_from = fields.Date('Next Action')
    date_action_to = fields.Date('To')
    date_deadline_from = fields.Date('Expected Closing')
    date_deadline_to = fields.Date('To')
    currency_ids = fields.Many2many(
                    'res.currency',
                    'opp_currency_rel',
                    'currency_id',
                    'oppo_id',
                    string='Currency')
    stage_ids = fields.Many2many(
                    'crm.stage',
                    'opp_case_stage_rel',
                    string='Stage')

    @api.multi
    def _check_to_date(self):
        if self.date_action_from > self.date_action_to:
            return False
        if self.date_deadline_from > self.date_deadline_to:
            return False
        return True

    @api.multi
    def _check_expected_revenue_to(self):
        if self.expected_revenue_from > self.expected_revenue_to:
            return False
        return True

    _constraints = [
        (_check_expected_revenue_to, 'Please select right range..!!!', ['expected_revenue_to']),
        (_check_to_date, ' Please select correct date, Select last date which is greater than from date...!!!', ['date_action_to', 'date_deadline_to']),
    ]

    @api.onchange('currency_ids')
    def _onchange_currency_ids(self):
        if not self.currency_ids:
            self.expected_revenue_from = False
            self.expected_revenue_to = False

    def get_oppo_lines(self):
        search_domain = [('type', '=', 'opportunity')]
        if self.user_id:
            search_domain.append(('user_id', '=', self.user_id.id))

        if self.date_action_from and self.date_action_to:
            search_domain.append(('activity_ids.date_deadline', '>=',
                                  self.date_action_from))
            search_domain.append(('activity_ids.date_deadline', '<=',
                                  self.date_action_to))

        if self.date_deadline_from and self.date_deadline_to:
            search_domain.append(('date_deadline', '>=',
                                  self.date_deadline_from))
            search_domain.append(('date_deadline', '<=',
                                  self.date_deadline_to))

        if self.expected_revenue_from or self.expected_revenue_to:
            if self.in_base_currency:
                search_domain.append(('planned_revenue', '>=',
                                      self.expected_revenue_from))
                search_domain.append(('planned_revenue', '<=',
                                      self.expected_revenue_to))
            else:
                search_domain.append(('planned_revenue_other_currency', '<=',
                                      self.expected_revenue_to))
                search_domain.append(('planned_revenue_other_currency', '>=',
                                      self.expected_revenue_from))

        if self.dealer_id:
            search_domain.append(('dealer_partner_ids', 'in',
                                  [self.dealer_id.id]))

        if self.influencer_id:
            search_domain.append(('influencer_ids', 'in',
                                  [self.influencer_id.id]))

        if self.currency_ids:
            currency_ids = []
            for curr_id in self.currency_ids:
                currency_ids.append(curr_id.id)
            search_domain.append(('other_currency_id', 'in', currency_ids))

        if self.stage_ids:
            search_domain.append(('stage_id', 'in', self.stage_ids.ids))

        oppo_recs = self.env['crm.lead'].search(search_domain)
        datas = []

        for oppo_rec in oppo_recs:
            datas.append({
                'salesperson': oppo_rec.user_id.name,
                'subject': oppo_rec.name,
                'other_currency_id': oppo_rec.other_currency_id.name,
                'planned_revenue_other_currency':
                    oppo_rec.planned_revenue_other_currency,
                'planned_revenue': oppo_rec.planned_revenue,
                'stage': oppo_rec.stage_id.name
            })
        return datas

    @api.multi
    def print_opportunity_analysis_report(self):
        self.ensure_one()
        return self.env.ref(
            'markant_crm.report_opportunity_markant').report_action(self)
