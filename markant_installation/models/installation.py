# -*- coding: utf-8 -*-

import datetime
from datetime import timedelta
import uuid
import base64

from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ReturnGoodLine(models.Model):
    _name = 'return.good.line'

    installation_id = fields.Many2one('markant.installation.form',
                                      string='Installation Form', copy=False)
    product_id = fields.Many2one('product.product', string='Product')
    name = fields.Text(string='Description', required=True)
    qty = fields.Integer(string='Quantity')


class UsedGoodLine(models.Model):
    _name = 'used.good.line'

    installation_id = fields.Many2one('markant.installation.form',
                                      string='Installation Form', copy=False)
    product_id = fields.Many2one('product.product', string='Product')
    name = fields.Text(string='Description', required=True)
    qty = fields.Integer(string='Quantity')


class InstallationInstallers(models.Model):
    _name = 'markant.installation.installers'

    installation_id = fields.Many2one('markant.installation.form',
                                      string='Installation Form', copy=False)
    days = fields.Selection([('sunday', 'Sunday'),
                             ('monday', 'Monday'),
                             ('tuesday', 'Tuesday'),
                             ('wednesday', 'Wednesday'),
                             ('thursday', 'Thursday'),
                             ('friday', 'Friday'),
                             ('saturday', 'Saturday')],
                            string='Days')
    arrival_time = fields.Datetime(string='Arrival')
    departure_time = fields.Datetime(string='Departure')
    number_installer = fields.Integer(
        string='Nr Installers')
    number_assistant_installer = fields.Integer(
        string='Nr assist Installers')
    number_of_hours = fields.Char(compute='_compute_number_of_hours',
                                  string='Nr Hours', copy=False)

    @api.multi
    @api.depends('arrival_time', 'departure_time',
                 'number_assistant_installer', 'number_installer')
    def _compute_number_of_hours(self):
        for inst in self:
            if inst.arrival_time and inst.departure_time:
                diff = inst.departure_time - inst.arrival_time
                hrs = diff.seconds / 3600
                day_hrs = diff.days * 24
                total_hrs = (day_hrs + hrs) * (inst.number_installer +
                                               inst.number_assistant_installer)
                inst.number_of_hours = str(timedelta(hours=total_hrs))[:-3]

    @api.onchange('departure_time', 'arrival_time')
    def onchange_arrival_departure_time(self):
        if self.departure_time and not self.arrival_time:
            self.departure_time = False
            return {
                'warning': {'title': _('Warning!'),
                            'message': _('Arrival Time is missing!')}
            }


class MarkantInstallationForm(models.Model):
    _name = 'markant.installation.form'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = 'Installation Form'
    _rec_name = 'name'

    def _get_default_access_token(self):
        return str(uuid.uuid4())

    @api.multi
    def _compute_stage_locks(self):
        self.top_lock = self.stage_id.top_lock
        self.bottom_lock = self.stage_id.bottom_lock

    name = fields.Char(string='Document Number', default='New', copy=False)
    sale_order_ids = fields.Many2many('sale.order',
                                      'installation_form_sale_rel',
                                      'order_id', 'form_id',
                                      string='Order Numbers')
    as400_order_ref = fields.Char(string='AS400 Order')
    end_user_id = fields.Many2one('res.partner', string='End User',
                                  domain=[('end_user', '=', True)])
    address_id = fields.Many2one('res.partner', string='Delivery Address')

    street_name = fields.Char()
    street_number = fields.Char(string='House')
    street_number2 = fields.Char(string='Door')
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one('res.country.state', string='State',
                               ondelete='restrict')
    country_id = fields.Many2one('res.country', string='Country',
                                 ondelete='restrict')

    dealer_id = fields.Many2one('res.partner', string='Dealer',
                                domain=[('customer', '=', True)])
    installation_type_id = fields.Many2one('markant.installation.type',
                                           string='Type')
    calculation_type_id = fields.Many2one('markant.calculation.type',
                                          string='Calculation')
    proposed_date_from = fields.Date(string='From')
    proposed_date_to = fields.Date(string='To')
    planned_date_from = fields.Date(string='From')
    planned_date_to = fields.Date(string='To')
    survey_needed = fields.Selection([('yes', 'Yes'),
                                      ('no', 'No'),
                                      ('na', 'Not applicable')],
                                     string='Survey Necessary')
    survey_date = fields.Date(string='Survey Date')
    survey_id = fields.Many2one('survey', string='Survey Form')
    staircase_available = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                           string='Staircase Available')
    any_empty_clean_zone = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                            string='Empty/Clean '
                                                   'rooms available')
    lift_available = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                      string='Lift Available')
    distance_place_unloading = fields.Integer(
        string='Distance to Place of Unloading (in Meter)')
    total_number_floors = fields.Integer(string='Total Number of Floors')
    floor_of_installation = fields.Integer(string='Floor of installation')
    google_drive_link = fields.Char(string='Google Drive')
    submit_date = fields.Date(string='Submit Date', copy=False,
                              default=fields.Date.today, readonly=True)
    installation_date = fields.Date(string='Installation Date')
    end_contact_id = fields.Many2one('res.partner', string='Contact Person')
    phone = fields.Char(string='Phonenumber')
    mobile = fields.Char(string='Mobile Number')
    email = fields.Char(string='Email')
    opportunity_ids = fields.Many2many('crm.lead', 'lead_installation_rel',
                                       'lead_id', 'form_id',
                                       string='Opportunities')
    dealer_contact_id = fields.Many2one(
        'res.partner', string='Dealer Contact',
        domain="[('parent_id', '=', dealer_id), ('customer', '=', True)]")
    phone_dealer = fields.Char(string='Phonenumber')
    mobile_dealer = fields.Char(string='Mobile Number')
    email_dealer = fields.Char(string='Email')
    site_drawing_avail = fields.Selection([('yes', 'Yes'),
                                           ('no', 'No')],
                                          string='Site Drawing Necessary')
    drawing_included = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                        string='Drawing Included')
    pre_assembly = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                    string='Pre Assembly')
    back_order = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                  string='Back Order')
    claim_ids = fields.Many2many('crm.claim', 'claim_installation_rel',
                                 'claim_id', 'form_id', string='Claims')
    note = fields.Html(string='Comment')
    internal_note = fields.Html(string='Internal Note')
    user_id = fields.Many2one('res.users', string='Created By',
                              default=lambda self: self.env.user.id,
                              copy=False, readonly=True)
    assignee_id = fields.Many2one('res.users', string='Assignee')
    stage_id = fields.Many2one(
        'markant.installation.stage', string='Stage',
        track_visibility='onchange', index=True, copy=False,
        default=lambda self: self.env.ref(
            'markant_installation.installation_draft'))
    enable_mail = fields.Boolean(
        string='Enable Send Mail Button',
        default=lambda self: self.env.ref(
            'markant_installation.installation_draft').enable_mail,
        copy=False)
    enable_preview = fields.Boolean(
        string='Enable Preview & Sign Button',
        default=lambda self: self.env.ref(
            'markant_installation.installation_draft').enable_preview,
        copy=False)
    enable_required = fields.Boolean(
        string='Enable Required Fields',
        default=lambda self: self.env.ref(
            'markant_installation.installation_draft').enable_required,
        copy=False)
    top_lock = fields.Boolean(
        string='Top Lock',
        compute='_compute_stage_locks',
        copy=False)
    bottom_lock = fields.Boolean(
        string='Bottom Lock',
        compute='_compute_stage_locks',
        copy=False)
    access_token = fields.Char(string='Security Token', copy=False,
                               default=_get_default_access_token)
    installation_installers_ids = fields.One2many('markant.installation.installers',
                                                  'installation_id',
                                                  string='Installation Installers')
    return_good_ids = fields.One2many('return.good.line', 'installation_id',
                                      string='Return Good Lines')
    used_good_ids = fields.One2many('used.good.line', 'installation_id',
                                    string='Used Good Lines')
    name_customer = fields.Char(string='Name',
                                copy=False, readonly=True)
    name_mechanic = fields.Char(string='Name',
                                copy=False, readonly=True)
    signature_customer = fields.Binary(string='Signature',
                                       copy=False, readonly=True)
    signature_mechanic = fields.Binary(string='Signature',
                                       copy=False, readonly=True)
    send_signature_mail = fields.Selection([('sent', 'Already Sent'),
                                            ('force_send', 'Force Send')],
                                           string='Send Signature eMail',
                                           copy=False)
    order_count = fields.Integer(string='Sale Orders',
                                 compute='_compute_order_ids')
    number_installer = fields.Integer(
        string='Number of Installers')
    number_assistant_installer = fields.Integer(
        string='Number of Assistant Installers')
    arrival_time = fields.Datetime(string='Arrival Time')
    departure_time = fields.Datetime(string='Departure Time')
    number_of_hours = fields.Char(compute='_compute_number_of_hours',
                                  string='Number of Hours', copy=False)
    linked_installation_ids = fields.Many2many('markant.installation.form',
                                               'linked_installation_form_rel',
                                               'form_id', 'linked_form_id',
                                               string='Installation Form')
    linked_installation_count = fields.Integer(string='Installation Form',
                                               compute='_compute_linked_installation')
    require_initial_so = fields.Boolean(string="Require Initial SO")
    initial_so_id = fields.Many2one('sale.order', string='Initial SO',
                                    copy=False)

    @api.onchange('installation_type_id')
    def _onchange_installation_type_id(self):
        if self.installation_type_id:
            self.require_initial_so = \
                self.installation_type_id.require_initial_so
        else:
            self.require_initial_so = False

    @api.onchange('require_initial_so')
    def _onchange_require_initial_so(self):
        if not self.require_initial_so:
            self.initial_so_id = False

    @api.multi
    @api.depends('arrival_time', 'departure_time',
                 'number_assistant_installer', 'number_installer')
    def _compute_number_of_hours(self):
        self.ensure_one()
        if self.arrival_time and self.departure_time:
            diff = self.departure_time - self.arrival_time
            hrs = diff.seconds / 3600
            day_hrs = diff.days * 24
            total_hrs = (day_hrs + hrs) * (self.number_installer +
                                           self.number_assistant_installer)
            self.number_of_hours = str(timedelta(hours=total_hrs))[:-3]

    @api.onchange('departure_time', 'arrival_time')
    def onchange_arrival_departure_time(self):
        if self.departure_time and not self.arrival_time:
            self.departure_time = False
            return {
                'warning': {'title': _('Warning!'),
                            'message': _('Arrival Time is missing!')}
            }
        if (self.arrival_time and self.departure_time) and \
                (self.departure_time < self.arrival_time):
            self.departure_time = False
            return {
                'warning': {'title': _('Warning!'),
                            'message': _('Departure Time should always '
                                         'greater than Arrival Time.')}
            }

    @api.depends('linked_installation_ids')
    def _compute_linked_installation(self):
        for inst in self:
            inst.linked_installation_count = len(inst.linked_installation_ids)

    @api.depends('sale_order_ids')
    def _compute_order_ids(self):
        for order in self:
            order.order_count = len(order.sale_order_ids)

    @api.multi
    def action_view_linked_installation(self):
        action = self.env.ref('markant_installation.action_markant_installation_form').read()[0]

        link_installation = self.mapped('linked_installation_ids')
        if len(link_installation) > 1:
            action['domain'] = [('id', 'in', link_installation.ids)]
        elif link_installation:
            form_view = [(self.env.ref(
                'markant_installation.view_installation_form_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in
                                               action['views'] if
                                               view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = link_installation.id
        return action

    @api.multi
    def action_view_sale(self):
        action = self.env.ref('sale.action_orders').read()[0]

        sale_orders = self.mapped('sale_order_ids')
        if len(sale_orders) > 1:
            action['domain'] = [('id', 'in', sale_orders.ids)]
        elif sale_orders:
            form_view = [(self.env.ref(
                'sale.view_order_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in
                                               action['views'] if
                                               view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = sale_orders.id
        return action

    def _compute_access_url(self):
        super(MarkantInstallationForm, self)._compute_access_url()
        for installation in self:
            installation.access_url = '/installation/%s' % installation.id

    @api.onchange('end_contact_id')
    def onchange_end_contact_id(self):
        if self.end_contact_id:
            self.phone = self.end_contact_id.phone
            self.mobile = self.end_contact_id.mobile
            self.email = self.end_contact_id.email

    @api.multi
    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s' % self.name

    @api.onchange('address_id')
    def onchange_address_id(self):
        if self.address_id:
            self.street_name = self.address_id.street_name
            self.street2 = self.address_id.street2
            self.street_number = self.address_id.street_number
            self.street_number2 = self.address_id.street_number2
            self.zip = self.address_id.zip
            self.city = self.address_id.city
            self.state_id = self.address_id.state_id.id \
                if self.address_id.state_id else False
            self.country_id = self.address_id.country_id.id \
                if self.address_id.country_id else False

    @api.model
    def create(self, vals):
        vals['name'] = \
            self.env['ir.sequence'].next_by_code('markant.installation.form') \
            or '/'
        res = super(MarkantInstallationForm, self).create(vals)
        if res.assignee_id:
            users = res.assignee_id - self.env.user
            if users:
                partners = users.partner_id
                res.message_subscribe(partners.ids)
                res.action_send_mail_followers(res.assignee_id.name,
                                               res.assignee_id.partner_id.id)

        if vals.get('installation_installers_ids'):
            installers = vals.get('installation_installers_ids')
            for install in installers:
                arrival = install[2]['arrival_time']
                departure = install[2]['departure_time']
                if arrival and departure and departure < arrival:
                    raise Warning(_('Departure Time should always be greater '
                                    'than Arrival Time.'))
        return res

    @api.multi
    def write(self, vals):
        if self.enable_required:
            if (not vals.get('site_drawing_avail') and
                not self.site_drawing_avail) or \
                    (not vals.get('drawing_included') and
                     not self.drawing_included) or \
                    (not vals.get('pre_assembly') and
                     not self.pre_assembly) or \
                    (not vals.get('back_order') and
                     not self.back_order) or \
                    (not vals.get('survey_needed') and
                     not self.survey_needed):
                raise Warning(_('Required fields are missing!'))
        if vals.get('assignee_id'):
            assignee_user = self.env['res.users'].browse(vals['assignee_id'])
            users = assignee_user - self.env.user
            if users:
                partners = users.partner_id
                self.message_subscribe(partners.ids)
                self.action_send_mail_followers(assignee_user.name,
                                                assignee_user.partner_id.id)
        if vals.get('stage_id'):
            stage = self.env['markant.installation.stage'].search([('id', '=', vals.get('stage_id'))])
            if stage and stage.cancel_stage:
                self.message_post(body=_('The Installation Form <a href=# data-oe-model=markant.installation.form data-oe-id=%d>%s</a> has been cancelled.') % (self.id, self.name),
                                  subtype='mt_comment')

        res = super(MarkantInstallationForm, self).write(vals)
        for inst in self.installation_installers_ids:
            if inst.departure_time and inst.arrival_time \
                    and inst.departure_time < inst.arrival_time:
                raise Warning(_('Departure Time should always be greater than '
                                'Arrival Time.'))
        return res

    @api.multi
    def send_signature_email(self):
        self.ensure_one()
        try:
            template = self.env.ref(
                'markant_installation.email_template_edi_installation')
        except ValueError:
            template = False

        email_to = []
        if self.email_dealer:
            email_to.append(self.email_dealer)
        if self.email:
            email_to.append(self.email)

        if email_to:
            email_values = ','.join(email_to)
            template.send_mail(self.id, force_send=True, email_values={'email_to': email_values})
        else:
            template.send_mail(self.id, force_send=True)

        return True

    @api.onchange('sale_order_ids')
    def onchange_sale_order_ids(self):
        if self.sale_order_ids and len(self.sale_order_ids) > 1:
            customer = []
            for order in self.sale_order_ids:
                customer.append(order.partner_id.id)
            if len(set(customer)) > 1:
                raise Warning(_('Can not select Order which contains '
                                'different Customers/Contacts.'))

    @api.onchange('stage_id')
    def onchange_stage_id(self):
        if self.stage_id:
            self.enable_mail = self.stage_id.enable_mail
            self.enable_preview = self.stage_id.enable_preview
            self.enable_required = self.stage_id.enable_required

    @api.onchange('survey_id')
    def onchange_survey_id(self):
        if self.survey_id:
            self.survey_date = self.survey_id.creation_date
            self.staircase_available = self.survey_id.staircase_available
            self.distance_place_unloading = \
                self.survey_id.distance_place_unloading
            self.total_number_floors = self.survey_id.total_number_floors \
                if self.survey_id.total_number_floors else False
            self.lift_available = self.survey_id.lift_available
            self.number_mechanics_assistant = \
                (self.survey_id.number_mechanics
                 if self.survey_id.number_mechanics else 0) + \
                (self.survey_id.number_assistant
                 if self.survey_id.number_assistant else 0)

    @api.onchange('dealer_contact_id')
    def onchange_dealer_contact_id(self):
        if not self.dealer_id and self.dealer_contact_id:
            self.dealer_contact_id = False
            return {
                'warning': {'title': _('Warning!'),
                            'message': _('Please, select Dealer first '
                                         'in order to select its contact.')}
            }
        else:
            self.phone_dealer = self.dealer_contact_id.phone
            self.mobile_dealer = self.dealer_contact_id.mobile
            self.email_dealer = self.dealer_contact_id.email

    @api.multi
    def action_send_mail(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference(
                'markant_installation', 'email_template_edi_installation')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(
                'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        if self.dealer_contact_id or self.dealer_id:
            email_to = self.dealer_contact_id.id \
                if self.dealer_contact_id else self.dealer_id.id
        else:
            if self.end_contact_id:
                email_to = self.end_contact_id.id
            else:
                email_to = self.end_user_id.id

        email_to_name = False
        if email_to:
            email_to_name = self.env['res.partner'].search(
                [('id', '=', email_to)]).name
        ctx = {
            'default_model': 'markant.installation.form',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'email_to': email_to,
            'email_to_name': email_to_name
        }
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def action_send_mail_followers(self, assignee_name=False,
                                   partner_id=False):
        self.ensure_one()
        try:
            template = self.env.ref('markant_installation.email_template_edi_installation_followers')
        except ValueError:
            template = False

        if partner_id and assignee_name:
            template.with_context(
                follower_name=assignee_name,
                follower_partner=partner_id).send_mail(self.id,
                                                       force_send=True)
        return True

    @api.multi
    def action_send_cancelled_mail_followers(self, assignee_name=False,
                                             partner_id=False):
        self.ensure_one()
        try:
            template = self.env.ref(
                'markant_installation.cancelled_email_template_edi_installation_followers')
        except ValueError:
            template = False

        if partner_id and assignee_name:
            template.with_context(
                follower_name=assignee_name,
                follower_partner=partner_id).send_mail(self.id, force_send=True)
        return True

    @api.multi
    def preview_installation_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def name_get(self):
        if self._context.get('markant_display_only_name', False):
            res = []
            for partner in self:
                name = ''
                if partner.name:
                    name = partner.name
                res.append((partner.id, name))
            return res
        return super(ResPartner, self).name_get()
