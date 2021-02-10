import datetime
import threading
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError
from odoo.tools.safe_eval import safe_eval


class InfluencerType(models.Model):
    _name = 'influencer.type'
    _description = 'Influencer Type'

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True)


class EventToDo(models.Model):
    _name = 'event.to.do'
    _description = 'Event To Do'

    check = fields.Boolean('Checkbox')
    description = fields.Char('Description')
    event_id = fields.Many2one('calendar.event', 'Event')


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    todo_ids = fields.One2many(
                    'event.to.do',
                    'event_id',
                    string='TODO')


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    @api.model
    def action_your_pipeline(self):
        action = self.env.ref('crm.crm_lead_opportunities_tree_view').read()[0]
        user_team_id = self.env.user.sale_team_id.id
        if not user_team_id:
            user_team_id = self.search([], limit=1).id
            action['help'] = _("""<p class='o_view_nocontent_smiling_face'>Add new opportunities</p><p>
                Looks like you are not a member of a Sales Team. You should add yourself
                as a member of one of the Sales Team.</p>""")
            if user_team_id:
                action['help'] += "<p>As you don't belong to any Sales Team, Odoo opens the first one by default.</p>"

        action_context = safe_eval(action['context'], {'uid': self.env.uid})
        if user_team_id:
            action_context['default_team_id'] = user_team_id

        tree_view_id = self.env.ref('crm.crm_case_tree_view_oppor').id
        form_view_id = self.env.ref('crm.crm_case_form_view_oppor').id
        kanb_view_id = self.env.ref('crm.crm_case_kanban_view_leads').id
        action['views'] = [
                [tree_view_id, 'tree'],
                [kanb_view_id, 'kanban'],
                [form_view_id, 'form'],
                [False, 'graph'],
                [False, 'calendar'],
                [False, 'pivot']
            ]
        action['context'] = action_context
        return action


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.multi
    def action_set_lost(self):
        res = super(CrmLead, self).action_set_lost()
        stage_id = self._stage_find(
            domain=[('probability', '=', 0), ('on_change', '=', True)])
        self.write({'stage_id': stage_id.id})
        return res

    @api.model
    def _get_default_currency(self):
        return self.env.user.company_id.currency_id

    def _get_user(self):
        for rec in self:
            show_original = False
            if self._context.get('active_model') == 'res.partner' and \
                    self.env.user.has_group('base.group_sale_manager'):
                show_original = True
            elif self._context.get('active_model') != 'res.partner' and \
                    (self.env.uid == SUPERUSER_ID or self.env.user.has_group('base.group_sale_salesman_all_leads') or
                        self.env.user.has_group('markant_crm.group_sale_opportunity')):
                show_original = True
            rec.show_original = show_original

    def _get_hide_dealer(self):
        for rec in self:
            hide_dealer = False
            if self._context.get('hide_dealer'):
                hide_dealer = True
            rec.hide_dealer = hide_dealer

    @api.multi
    def _compute_child_count(self):
        DealersOppInfo = self.env['dealers.opportunity.info']
        for lead in self:
            lead.child_count = DealersOppInfo.search_count(
                [('opportunity_id', '=', lead.id),
                 '|', ('active', '=', False), ('active', '=', True)])

    @api.depends('planned_revenue', 'commission')
    def get_commission(self):
        for rec in self:
            rec.commission_amount = (rec.planned_revenue *
                                     rec.commission) / 100

    contact_id = fields.Many2one('res.partner', string='Contact Name')
    contact_mobile = fields.Char(string='Contact Mobile')
    contact_email = fields.Char(string='Contact Email')
    contact_phone = fields.Char(string='Contact Phone')
    influencer_ids = fields.Many2many('res.partner',
                                      'crm_lead_influencer_rel', 'lead_id',
                                      'influencer_id', string='Influencers',
                                      domain=[('influencer', '=', True)])
    commission = fields.Float(string='Commission (%)')
    commission_amount = fields.Float(string='Commission Amount',
                                     compute='get_commission', store=True)
    ref_desc = fields.Char('Reference/Description')
    commission_currency_id = fields.Many2one('res.currency', string='Currency')
    dealer_oppor_info_ids = fields.One2many('dealers.opportunity.info',
                                            'opportunity_id',
                                            string='Dealers Opportunity Info')
    planned_revenue_other_currency = fields.Float(
        string='Expected Revenue other Currency')
    planned_revenue_backend = fields.Float(string='Planned Revenue Backend')
    other_currency_id = fields.Many2one('res.currency',
                                        string='Other Currency',
                                        default=_get_default_currency)
    dealer_partner_ids = fields.Many2many(
        'res.partner', string='Add Dealers',
        compute='_compute_dealer_partner_ids', store=True)
    portal_user = fields.Boolean(
                    compute='check_portal_user',
                    string='Portal User?')
    quote_create = fields.Boolean('Quote Created?')
    event_start_ids = fields.Many2many('calendar.event',
                                       'calendar_event_lead_start_rel',
                                       'lead_id', 'event_start_id',
                                       string='Event Start')
    event_end_ids = fields.Many2many('calendar.event',
                                     'calendar_event_lead_end_rel',
                                     'lead_id', 'event_end_id',
                                     string='Event End')
    event_next_action_ids = fields.Many2many(
        'calendar.event', 'calendar_event_lead_next_action_rel',
        'lead_id', 'event_id', string='Event Next Action Date')
    removed = fields.Boolean(string='Removed')
    lead_att_link = fields.Char(string='To Google Drive', size=1024)
    parent_id = fields.Many2one('crm.lead', string='Parent Pipeline')
    child_ids = fields.One2many('crm.lead', 'parent_id',
                                string='Child Piplelines')
    child_count = fields.Integer('# Childs', compute='_compute_child_count')
    preferred_dealer_id = fields.Many2one('res.partner',
                                          string='Preferred Dealer')
    dealer_company_id = fields.Many2one('res.partner',
                                        compute="_get_dealer_company",
                                        string='Dealer company', store=True)
    child_lead = fields.Boolean(string='Child Lead')
    phonecall_count = fields.Integer('Call/Visit Report',
                                     compute='_compute_phonecall_count')
    contact_name = fields.Char(string='Contact Name Info')
    partner_pipeline_ids = fields.One2many('partner.crm.lead', 'oppo_id',
                                           string='Partner Parent Pipeline')
    dealer_partner_name = fields.Char(string='Dealers',
                                      compute='_compute_dealer_partner_ids',
                                      store=True)
    next_action_date = fields.Date(string="Next Action Date")
    title_action_date = fields.Char(string='Title Action Date')
    # nett_revenue = fields.Float(compute='_get_nett_revenue',
    #                             string='Nett Revenue', store=True)
    expected_revenue = fields.Monetary(string='Nett Revenue')
    name = fields.Char(string='Opportunity', required=True,
                       index=True, default='/')
    main_description = fields.Char(string='Description')
    partner_company_id = fields.Many2one('res.partner',
                                         string='End User Company',
                                         compute='_get_partner_company',
                                         store=True)

    @api.depends('partner_id')
    def _get_partner_company(self):
        for crm in self:
            if crm.partner_id:
                crm.partner_company_id = \
                    crm.partner_id.parent_id.id or crm.partner_id.id

    # @api.depends('planned_revenue_other_currency', 'probability')
    # def _get_nett_revenue(self):
    #     for crm in self:
    #         if crm.planned_revenue and crm.probability:
    #             crm.nett_revenue = \
    #                 crm.planned_revenue * (crm.probability / 100)

    @api.multi
    @api.depends('preferred_dealer_id')
    def _get_dealer_company(self):
        for crm in self:
            if crm.preferred_dealer_id:
                    crm.dealer_company_id = \
                        crm.preferred_dealer_id.parent_id.id or \
                        crm.preferred_dealer_id.id

    @api.multi
    def _compute_phonecall_count(self):
        Phonecall = self.env['voip.phonecall']
        for rec in self:
            rec.phonecall_count = Phonecall.search_count(
                [('opportunity_id', '=', rec.id)])

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        if self.env.context.get('lead_partner_id') and \
                self.env.context['lead_partner_id']:
            domain = []
            domain.append(('partner_id', '=',
                           self.env.context['lead_partner_id']))
            return self.search(args + domain, limit=limit).name_get()
        return super(CrmLead, self).name_search(name, args=args,
                                                operator=operator,
                                                limit=limit)

    @api.onchange('contact_id')
    def onchange_contact_id(self):
        for rec in self:
            rec.contact_mobile = rec.contact_id.mobile
            rec.contact_email = rec.contact_id.email
            rec.contact_phone = rec.contact_id.phone
            rec.function = rec.contact_id.job_position_id.name or \
                           rec.contact_id.function

    @api.onchange('preferred_dealer_id')
    def onchange_preferred_dealer_id(self):
        DealersOppInfo = self.env['dealers.opportunity.info']
        if self.env.context.get('lead_id'):
            dealer_line = DealersOppInfo.search([
                ('dealer_id', '=', self.preferred_dealer_id.id),
                ('opportunity_id', '=', self.env.context['lead_id'])
            ], limit=1)
            if dealer_line:
                self.planned_revenue_other_currency = \
                    dealer_line.planned_revenue_other_currency
                self.other_currency_id = dealer_line.other_currency_id
                self.probability = dealer_line.probability
                self.commission = dealer_line.commission_per
                self.date_deadline = dealer_line.date_deadline
                self.email_from = dealer_line.email_from
                self.phone = dealer_line.phone
                self.user_id = dealer_line.user_id

    @api.constrains('commission', 'planned_revenue_other_currency')
    def _check_commission(self):
        for record in self:
            if record.commission > record.planned_revenue_other_currency:
                raise Warning(
                    _('Commission value must be less then expected revenue'))

    def check_portal_user(self):
        if self.env.user.has_group('base.group_portal'):
            for oppor in self:
                oppor.portal_user = True

    @api.multi
    def create_event(self, _field_name, date_deadline, _prefix=False, user_id=False, event_description=False):
        self.ensure_one()
        if not _prefix:
            _prefix = _('Action') \
                if _field_name == 'event_start_ids' else 'Close'
        partner_ids = []
        if self.user_id:
            partner_ids.append(self.user_id.sudo(SUPERUSER_ID).partner_id.id)
        if user_id:
            pid = self.env['res.users'].browse(user_id).partner_id.id
            partner_ids.append(pid)
        event_start = self.env['calendar.event'].with_context(
            not_dealer=True, from_ui=True).create({
                'name': '%s: %s' % (_prefix, self.name),
                'start': date_deadline,
                'start_date': date_deadline,
                'stop': date_deadline,
                'stop_date': date_deadline,
                'allday': True,
                'description':event_description,
                'partner_ids': [(6, 0, partner_ids)]
            })
        return self.write({_field_name: [(6, 0, event_start.ids)]})

    @api.model
    def create(self, vals):
        if vals.get('planned_revenue_backend', 0.0):
            vals.update({'planned_revenue': vals['planned_revenue_backend']})

        # update color
        today = fields.Date.today()
        if vals.get('next_action_date') and \
                fields.Date.from_string(vals.get('next_action_date')) < today:
            vals['color'] = 1

        record_name = vals.get('main_description')
        if vals.get('partner_id'):
            vals['name'] = self.env['res.partner'].browse(
                vals['partner_id']).name_get()[0][1] + ' - ' + record_name
        else:
            vals['name'] = record_name

        record = super(CrmLead, self).create(vals)
        if record.type == 'opportunity' and record.partner_id:
            self.env['partner.crm.lead'].create({
                'oppo_id': record.id,
                'partner_id': record.partner_id.id,
                'date_deadline': record.date_deadline
            })
        if vals.get('date_deadline'):
            record.create_event('event_end_ids', vals['date_deadline'])
        if vals.get('next_action_date'):
            record.create_event('event_next_action_ids',
                                vals['next_action_date'], 'Next Action Date ')
        return record

    @api.model
    def generate_name(self):
        """
        generate name = company name, contact - street, city - description
        :return:
        """
        record_name = self.main_description
        if self.partner_id:
            record_name = self.partner_id.name_get()[0][1] + \
                ' - ' + record_name
        self.with_context(gen_name=True).name = record_name

    @api.multi
    def write(self, vals):
        DealersOpportunityInfo = self.env['dealers.opportunity.info']
        ResUsers = self.env['res.users']
        if 'planned_revenue_backend' in vals:
            vals.update({'planned_revenue': vals['planned_revenue_backend']})

        res = super(CrmLead, self).write(vals)

        # HITESH : when lost we set date closed and when other stage need to set false. for won super will handle
        if self.env.context.get('no_need_check_probabilty') is None:
            if vals.get('probability') is not None:
                if vals.get('probability', 999999999) <= 0.0:
                    self.with_context(no_need_check_probabilty=True).write({'date_closed': fields.Datetime.now()})
                elif vals.get('probability', 0) >= 100:
                    # bcz this condition is for won and it get applied in the super call, we 
                    # need to call this bcz if not won not lost then date close should be false
                    pass
                else:
                    self.with_context(no_need_check_probabilty=True).write({'date_closed': False})

        # update color
        if vals.get('next_action_date'):
            self.update_color()

        PartnerLead = self.env['partner.crm.lead']
        # checking for other value
        p_lead = False
        for lead in self:
            p_lead = PartnerLead.search([('oppo_id', '=', lead.id)])
            if not p_lead:
                if lead.type == 'opportunity' and \
                        lead.partner_id and lead.stage_id:
                    p_lead = PartnerLead.create({
                        'oppo_id': lead.id,
                        'partner_id': lead.partner_id.id,
                        'date_deadline': lead.date_deadline,
                        'stage_id': lead.stage_id.id
                    })

            if p_lead:
                p_lead_vals = {}
                if vals.get('partner_id'):
                    p_lead_vals.update({'partner_id': lead.partner_id.id})
                if vals.get('date_deadline'):
                    p_lead_vals.update({'date_deadline': lead.date_deadline})
                if vals.get('stage_id'):
                    p_lead_vals.update({'stage_id': lead.stage_id.id})

                if p_lead_vals.keys():
                    p_lead.write(p_lead_vals)

            if not self.env.context.get('from_child'):
                preferred_dealer_line = DealersOpportunityInfo.search([
                    ('dealer_id', '=', lead.preferred_dealer_id.id),
                    ('opportunity_id', '=', lead.id)
                ])
                dealer_lines = DealersOpportunityInfo.search([
                    ('opportunity_id', '=', lead.id)
                ])

                # update parent lead values for preferred child
                pre_vals = {
                    'commission_per': lead.commission,
                    'commission_currency_id': lead.commission_currency_id.id,
                    'probability': lead.probability,
                    'planned_revenue_other_currency':
                        lead.planned_revenue_other_currency,
                    'other_currency_id': lead.other_currency_id.id,
                    'planned_revenue': lead.planned_revenue_backend,
                    'user_id': lead.user_id.id,
                    'email_from': lead.email_from,
                    'stage_id': lead.stage_id.id,
                    'phone': lead.phone,
                }
                # only update probability, active for preferred child
                # when opp stage = lost (0%)
                if lead.probability == 0:
                    pre_vals['active'] = lead.active,
                    pre_vals['probability'] = lead.probability
                preferred_dealer_line.with_context(
                    from_parent=True).write(pre_vals)

                # update parent lead values for all child
                all_child_vals = {
                    'name': lead.name,
                    'user_id': lead.user_id.id,
                }
                # only update probability, active for all child
                # when opp stage = lost (0%)
                if lead.probability == 0:
                    all_child_vals['active'] = lead.active,
                    all_child_vals['probability'] = lead.probability
                    all_child_vals['stage_id'] = lead.stage_id.id
                dealer_lines.with_context(from_parent=True).write(
                    all_child_vals)

            if vals.get('user_id'):
                partner_ids = []
                end_partner_ids = []
                end_user = ResUsers.browse(vals['user_id'])
                partner_ids.append(end_user.partner_id.id)
                end_partner_ids.append(end_user.partner_id.id)
                end_partner_ids += lead.dealer_oppor_info_ids.mapped(
                    'dealer_id.id')

                lead.event_start_ids.write({
                    'partner_ids': [(6, 0, partner_ids)]
                })
                lead.event_end_ids.write({
                    'partner_ids': [(6, 0, end_partner_ids)]
                })
            if vals.get('date_deadline'):
                lead.dealer_oppor_info_ids.write({
                    'date_deadline': lead.date_deadline
                })
                if lead.event_end_ids:
                    lead.event_end_ids.write({
                        'start': lead.date_deadline,
                        'start_date': lead.date_deadline,
                        'stop': lead.date_deadline,
                        'stop_date': lead.date_deadline,
                    })
                else:
                    lead.create_event('event_end_ids', lead.date_deadline)
            # if lead have event for next action date > update data
            if vals.get('next_action_date') or vals.get('user_id'):
                if lead.event_end_ids:
                    lead.event_next_action_ids.write({
                        'start': lead.next_action_date,
                        'start_date': lead.next_action_date,
                        'stop': lead.next_action_date,
                        'stop_date': lead.next_action_date,
                        'partner_ids':
                            [(6, 0, [lead.user_id.partner_id.id] or False)]
                    })
                    # if lead not have event for next action date > create new
                else:
                    lead.create_event('event_next_action_ids',
                                      vals['next_action_date'],
                                      'Next Action Date ')
        if self._context.get('gen_name'):
            return res
        for record in self:
            if record.partner_id:
                record.generate_name()
            return res

    @api.multi
    def unlink(self):
        for rec in self:
            rec.event_start_ids.unlink()
            rec.event_end_ids.unlink()
            rec.dealer_oppor_info_ids.unlink()
        return super(CrmLead, self).unlink()

    @api.depends('dealer_oppor_info_ids')
    def _compute_dealer_partner_ids(self):
        for opp in self:
            partner_ids = opp.dealer_oppor_info_ids.mapped('dealer_id.id')
            opp.dealer_partner_ids = partner_ids

    @api.onchange('planned_revenue_other_currency')
    def onchange_planned_revenue_other_currency(self):
        if self.env.user.company_id.currency_id and self.other_currency_id:
            planned_revenue = self.other_currency_id. \
                compute(self.planned_revenue_other_currency,
                        self.env.user.company_id.currency_id)
            self.planned_revenue = planned_revenue
            self.planned_revenue_backend = planned_revenue
        else:
            self.planned_revenue = self.planned_revenue_other_currency
            self.planned_revenue_backend = self.planned_revenue_other_currency

    @api.onchange('other_currency_id')
    def onchange_other_currency(self):
        if self.env.user.company_id.currency_id and self.other_currency_id:
            planned_revenue = self.other_currency_id. \
                compute(self.planned_revenue_other_currency,
                        self.env.user.company_id.currency_id)
            self.planned_revenue = planned_revenue
            self.planned_revenue_backend = planned_revenue
            self.commission_currency_id = self.other_currency_id

    @api.multi
    def on_change_partner_id(self, partner_id):
        vals = super(CrmLead, self).on_change_partner_id(partner_id)
        user_id = False
        contact_id = self.contact_id.id
        if self.partner_id.id != partner_id:
            contact_id = False
        if partner_id:
            user_id = self.env['res.partner'].browse(partner_id).user_id.id
        vals['value'].update({
            'contact_id': contact_id,
            'user_id': user_id
        })
        return vals

    @api.multi
    def case_mark_quotation(self):
        stages_leads = {}
        for lead in self:
            stage_id = self.stage_find([lead], lead.section_id.id or False,
                                       [('probability', '=', 100.0),
                                        ('quotation_stage', '=', True),
                                        ('on_change', '=', True)])
            if stage_id:
                if stages_leads.get(stage_id):
                    stages_leads[stage_id].append(lead.id)
                else:
                    stages_leads[stage_id] = [lead.id]
            else:
                raise ValidationError(
                    _('To relieve your sales pipe and group all '
                      'Quotation opportunities, configure one of your sales '
                      'stage as follow:\n'
                      'probability = 100 % and select "Change Probability '
                      'Automatically".\n'
                      'Create a specific stage or edit an existing one by '
                      'editing columns of your opportunity pipe.'))
        for stage_id, lead_ids in stages_leads.items():
            leads = self.browse(lead_ids)
            leads.write({'stage_id': stage_id})
        return True

    @api.multi
    def action_child_pipeline(self):
        self.ensure_one()
        action = self.env.ref(
            'markant_crm.action_your_pipeline_child').read()[0]
        action['context'] = {
            'default_opportunity_id': self.id,
            'default_name': self.name,
            'default_partner_id': self.partner_id.id,
            'default_probabilty': self.probability,
            'default_other_currency_id': self.other_currency_id.id,
            'default_commission_per': self.commission,
            'default_planned_revenue_other_currency':
                self.planned_revenue_other_currency,
            'default_date_deadline': self.date_deadline,
            'default_user_id': self.user_id.id,
            'default_next_action_date': self.next_action_date,
            'default_title_action_date': self.title_action_date,
        }
        action['domain'] = [('opportunity_id', '=', self.id),
                            '|', ('active', '=', False), ('active', '=', True)]
        return action

    @api.multi
    def action_set_won(self):
        res = super(CrmLead, self).action_set_won()
        threaded_send_mail = threading.Thread(
            target=self.send_mail_set_won, args=())
        threaded_send_mail.daemon = True
        threaded_send_mail.start()
        return res

    def send_mail_set_won(self):
        with api.Environment.manage():
            new_env = api.Environment(
                self.pool.cursor(), self.env.uid, self.env.context)
            template = new_env.ref('markant_crm.email_template_crm_lead_won')
            # use self._origin.id == self.id when onchange stage don't have id
            # when click mark won then user self.id
            try:
                res_id = self._origin.id
            except:
                res_id = self.id
            template.send_mail(res_id=res_id, force_send=True)

    @api.onchange('stage_id')
    def onchange_stage(self):
        """
        when onchange stage, check if stage have probability is 100% -> send email
        :return:
        """
        if self.stage_id and self.stage_id.probability == 100:
            # check record is new not save
            if not self._origin.id:
                raise UserError(_("You can not change this stage without "
                                  "saving data!"))
            threaded_send_mail = threading.Thread(
                target=self.send_mail_set_won, args=())
            threaded_send_mail.daemon = True
            threaded_send_mail.start()

    @api.model
    def schedule_set_color_crm_lead(self):
        today = fields.datetime.today().strftime('%Y-%m-%d')

        list_opp = self.search([('type', '=', 'opportunity'),
                                ('active', '=', True),
                                ('next_action_date', '=', today)])
        list_opp.update_color()

    @api.multi
    def update_color(self):
        today = fields.date.today()
        for opp in self:
            if opp.next_action_date and opp.next_action_date < today:
                opp.color = 1
            else:
                opp.color = 0


class Activity(models.Model):
    """
    On Schedule activity
        - Create event in Main Calendar
    """
    _inherit = "mail.activity"

    def _default_user_id(self):
        ctx = self.env.context
        uid = self.env.uid
        if ctx.get('default_res_model') == 'dealers.opportunity.info' \
                and ctx.get('default_res_id'):
            record = self.env['dealers.opportunity.info'].browse(
                ctx['default_res_id'])
            uid = record.user_id.id
        return uid

    user_id = fields.Many2one(default=_default_user_id)

    @api.model
    def create(self, vals):
        """
            Special Hack: For None-linking calendar event created by internal
            -  eg. Action Events
        """
        EXCEPTION_MODEL = ['crm.lead', 'dealers.opportunity.info']
        if vals.get('res_model_id') and vals.get('calendar_event_id'):
            model = self.env['ir.model'].sudo().browse(
                vals.get("res_model_id")).model
            if model in EXCEPTION_MODEL:
                return self.env['mail.activity']

        if vals.get('res_model_id') and vals.get('date_deadline') \
                and vals.get('res_id'):
            res_model = self.env['ir.model'].browse(vals['res_model_id'])
            if vals.get('summary'):
                vals['summary'] = '%s: %s' % (_("Action"), vals['summary'])
            if res_model.model == 'crm.lead':
                lead = self.env['crm.lead'].browse(vals['res_id'])
                lead.with_context(vp_event_write=True).create_event(
                    'event_start_ids', vals['date_deadline'], False,
                    vals.get('user_id'), vals['summary'])
            elif res_model.model == 'dealers.opportunity.info':
                dealer = self.env['dealers.opportunity.info'].browse(
                    vals['res_id'])
                dealer.with_context(vp_event_write=True)._create_event_child(
                    vals['date_deadline'], vals.get('user_id'))
        return super(Activity, self).create(vals)

    @api.multi
    def write(self, vals):
        ResUsers = self.env['res.users']
        res = super(Activity, self).write(vals)

        if self.env.context.get('vp_event_write') or \
                (not vals.get('date_deadline') and not vals.get('user_id')):
            return res

        for record in self.filtered(lambda r: r.res_model in (
                'crm.lead', 'dealers.opportunity.info')):
            event_vals = {}
            pipeline = self.env[record.res_model].browse(record.res_id)

            if vals.get('date_deadline'):
                date_deadline = vals['date_deadline']
                if isinstance(date_deadline, type(datetime.date.today())):
                    date_deadline = fields.Date.to_string(
                        vals['date_deadline'])
                event_vals.update({
                    'start': date_deadline,
                    'start_date': date_deadline,
                    'stop': date_deadline,
                    'stop_date': date_deadline,
                })
            if vals.get('user_id'):

                end_user = ResUsers.sudo(SUPERUSER_ID).browse(vals['user_id'])
                partner_ids = [end_user.partner_id.id,
                               pipeline.user_id.partner_id.id]
                event_vals.update({'partner_ids': [(6, 0, partner_ids)]})

            if record.res_model == 'crm.lead':
                pipeline.event_start_ids.with_context(
                    vp_event_write=True).write(event_vals)
            elif record.res_model == 'dealers.opportunity.info':
                pipeline.event_ids.with_context(
                    vp_event_write=True).write(event_vals)
        return res


class DealersOpportunityInfo(models.Model):
    _name = 'dealers.opportunity.info'
    _description = 'Dealers opportunity information'
    _order = 'create_date'
    _inherit = ['mail.thread', 'mail.activity.mixin',
                'utm.mixin', 'format.address.mixin']

    @api.depends('planned_revenue', 'commission_per')
    def get_commission(self):
        for rec in self:
            rec.commission = (rec.planned_revenue * rec.commission_per) / 100

    @api.model
    def _get_default_currency(self):
        return self.env.user.company_id.currency_id

    @api.multi
    def _compute_parent_count(self):
        CrmLead = self.env['crm.lead']
        for dealer in self:
            dealer.parent_count = CrmLead.search_count(
                [('id', '=', dealer.opportunity_id.id)])

    def _default_stage_id(self):
        team = self.env['crm.team'].sudo()._get_default_team_id(
            user_id=self.env.uid)
        return self._stage_find(team_id=team.id,
                                domain=[('fold', '=', False)]).id

    name = fields.Char(string='Opportunity', required=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Customer',
                                 track_visibility='onchange', index=True)
    probability = fields.Float(string='Probability', group_operator="avg",
                               default=10)
    planned_revenue = fields.Float(string='Expected Revenue',
                                   track_visibility='always')
    planned_revenue_backend = fields.Float(string='Planned Revenue Backend')
    user_id = fields.Many2one('res.users', string='Salesperson',
                              index=True, default=lambda self: self.env.user)
    referred = fields.Char(string='Referred By')
    email_from = fields.Char(string='Email',
                             help="Email address of the contact", index=True)
    website = fields.Char(string='Website', index=True,
                          help="Website of the contact")
    team_id = fields.Many2one(
        'crm.team', string='Sales Channel',
        default=lambda self: self.env['crm.team'].sudo()._get_default_team_id(
            user_id=self.env.uid),
        index=True)
    description = fields.Text(string='Notes')
    date_closed = fields.Datetime(string='Closed Date', readonly=True,
                                  copy=False)
    create_date = fields.Datetime(string='Create Date', readonly=True)
    write_date = fields.Datetime(string='Update Date', readonly=True)
    date_deadline = fields.Date(string='Expected Closing',
                                help="Estimate of the date on which the "
                                     "opportunity will be won.")
    company_currency = fields.Many2one(string='Currency',
                                       related='company_id.currency_id',
                                       readonly=True, relation="res.currency")
    phone = fields.Char(string='Phone')
    company_id = fields.Many2one(
        'res.company', string='Company', index=True,
        default=lambda self: self.env.user.company_id.id)

    # custom fields
    other_currency_id = fields.Many2one('res.currency',
                                        string='Other Currency',
                                        default=_get_default_currency)
    commission = fields.Float(string='Commission', compute='get_commission',
                              store=True)
    commission_per = fields.Float(string='Commission %')
    planned_revenue_other_currency = fields.Float(
        string='Expected Revenue other Currency')

    total_revenue = fields.Float(string='Total Revenue')
    date_shipping = fields.Datetime(string='Shipping Date', copy=False)
    account_manager_id = fields.Many2one('res.users', string='Salesperson')
    dealer_id = fields.Many2one('res.partner', string='Dealer',
                                domain=[('customer', '=', True)])
    opportunity_id = fields.Many2one('crm.lead', string='Parent Pipeline',
                                     ondelete='cascade')
    commission_currency_id = fields.Many2one('res.currency',
                                             string='Currency')
    event_ids = fields.Many2many('calendar.event', 'calendar_event_dealer_rel',
                                 'dealer_id', 'event_id',
                                 string='Event')
    event_dealer_next_action_ids = fields.Many2many(
        'calendar.event', 'calendar_event_dealer_next_action_rel',
        'dealer_id', 'event_id',
        string='Event Next Action Date')
    parent_count = fields.Integer('# Parent', compute='_compute_parent_count')
    stage_id = fields.Many2one('crm.stage', string='Stage',
                               track_visibility='onchange', index=True,
                               group_expand='_read_group_stage_ids',
                               default=lambda self: self._default_stage_id())
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(string='Active', default=True)
    partner_pipeline_ids = fields.One2many('partner.crm.lead', 'child_oppo_id',
                                           string='Partner Child Pipeline')
    next_action_date = fields.Date(string="Next Action Date")
    title_action_date = fields.Char(string='Title Action Date')

    @api.multi
    def action_set_active(self):
        return self.write({'active': True})

    @api.multi
    def action_set_unactive(self):
        return self.write({'active': False})

    @api.one
    @api.constrains('dealer_id')
    def check_same_dealer(self):
        same_children_count = self.search_count([
            ('opportunity_id', '=', self.opportunity_id.id),
            ('dealer_id', '=', self.dealer_id.id),
            ('id', '!=', self.id)
        ])
        if same_children_count:
            raise ValidationError(_("You cannot assign same dealer in "
                                    "multiple child pipeline of "
                                    "same opportunity."))

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        # retrieve team_id from the context and write the domain
        # - ('id', 'in', stages.ids): add columns that should be present
        # - OR ('fold', '=', False): add default columns that are not folded
        # - OR ('team_ids', '=', team_id), ('fold', '=', False) if team_id: add team columns that are not folded
        team_id = self._context.get('default_team_id')
        if team_id:
            search_domain = ['|', ('id', 'in', stages.ids), '|',
                             ('team_id', '=', False),
                             ('team_id', '=', team_id)]
        else:
            search_domain = ['|', ('id', 'in', stages.ids),
                             ('team_id', '=', False)]

        # perform search
        stage_ids = stages._search(search_domain, order=order,
                                   access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    def _stage_find(self, team_id=False, domain=None, order='sequence'):
        """ Determine the stage of the current lead with its teams, the given
        domain and the given team_id
            :param team_id
            :param domain : base search domain for stage
            :returns crm.stage recordset
        """
        # collect all team_ids by adding given one, and the ones related to
        # the current leads
        team_ids = set()
        if team_id:
            team_ids.add(team_id)
        for lead in self:
            if lead.team_id:
                team_ids.add(lead.team_id.id)
        # generate the domain
        if team_ids:
            search_domain = ['|', ('team_id', '=', False),
                             ('team_id', 'in', list(team_ids))]
        else:
            search_domain = [('team_id', '=', False)]
        # AND with the domain in parameter
        if domain:
            search_domain += list(domain)
        # perform search, return the first found
        return self.env['crm.stage'].search(search_domain, order=order, limit=1)

    @api.onchange('opportunity_id')
    def _onchange_opportunity_id(self):
        if self.opportunity_id:
            self.name = self.opportunity_id.name
            self.planned_revenue_other_currency = \
                self.opportunity_id.planned_revenue_other_currency
            self.other_currency_id = self.opportunity_id.other_currency_id
            self.probability = self.opportunity_id.probability
            self.commission_per = self.opportunity_id.commission
            self.date_deadline = self.opportunity_id.date_deadline
            self.email_from = self.opportunity_id.email_from
            self.phone = self.opportunity_id.phone
            self.user_id = self.opportunity_id.user_id

    @api.onchange('planned_revenue_other_currency')
    def onchange_planned_revenue_other_currency(self):
        if self.env.user.company_id.currency_id and self.other_currency_id:
            planned_revenue = self.other_currency_id. \
                compute(self.planned_revenue_other_currency,
                        self.env.user.company_id.currency_id)
            self.planned_revenue = planned_revenue
            self.planned_revenue_backend = planned_revenue
        else:
            self.planned_revenue = self.planned_revenue_other_currency
            self.planned_revenue_backend = self.planned_revenue_other_currency

    @api.onchange('other_currency_id')
    def onchange_other_currency(self):
        if self.env.user.company_id.currency_id and self.other_currency_id:
            planned_revenue = self.other_currency_id. \
                compute(self.planned_revenue_other_currency,
                        self.env.user.company_id.currency_id)
            self.planned_revenue = planned_revenue
            self.planned_revenue_backend = planned_revenue
            self.commission_currency_id = self.other_currency_id

    @api.multi
    def action_parent_pipeline(self):
        self.ensure_one()
        action = self.env.ref('crm.crm_lead_opportunities_tree_view').read()[0]
        action['domain'] = [('id', '=', self.opportunity_id.id)]
        return action

    @api.multi
    def write(self, vals):
        if 'planned_revenue_backend' in vals:
            vals.update({'planned_revenue': vals['planned_revenue_backend']})
        # write to dealer of opportunity

        p_lead = PartnerLead = self.env['partner.crm.lead']
        for line in self:
            if not self.env.context.get('from_parent'):
                parent_vals = {}
                if line.dealer_id and line.dealer_id == \
                        line.opportunity_id.preferred_dealer_id:
                    if vals.get('planned_revenue_other_currency'):
                        parent_vals['planned_revenue_other_currency'] = \
                            vals['planned_revenue_other_currency']
                    if vals.get('planned_revenue_backend'):
                        parent_vals['planned_revenue'] = \
                            vals['planned_revenue_backend']
                    if vals.get('other_currency_id'):
                        parent_vals['other_currency_id'] = \
                            vals['other_currency_id']
                    if vals.get('probability'):
                        parent_vals['probability'] = vals['probability']
                    if vals.get('commission_per'):
                        parent_vals['commission'] = vals['commission_per']
                    # Child pipeline does not have their own Expected closing
                    if vals.get('email_from'):
                        parent_vals['email_from'] = vals['email_from']
                    if vals.get('phone'):
                        parent_vals['phone'] = vals['phone']
                    if vals.get('user_id'):
                        parent_vals['user_id'] = vals['user_id']
                    if vals.get('stage_id'):
                        parent_vals['stage_id'] = vals['stage_id']

                    line.opportunity_id.with_context(
                        from_child=True).write(parent_vals)

            p_lead_vals = {}
            if vals.get('dealer_id'):
                end_partner_ids = []
                if line.dealer_id == line.opportunity_id.preferred_dealer_id:
                    raise ValidationError(_('You can not update dealer which '
                                            'used in preffered dealer!'))
                partner_ids = [
                    vals['dealer_id'],
                    line.opportunity_id.user_id.partner_id.id
                ]
                line.event_ids.write({
                    'partner_ids': [(6, 0, partner_ids)]
                })
                end_partner_ids += \
                    line.opportunity_id.dealer_oppor_info_ids.filtered(
                        lambda l: l.id != line.id).mapped('dealer_id.id')
                end_partner_ids.append(
                    line.opportunity_id.user_id.partner_id.id)
                end_partner_ids.append(vals['dealer_id'])
                line.opportunity_id.event_end_ids.write({
                    'partner_ids': [(6, 0, end_partner_ids)]
                })
                # Common Pipeline in Partner Form
                p_lead_vals.update({'partner_id': vals['dealer_id']})

            if vals.get('date_deadline'):
                p_lead_vals.update({'date_deadline': vals['date_deadline']})
            if vals.get('stage_id'):
                p_lead_vals.update({'stage_id': vals['stage_id']})

            if p_lead_vals.keys():
                p_lead = PartnerLead.search([('child_oppo_id', '=', line.id)])
                p_lead.write(p_lead_vals)

            if vals.get('next_action_date') or vals.get('user_id') or \
                    vals.get('dealer_id'):
                if line.event_dealer_next_action_ids:
                    partner_ids = []
                    if line.user_id:
                        partner_ids.append(line.user_id.partner_id.id)
                    if line.dealer_id:
                        partner_ids.append(line.dealer_id.id)
                    line.event_dealer_next_action_ids.write({
                        'start': line.next_action_date,
                        'start_date': line.next_action_date,
                        'stop': line.next_action_date,
                        'stop_date': line.next_action_date,
                        'partner_ids': [(6, 0, partner_ids or False)]
                    })
                else:
                    if vals.get('next_action_date'):
                        line._create_event_child(vals.get('next_action_date'))
        return super(DealersOpportunityInfo, self).write(vals)

    @api.one
    def _create_event_child(self, date_deadline, user_id=False):
        partner_ids = []
        if self.user_id:
            partner_ids.append(self.user_id.sudo(SUPERUSER_ID).partner_id.id)
        if user_id:
            pid = self.env['res.users'].browse(user_id).partner_id.id
            partner_ids.append(pid)

        partner_ids.append(self.dealer_id.id)
        event = self.env['calendar.event'].with_context(
            not_dealer=True).create({
                'name': '%s: %s' % ('Action', self.name),
                'start': date_deadline,
                'start_date': date_deadline,
                'stop': date_deadline,
                'stop_date': date_deadline,
                'allday': True,
                'partner_ids': [(6, 0, partner_ids)]
            })
        return self.write({'event_ids': [(6, 0, event.ids)]})

    @api.model
    def create(self, vals):
        CrmLead = self.env['crm.lead']
        if vals.get('planned_revenue_backend', 0.0):
            vals.update({'planned_revenue': vals['planned_revenue_backend']})
        record = super(DealersOpportunityInfo, self).create(vals)
        self.env['partner.crm.lead'].create({
            'child_oppo_id': record.id,
            'opportunity_id': False,
            'partner_id': record.dealer_id.id,
            'date_deadline': record.date_deadline,
        })
        if 'opportunity_id' in vals:
            lead = CrmLead.browse(vals['opportunity_id'])
            exist = self.search([('opportunity_id', '=', lead.id),
                                 ('id', '!=', record.id)], limit=1)
            # set preferred dealer if only have 1 dealer
            if not exist and not self.env.context.get('from_popup', False):
                lead.preferred_dealer_id = record.dealer_id.id
            lead.event_end_ids.write({'partner_ids': [(4, vals['dealer_id'])]})
        if vals.get('next_action_date'):
            record._create_event_child(vals.get('next_action_date'))
        return record

    @api.multi
    def unlink(self):
        lines = self.filtered(
            lambda rec: rec.opportunity_id.preferred_dealer_id.id ==
            rec.dealer_id.id)
        if lines:
            raise ValidationError(
                _('You can not delete record which link to Parent Pipeline!'))
        for rec in self:
            opportunity = rec.opportunity_id
            self._remove_dealer_from_events(opportunity.event_end_ids,
                                            rec.dealer_id.id)
            self._remove_dealer_from_events(opportunity.event_start_ids,
                                            rec.dealer_id.id)

        self.mapped('event_ids').unlink()
        return super(DealersOpportunityInfo, self).unlink()

    @api.model
    def _remove_dealer_from_events(self, events, dealer_id):
        for event in events.filtered(lambda ev: dealer_id in
                                     ev.partner_ids.ids):
            pids = event.partner_ids.ids
            pids.remove(dealer_id)
            event.write({'partner_ids': [(6, 0, pids)]})


class crm_case_stage(models.Model):
    _inherit = 'crm.stage'

    quotation_stage = fields.Boolean('Quotation Stage?')

    @api.constrains('quotation_stage')
    def _check_quotation_stage(self):
        for record in self:
            if record.quotation_stage:
                stages = self.search([
                    ('quotation_stage', '=', True),
                    ('id', '!=', self.id)]
                )
                if stages:
                    raise ValidationError(_('You cannot have create more than '
                                            'one with quotation stage'))
