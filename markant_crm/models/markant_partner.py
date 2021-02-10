from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DebtorCreation(models.Model):
    _name = 'debtor.creation'
    _description = 'Debtor Creation'

    name = fields.Char(string='Name', required=1)
    email = fields.Char(string='Email')


class CreditorCreation(models.Model):
    _name = 'creditor.creation'
    _description = 'Creditor Creation'

    name = fields.Char(string='Name', required=1)
    email = fields.Char(string='Email')


class JobPosition(models.Model):
    _name = 'job.position'
    _description = 'Job Position'

    name = fields.Char(string='Job Position', required=1)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    parent_id1 = fields.Many2one('res.partner', string='Related Company')

    child_ids = fields.One2many('res.partner', 'parent_id', string='Contacts',
                                domain=[('active', '=', True),
                                        ('type', '=', 'contact')])
    # force "active_test" domain to bypass _search() override

    child_ids_address = fields.One2many('res.partner', 'parent_id1',
                                        string='Addresses',
                                        domain=[('active', '=', True),
                                                ('type', '!=', 'contact')])
    # force "active_test" domain to bypass _search() override

    partner_seq = fields.Integer(string='Sequence')
    end_user = fields.Boolean(string='End User')
    att_link = fields.Char(string='To Google Drive', size=1024)
    influencer = fields.Boolean(string='Influencer')
    job_position_id = fields.Many2one('job.position', string='Job position')
    customer = fields.Boolean(string='Dealer', default=False)
    linkedin_url = fields.Char(string="Linkedin url")
    active = fields.Boolean(string='Active', default=True)
    is_company = fields.Boolean(string='Is a Company?', default=True)
    dealer_ids = fields.Many2many('res.partner', 'enduser_dealer_rel',
                                  'enduser_id', 'dealer_id',
                                  string='Dealers')
    end_user_ids = fields.Many2many('res.partner', 'enduser_dealer_rel',
                                    'dealer_id', 'enduser_id',
                                    string='End Users')
    end_user_id = fields.Many2one('res.partner', string='End User',
                                  domain=[('end_user', '=', True)])
    influencer_ids = fields.Many2many('res.partner',
                                      'influencer_influenced_rel',
                                      'influencer_id', 'influenced_id',
                                      string='Influencing')
    infuenced_ids = fields.Many2many('res.partner',
                                     'influencer_influenced_rel',
                                     'influenced_id', 'influencer_id',
                                     string='Influenced by')
    dealer_oppor_ids = fields.Many2many(
        'crm.lead', string='Opportunities',
        compute='_compute_dealer_influencer_oppr_ids')
    influencer_oppor_ids = fields.Many2many(
        'crm.lead', string='Opportunities',
        compute='_compute_dealer_influencer_oppr_ids')
    pipeline_ids = fields.One2many('partner.crm.lead', 'partner_id',
                                   string='Pipelines',
                                   domain=[('is_display', '=', True)])
    influencer_type = fields.Selection([
                                ('architect', 'Architect'),
                                ('facility2', 'Facility Manager'),
                                ('other', 'Other')], string='Influencer')
    internal_note = fields.Text(string='Internal Note')
    opp_ids = fields.One2many('crm.lead', 'partner_id', string="Oppo")
    opp_count = fields.Integer(string='Opp', compute='_compute_opp_count')
    opp_dealer_count = fields.Integer(string='Opp',
                                      compute='_compute_opp_count')
    lead_ids = fields.One2many('crm.lead', 'partner_id', string='Lead')
    lead_count = fields.Integer(string='Leads', compute='_compute_lead_count')
    phonecall_count = fields.Integer(string='Phonecall Count',
                                     compute='_compute_phonecall_count')
    phonecall_count_company = fields.Integer(
        string='Company Phonecall Count', compute='_compute_phonecall_count')
    all_phonecall_count = fields.Integer(string='All Phonecall Count',
                                         compute='_compute_phonecall_count')
    parent_count = fields.Integer(string='Parent', compute='_compute_pipeline')
    child_count = fields.Integer(string='Child', compute='_compute_pipeline')
    stage_ids = fields.Many2many('crm.stage', string='Stage',
                                 group_expand='_read_group_stage_ids')
    fax = fields.Char(string='Fax')
    email_invoices = fields.Char(string='Email Invoices')
    email_orders = fields.Char(string='Email Orders')
    chamber_of_commerce = fields.Char(string='Chamber of Commerce')

    # ZEN: Rename and add new field to display contact id
    relation_number = fields.Char(string='Relation-number (AS400 Old ID)')
    pricelist_discount_group = fields.Char(string='Pricelist discount group')

    # New field to count the quotation linked ton influencer
    influencer_quotation_count = fields.Integer(compute="_compute_influencer_quotation_count")

    # HITESH : add new field to set default addresses like invoice or shipping ones
    is_default_address = fields.Boolean(string="Default Address")

    @api.multi
    def _compute_influencer_quotation_count(self):
        SaleOrder = self.env['sale.order'].search([('state', 'in', ['draft', 'sent'])])
        for partner in self:
            if partner.influencer:
                quotations = SaleOrder.filtered(lambda r: partner in r.influencer_ids)
                partner.influencer_quotation_count = len(quotations)
            else:
                partner.influencer_quotation_count = 0

    @api.multi
    def list_influencer_quotations(self):
        action = self.env.ref('sale.action_quotations_with_onboarding')
        ctx = self.env.context
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'view_type': action.view_type,
            'view_mode': action.view_mode,
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        SaleOrder = self.env['sale.order'].search([('state', 'in', ['draft', 'sent'])])
        quotations = SaleOrder.filtered(lambda r: self in r.influencer_ids)
        if len(quotations) > 1:
            result['domain'] = "[('id','in',["+','.join(map(str, quotations.ids))+"])]"
        elif len(quotations) == 1:
            form = self.env.ref('sale.view_order_form', False)
            form_id = form.id if form else False
            result['views'] = [(form_id, 'form')]
            result['res_id'] = quotations.ids[0]
        else:
            return True
        return result

    @api.onchange('end_user_id')
    def _onchange_end_user_id(self):
        if self.end_user_id:
            self.first_name = False
            self.last_name = False
            self.job_position_id = False
            self.title = False
            if not self.end_user_id.is_company:
                self.first_name = self.end_user_id.first_name
                self.last_name = self.end_user_id.last_name
                self.job_position_id = self.end_user_id.job_position_id.id
                self.title = self.end_user_id.title
            self.name = self.end_user_id.name or False
            self.email = self.end_user_id.email or False
            self.phone = self.end_user_id.phone or False
            self.mobile = self.end_user_id.mobile or False
            self.use_parent_address = False
            self.street = self.end_user_id.street or False
            self.street2 = self.end_user_id.street2 or False
            self.city = self.end_user_id.city or False
            self.state_id = self.end_user_id.state_id.id or False
            self.zip = self.end_user_id.zip or False
            self.country_id = self.end_user_id.country_id.id or False
            self.linkedin_url = self.end_user_id.linkedin_url or False
            self.category_id = self.end_user_id.category_id or False
            self.base_group_ids = self.end_user_id.base_group_ids or False
            self.base_lead_source_id = self.end_user_id.base_lead_source_id or False

    @api.multi
    def _check_influencer(self):
        for partner in self:
            if not partner.influencer:
                if partner.influencer_ids:
                    return False
        return True

    @api.multi
    def _check_default_address(self):
        for record in self:
            parent = record.parent_id
            if parent and record.type != 'contact':
                default_address = parent.child_ids_address.filtered(lambda child: child.is_default_address and child.type == record.type and child != record)
                if default_address and record.is_default_address:
                    return False
        return True

    _constraints = [
        (_check_influencer, "This contact is influencing other contact(s) "
                            "and cannot be unticked", []),
        (_check_default_address, "You cannot set two as default address.", [])
    ]

    @api.multi
    def _compute_phonecall_count(self):
        Phonecall = self.env['voip.phonecall']
        for rec in self:
            if rec.is_company:
                rec.phonecall_count_company = Phonecall.search_count(
                    [('partner_ids', 'in', rec.ids)])
                company_phonecall = Phonecall.search(
                    [('partner_ids', 'in', rec.ids)]).ids
                contact_phonecall = Phonecall.search(
                    [('partner_contact_ids', 'in',
                      rec.child_ids.ids + rec.child_ids_address.ids)]).ids
                final_phonecall = list(set(company_phonecall +
                                           contact_phonecall))
                rec.all_phonecall_count = len(final_phonecall)
            else:
                rec.phonecall_count = Phonecall.search_count(
                    [('partner_contact_ids', 'in', rec.ids)])

    @api.multi
    def show_all_phonecall(self):
        def ref(module, xml_id):
            proxy = self.env['ir.model.data']
            return proxy.get_object_reference(module, xml_id)

        model, form_view_id = ref('markant_phonecall',
                                  'markant_voip_phonecall_form_view')
        model, tree_view_id = ref('markant_phonecall',
                                  'markant_voip_phonecall_tree_view')

        views = [
            (tree_view_id, 'tree'),
            (form_view_id, 'form'),
        ]

        for rec in self:
            return {
                'name': _('Partner Phonecalls'),
                'type': 'ir.actions.act_window',
                'res_model': 'voip.phonecall',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'views': views,
                'view_id': False,
                'domain': ['|', ('partner_ids', 'in', rec.ids),
                           ('partner_contact_ids', 'in', rec.child_ids.ids +
                            rec.child_ids_address.ids)],
                'context': {'default_markant_phonecall': True,
                            'default_partner_contact_ids': rec.ids,
                            'phonecall_from_partner': True}
            }

    @api.depends('opportunity_ids')
    def _compute_pipeline(self):
        DealersOpportunityInfo = self.env['dealers.opportunity.info']
        for part in self:
            if part.end_user:
                part.parent_count = len(part.opportunity_ids.ids)

            # # search lead where partner as dealer
            child_pipeline_ids = DealersOpportunityInfo.search(
                [('dealer_id', '=', part.id)])
            part.child_count = len(child_pipeline_ids.ids)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        CrmLead = self.env['crm.lead']
        if args is None:
            args = []
        lead_id = self.env.context.get('lead_id')
        if lead_id:
            # when not lead_id, fix key='nothing' and
            # not allow display customer
            # on preferred_dealer_id
            if lead_id == 'nothing':
                domain = [('id', 'in', [])]
            else:
                domain = []
                lead = CrmLead.browse(self.env.context['lead_id'])
                partner_ids = lead.dealer_oppor_info_ids.mapped('dealer_id.id')
                domain.append(('id', 'in', partner_ids))
            return self.search(args + domain, limit=limit).name_get()
        return super(ResPartner, self).name_search(name, args=args,
                                                   operator=operator,
                                                   limit=limit)

    @api.multi
    def action_view_parent_opportunity(self):
        self.ensure_one()
        context = dict(self._context or {})
        context.update({
            'partner_id': self.id,
            'default_type': 'opportunity',
        })
        result = self.env.ref('crm.relate_partner_opportunities').read()[0]
        result['domain'] = [
            ('partner_id.end_user', '=', True),
            ('partner_id', '=', self.id),
            ('type', '=', 'opportunity'),
        ]
        # Remove context so it is not going to filter on product_id
        # with active_id of template
        result['context'] = context
        return result

    @api.multi
    def action_view_child_opportunity(self):
        self.ensure_one()
        context = dict(self._context or {})
        context.update({
            'partner_id': self.id,
            'hide_dealer': True
        })
        result = self.env.ref(
            'markant_crm.action_your_pipeline_child').read()[0]
        result['domain'] = [('dealer_id', '=', self.id)]
        # Remove context so it is not going to filter on
        # product_id with active_id of template
        result['context'] = context
        return result

    @api.multi
    def action_view_opportunity(self):
        self.ensure_one()
        context = dict(self._context or {})
        context.update({
            # 'search_default_partner_id': self.id,
            'default_type': 'opportunity',
        })
        result = self.env.ref('crm.relate_partner_opportunities').read()[0]
        result['domain'] = [('id', 'in', self.mapped('dealer_oppor_ids').ids)]
        # Remove context so it is not going to filter on
        # product_id with active_id of template
        result['context'] = context
        return result

    @api.multi
    def action_view_dealer_opportunity(self):
        self.ensure_one()
        context = dict(self._context or {})
        context.update({
            'partner_id': self.id,
            'hide_dealer': True
        })
        result = self.env.ref('crm.relate_partner_opportunities').read()[0]
        result['domain'] = [('id', 'in', self.mapped('dealer_oppor_ids').ids)]
        # Remove context so it is not going to filter on
        # product_id with active_id of template
        result['context'] = context
        return result

    @api.multi
    def action_view_phonecall(self):
        self.ensure_one()
        result = self.env.ref('crm.crm_case_categ_phone_incoming0').read()[0]
        call_ids = []
        for rec in self:
            call_ids = self.env['crm.phonecall'].search([]).filtered(
                        lambda r: rec in r.partner_ids)
        result['domain'] = \
            "[('id', 'in', ["+','.join(map(str, call_ids.ids))+"])]"
        return result

    @api.one
    def _get_call_ids(self):
        for rec in self:
            rec.call_ids = self.env["crm.phonecall"].search([]).filtered(
                lambda r: rec in r.partner_ids)

    @api.depends('dealer_oppor_ids')
    def _compute_opp_count(self):
        for oppo in self:
            data = len(oppo.dealer_oppor_ids.filtered(
                    lambda r: r.type == 'opportunity').ids)
            oppo.opp_count = data
            oppo.opp_dealer_count = data

    @api.depends('lead_ids')
    def _compute_lead_count(self):
        for lead in self:
            lead.lead_count = len(lead.lead_ids.filtered(
                    lambda r: r.type == 'lead' or r.type == False).ids)

    @api.one
    @api.constrains('name', 'supplier', 'customer', 'influencer', 'end_user',
                    'street', 'street2', 'city', 'state_id', 'zip',
                    'country_id')
    def _check_unique_partner(self):
        if self.is_company:
            partner_ids = False
            if self.street2 and self.state_id:
                partner_ids = self.search(
                    [('id', '!=', self.id), ('name', '=', self.name),
                     ('street', '=', self.street),
                     ('street2', '=', self.street2),
                     ('city', '=', self.city),
                     ('state_id.id', '=', self.state_id.id),
                     ('zip', '=', self.zip),
                     ('country_id.id', '=', self.country_id.id)])
            if self.street2 and not self.state_id:
                partner_ids = self.search(
                    [('id', '!=', self.id), ('name', '=', self.name),
                     ('street', '=', self.street),
                     ('street2', '=', self.street2),
                     ('city', '=', self.city), ('zip', '=', self.zip),
                     ('country_id.id', '=', self.country_id.id)])
            if not self.street2 and self.state_id:
                partner_ids = self.search(
                    [('id', '!=', self.id), ('name', '=', self.name),
                     ('street', '=', self.street), ('city', '=', self.city),
                     ('state_id.id', '=', self.state_id.id),
                     ('zip', '=', self.zip),
                     ('country_id.id', '=', self.country_id.id)])
            if not self.street2 and not self.state_id:
                partner_ids = self.search(
                    [('id', '!=', self.id), ('name', '=', self.name),
                     ('street', '=', self.street),
                     ('city', '=', self.city), ('zip', '=', self.zip),
                     ('country_id.id', '=', self.country_id.id)])
            for partner in partner_ids:
                if partner.customer == self.customer and \
                        partner.supplier==self.supplier and \
                        partner.influencer==self.influencer and \
                        partner.end_user==self.end_user:
                    raise Warning(_('Created partner name "%s" '
                                    'already exist!!') % partner.name)
        else:
            domain = [('id', '!=', self.id), ('name', '=', self.name),
                      ('street', '=', self.street),
                      ('street2', '=', self.street2),
                      ('city', '=', self.city), ('zip', '=', self.zip),
                      ('parent_id.id', '=', self.parent_id.id)]

            if self.state_id:
                domain.append(('state_id.id', '=', self.state_id.id))

            if self.country_id:
                domain.append(('country_id.id', '=', self.country_id.id))

            if self.search(domain):
                raise Warning(_('Created partner name "%s" '
                                'already exist!!') % self.name)

    @api.model
    def create(self, vals):
        if vals.get('parent_id'):
            vals['is_company'] = False

            parent = self.search([('id', '=', vals.get('parent_id')),
                                  ('is_company', '=', True)], limit=1)
            if parent and parent.user_id:
                vals['user_id'] = parent.user_id.id
        partner = super(ResPartner, self).create(vals)

        if vals.get('parent_id') and vals.get('end_user_id') \
                and vals.get('type') == 'delivery':
            parent = self.browse(vals['parent_id'])
            parent.write({'end_user_ids': [(4, vals['end_user_id'])]})

        Mail = self.env['mail.mail']
        if partner.is_company and (not partner.credit_limit or
                                   not partner.property_payment_term) and \
                (partner.customer or partner.supplier):
            email_to = ""
            if partner.supplier:
                _email = self.env['creditor.creation'].search(
                    [], limit=1).email
                email_to += _email or ''
            if partner.customer:
                if email_to:
                    email_to += " , "
                _email = self.env['debtor.creation'].search([], limit=1).email
                email_to += _email or ''

            if email_to:
                body = ''' <div><p>Hello,</p>
                    <p>This mail regarding setting new partner 
                    <blockquote>%s</blockquote> credit limit and payment 
                    term </p>
                    <p>Requested you to please set credit limit and 
                    payment term for partner %s.</p>
                    <p>Thanks for your help!<p>
                    </div>''' % (partner.name, partner.name)
                mail = Mail.create({
                        'email_from': self.env.user.email,
                        'email_to': email_to,
                        'subject': 'Mail regarding set Partner Credit Limit '
                                   'and Payment Term',
                        'body_html': '<pre>%s</pre>' % body})
                mail.send()
        if partner.parent_id:
            company = partner.parent_id
            partner.write({'customer': company.customer,
                           'end_user': company.end_user,
                           'influencer': company.influencer,
                           'supplier': company.supplier})
        return partner

    @api.model
    def SendEmailToDealer(self):
        return True

    @api.depends('dealer_ids', 'influencer_ids')
    def _compute_dealer_influencer_oppr_ids(self):
        CrmLead = self.env['crm.lead']
        for partner in self:
            if partner.ids:
                dealer_oppr_ids = CrmLead.search([
                    '|', ('dealer_partner_ids', 'in', [partner.id]),
                    ('partner_id', 'in', [partner.id]),
                    ('type', '=', 'opportunity')
                ])
                influencer_oppr_ids = CrmLead.search([
                    ('influencer_ids', 'in', [partner.id]),
                    ('type', '=', 'opportunity')])
                partner.dealer_oppor_ids = dealer_oppr_ids
                partner.influencer_oppor_ids = influencer_oppr_ids

    @api.multi
    def partner_crm_lead_by_state(self):
        """
            get all line of current partner
            and set is_display filter by stage
        :return:
        """
        for record in self:
            list_line = self.env['partner.crm.lead'].search(
                ['&', ('partner_id', '=', record.id),
                 '|', ('oppo_id', '!=', False),
                 ('child_oppo_id', '!=', False)])
            for line in list_line:
                if line.oppo_id:
                    obj = line.oppo_id
                elif line.child_oppo_id:
                    obj = line.child_oppo_id
                if obj.stage_id and obj.stage_id.id in self.stage_ids.ids:
                    line.is_display = True
                else:
                    line.is_display = False

    @api.multi
    def clear_filter_partner_crm_lead(self):
        """
            clear filter stage of partner.crm.lead
        :return:
        """
        for record in self:
            list_line = self.env['partner.crm.lead'].search(
                [('partner_id', '=', record.id), ('is_display', '=', False)])
            list_line.write({'is_display': True})
            # remove stage_ids data
            record.stage_ids = None

    @api.multi
    def write(self, vals):
        if 'active' in vals \
                and vals.get('active') is False \
                and \
                not self.env.user.has_group(
                    'markant_crm.group_partner_archive'):
            raise ValidationError(
                _('You don\'t have permission to archive this contact !'))
        return super(ResPartner, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('markant_crm.group_partner_archive'):
            raise ValidationError(
                _('You don\'t have permission to delete this contact !'))
        return super(ResPartner, self).unlink()

    # HITESH : Override below method bcz we have added domain on child_ids , so due to this 
    # below method always return the contact type records not addreses.
    @api.multi
    def address_get(self, adr_pref=None):
        """ Find contacts/addresses of the right type(s) by doing a depth-first-search
        through descendants within company boundaries (stop at entities flagged ``is_company``)
        then continuing the search at the ancestors that are within the same company boundaries.
        Defaults to partners of type ``'default'`` when the exact type is not found, or to the
        provided partner itself if no type ``'default'`` is found either. """
        adr_pref = set(adr_pref or [])
        if 'contact' not in adr_pref:
            adr_pref.add('contact')
        result = {}
        visited = set()
        for partner in self:
            current_partner = partner
            while current_partner:
                to_scan = [current_partner]
                # Scan descendants, DFS
                while to_scan:
                    record = to_scan.pop(0)
                    visited.add(record)
                    if record.type in adr_pref and not result.get(record.type):
                        result[record.type] = record.id
                    if len(result) == len(adr_pref):
                        return result
                    # HITESH : Here we add the child_ids plus address so all work well.
                    print ("---->",record.child_ids + record.child_ids_address)
                    to_scan = [c for c in record.child_ids + record.child_ids_address
                                 if c not in visited
                                 if not c.is_company] + to_scan

                    # DefaultAddress : below code is to find the default addresses
                    for ap in adr_pref:
                        if not result.get(ap):
                            find_match = False
                            for ts in to_scan:
                                if ts.type == ap and ts.is_default_address:
                                    find_match = ts
                                    break
                            if find_match:
                                result[ap] = find_match[0].id
                    # End DefaultAddress

                # Continue scanning at ancestor if current_partner is not a commercial entity
                # HITESH : Here we stop searching for parent company
                # if current_partner.is_company or not current_partner.parent_id:
                if True:
                    break
                current_partner = current_partner.parent_id

        # default to type 'contact' or the partner itself
        default = result.get('contact', self.id or False)
        for adr_type in adr_pref:
            result[adr_type] = result.get(adr_type) or default
        return result

class LeadPartner(models.Model):
    _name = "partner.crm.lead"
    _description = "Partner - CRM Lead"
    _order = "date_deadline"

    name = fields.Char(string='Opportunity', compute='_compute_all')
    probability = fields.Float(string='Probability', group_operator='avg',
                               compute='_compute_all')
    planned_revenue = fields.Float(string='Expected Revenue',
                                   compute='_compute_all')
    planned_revenue_backend = fields.Float(string='Planned Revenue Backend',
                                           compute='_compute_all')
    user_id = fields.Many2one('res.users', string='Salesperson',
                              compute='_compute_all')
    referred = fields.Char(string='Referred By', compute='_compute_all')
    email_from = fields.Char(string='Email',
                             help='Email address of the contact',
                             compute='_compute_all')
    team_id = fields.Many2one('crm.team', string='Sales Channel',
                              compute='_compute_all')

    date_deadline = fields.Date(
        string='Expected Closing', help='Estimate of the date on which '
                                 'the opportunity will be won.')
    company_id = fields.Many2one('res.company', string='Company',
                                 compute='_compute_all')
    company_currency = fields.Many2one(string='Currency',
                                       related='company_id.currency_id',
                                       relation='res.currency')
    phone = fields.Char(string='Phone', compute='_compute_all')

    other_currency_id = fields.Many2one('res.currency',
                                        string='Other Currency',
                                        compute='_compute_all')

    commission = fields.Float(string='Commission', compute='_compute_all')
    commission_per = fields.Float(string='Commission %',
                                  compute="_compute_all")
    planned_revenue_other_currency = fields.Float(
        string='Expected Revenue other Currency', compute="_compute_all")

    commission_currency_id = fields.Many2one('res.currency', string='Currency',
                                             compute='_compute_all')
    stage_id = fields.Many2one('crm.stage', string='Stage',
                               search='_search_stage_id',
                               group_expand='_read_group_stage_ids')

    # Don't mess with below fields
    customer_id = fields.Many2one('res.partner', string='Customer',
                                  compute='_compute_all')
    partner_id = fields.Many2one('res.partner', string='Customer')
    # to remove default value by default_opportunity_id
    oppo_id = fields.Many2one('crm.lead', string='Pipeline',
                              ondelete='cascade')
    child_oppo_id = fields.Many2one('dealers.opportunity.info',
                                    string='Child Pipeline',
                                    ondelete='cascade')
    is_display = fields.Boolean(string='Display', default=True)

    def _compute_all(self):
        for rec in self.filtered(lambda r: r.oppo_id or r.child_oppo_id):
            if rec.child_oppo_id:
                lead = rec.child_oppo_id
                rec.customer_id = \
                    rec.child_oppo_id.opportunity_id.partner_id.id
                rec.commission_per = lead.commission_per
                rec.commission = lead.commission
            elif rec.oppo_id:
                lead = rec.oppo_id
                rec.customer_id = rec.oppo_id.partner_id.id
                rec.commission_per = lead.commission
                rec.commission = lead.commission_amount

            rec.name = lead.name
            rec.company_id = lead.company_id.id
            rec.commission_currency_id = lead.commission_currency_id.id
            rec.probability = lead.probability
            rec.planned_revenue_other_currency = \
                lead.planned_revenue_other_currency
            rec.other_currency_id = lead.other_currency_id.id
            rec.user_id = lead.user_id.id
            rec.email_from = lead.email_from
            # rec.stage_id = lead.stage_id.id
            rec.phone = lead.phone
            rec.team_id = lead.team_id.id

            planned_revenue = rec.other_currency_id. \
                compute(rec.planned_revenue_other_currency,
                        rec.company_currency)
            rec.planned_revenue = planned_revenue
