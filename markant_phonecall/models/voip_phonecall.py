import time

from odoo import api, fields, models, _


class VoipPhonecall(models.Model):
    _name = 'voip.phonecall'
    _inherit = ['mail.thread', 'voip.phonecall', 'mail.activity.mixin']

    @api.model
    def _get_default_state(self):
        if self.env.context.get('default_markant_phonecall'):
            return 'done'
        else:
            return 'open'

    name = fields.Char('Call Name', required=True, default='New')
    markant_phonecall = fields.Boolean(string='Markant Phonecall')
    state = fields.Selection([
        ('pending', 'Not Held'),
        ('cancel', 'Cancelled'),
        ('open', 'To Do'),
        ('done', 'Held'),
    ], string='Status', default=_get_default_state,
        help='The status is set to To Do, when a call is created.\n'
             'When the call is over, the status is set to Held.\n'
             'If the call is not applicable anymore, '
             'the status can be set to Cancelled.')
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')],
                                string='Priority', default='0')
    markant_phonecall_cate_id = fields.Many2one(
        'markant.voip.phonecall.category', string='Category', required=True)
    partner_ids = fields.Many2many(
        'res.partner', 'voip_phonecall_partner_rel',
        'partner_id', 'phonecall_id',
        domain=[('is_company', '=', True)],
        string='Companies', required=True)
    partner_contact_ids = fields.Many2many(
        'res.partner', 'voip_phonecall_partner_contact_rel',
        'partner_id', 'phonecall_id',
        domain=[('is_company', '=', False)],
        string='Contacts', required=True)
    opportunity_id = fields.Many2one('crm.lead', string='Lead/Opportunity')
    description = fields.Char(string='Description')

    next_action_date = fields.Date(string="Next Action Date")
    next_action_summary = fields.Char(string='Next Action Summary')
    call_date = fields.Datetime('Call Date',
                                default=lambda self: fields.Datetime.now())
    partner_group_by = fields.Many2one(
        'res.partner', string='Companies', compute='_get_partner_group_by',
        store=True)
    partner_contact_group_by = fields.Many2one(
        'res.partner', string='Contacts',
        compute='_get_partner_contact_group_by', store=True)

    @api.depends('partner_ids')
    def _get_partner_group_by(self):
        for record in self:
            if record.partner_ids and record.partner_ids[0]:
                record.partner_group_by = record.partner_ids[0].id

    @api.depends('partner_contact_ids')
    def _get_partner_contact_group_by(self):
        for record in self:
            if record.partner_contact_ids and record.partner_contact_ids[0]:
                record.partner_contact_group_by = \
                    record.partner_contact_ids[0].id

    # @api.onchange('partner_ids')
    # def onchange_partner_ids(self):
    #     res = {}
    #     # if self.partner_ids:
    #     #     self.mobile = self.partner_ids[0].mobile
    #     #     self.phone = self.partner_ids[0].phone
    #     res['domain'] = {'partner_contact_ids': [
    #         ('is_company', '=', False),
    #         ('parent_id', 'in', self.partner_ids.ids)]}
    #     return res

    @api.onchange('partner_contact_ids')
    def onchange_partner_contact_ids(self):
        if self.partner_contact_ids:
            self.mobile = self.partner_contact_ids[0].mobile
            self.phone = self.partner_contact_ids[0].phone

    @api.multi
    def action_convert2opportunity(self):
        self.ensure_one()
        opportunity = self.create_opportunity()
        return opportunity.redirect_opportunity_view()

    @api.multi
    def create_opportunity(self):
        self.ensure_one()
        partner = self.env['res.partner']
        opportunity = self.env['crm.lead']
        default_contact = False
        if self.partner_ids:
            partner = self.partner_ids[0]
        address_id = partner.address_get().get('default')
        if address_id:
            default_contact = partner.browse(address_id)
        opportunity = opportunity.create({
            'name': self.name,
            'planned_revenue': 0.0,
            'probability': 10.0,
            'partner_id': partner.id,
            'mobile': default_contact and default_contact.mobile,
            'type': 'opportunity',
            'phone': self.phone or False,
            'email_from': default_contact and default_contact.email,
            'main_description': self.description or '',
        })
        vals = {
            'partner_id': partner.id,
            'opportunity_id': opportunity.id,
            'state': 'done',
        }
        self.write(vals)
        return opportunity

    @api.model
    def create_from_phone_widget(self, model, res_id, number):
        if model == 'voip.phonecall':
            phonecall = self.env[model].browse(res_id)
        else:
            name = _('Call to ') + number
            partner_id = False
            if model == 'res.partner':
                partner_id = res_id
            else:
                record = self.env[model].browse(res_id)
                fields = self.env[model]._fields.items()
                partner_field_name = [k for k, v in fields if
                                      v.type == 'many2one' and v.comodel_name == 'res.partner'][
                    0]
                if len(partner_field_name):
                    partner_id = record[partner_field_name].id
            phonecall = self.create({
                'name': name,
                'phone': number,
                'partner_id': partner_id,
            })
        phonecall.init_call()
        return phonecall.get_info()[0]

    @api.multi
    def hangup_call(self):
        self.ensure_one()
        stop_time = int(time.time())
        duration_seconds = float(stop_time - self.start_time)
        duration = round(duration_seconds / 60, 2)
        seconds = duration_seconds - int(duration) * 60
        note = False
        if (self.activity_id):
            note = self.activity_id.note
            duration_log = '<br/><p>Call duration: ' + str(
                int(duration)) + 'min ' + str(int(seconds)) + 'sec</p>'
            if self.activity_id.note:
                self.activity_id.note += duration_log
            else:
                self.activity_id.note = duration_log
            self.activity_id.action_done()
        self.write({
            'state': 'done',
            'duration': duration,
            'note': note,
        })
        if self.markant_phonecall:
            self.message_post(
                body=_("<p><span class='fa fa-phone'/> Call done by " +
                       self.env['res.users'].browse(self.env.uid).name +
                       "</p><br/><p>Call duration: " +
                       str(int(duration)) + 'min ' +
                       str(int(seconds)) + 'sec</p>'))
        return

    @api.model
    def create(self, vals):
        res = super(VoipPhonecall, self).create(vals)
        if res.partner_ids and res.markant_phonecall:
            self.set_data(res)
        return res

    @api.multi
    def write(self, vals):
        res = super(VoipPhonecall, self).write(vals)
        if self.env.context.get('already_gen_name'):
            return res
        for record in self:
            if record.partner_ids and record.markant_phonecall:
                self.set_data(record)
            return res

    @api.model
    def set_data(self, record):
        first_partner = record.partner_ids[0]
        name = first_partner.name
        name = record.markant_phonecall_cate_id.name + ' - ' + name
        if record.opportunity_id:
            name = name + ' - ' + record.opportunity_id.name
        if record.description:
            name = name + ' - ' + record.description
        data = {
            'name': name
        }
        record.with_context(already_gen_name=True).write(data)

    @api.model
    def call_visit_email(self):
        template = self.env.ref(
            'markant_phonecall.email_template_markant_call_visit')
        user_lst = []
        for rec in self.search(
                [('next_action_date', '=', fields.date.today())]):
            if rec.user_id.id not in user_lst:
                user_lst.append(rec.user_id.id)
                template.send_mail(rec.id, force_send=True)
        return True

    @api.multi
    def action_make_meeting(self):
        """ This opens Meeting's calendar view to schedule meeting on current Phonecall
            @return : Dictionary value for created Meeting view
        """
        self.ensure_one()
        res = {}
        calendar_form = self.env.ref('calendar.view_calendar_event_form')

        ctx = dict(self.env.context)
        pids = self.partner_contact_ids.ids + self.partner_ids.ids
        ctx.update({
            'default_phonecall_id': self.id,
            'default_partner_ids': [(4, _id) for _id in pids],
            'default_name': self.name,
        })

        return {
            'name': _('Create Event'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'calendar.event',
            'views': [(calendar_form.id, 'form')],
            'view_id': calendar_form.id,
            'target': 'new',
            'context': ctx,
        }
        return res
