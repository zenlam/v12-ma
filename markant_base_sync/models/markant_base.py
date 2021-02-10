from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from . import basecrm
from datetime import datetime


class BaseSynchronization(models.Model):
    _name = 'base.synchronization'

    name = fields.Char(required=True)
    sync_lead = fields.Boolean(string="Sync Lead ?", default=True)
    sync_note = fields.Boolean(string="Sync Notes ?", default=True)
    sync_task = fields.Boolean(string="Sync Task ?", default=True)

    base_model = fields.Char(string="Model", default="res.partner, voip.phonecall", readonly=True)

    base_lead_status = fields.Char(required=True)

    lead_fields = fields.Many2many(
                    'base.sync.fields',
                    'lead_base_sync_fields_rel',
                    'lead_base_sync_id',
                    'lead_base_sync_fields_id',
                    string='Fields to Sync',
                    domain=[('model_of_field', '=', 'lead')])
    note_fields = fields.Many2many(
                    'base.sync.fields',
                    'note_base_sync_fields_rel',
                    'note_base_sync_id',
                    'note_base_sync_fields_id',
                    string='Fields to Sync',
                    domain=[('model_of_field', '=', 'note')])
    task_fields = fields.Many2many(
                    'base.sync.fields',
                    'task_base_sync_fields_rel',
                    'task_base_sync_id',
                    'task_base_sync_fields_id',
                    string='Fields to Sync',
                    domain=[('model_of_field', '=', 'task')])

    last_sync_date_time = fields.Datetime(readonly=True)
    active = fields.Boolean(default=True)
    email_code = fields.Char(required=True)

    _sql_constraints = [
        ('name_uniq', 'unique (base_lead_status)', """You can define only one rule per lead status."""),
    ]

    def get_salesperson(self):
        Params = self.env['ir.config_parameter']
        BaseSyncTodo = self.env['base.sync.todo']
        base_owner_id = Params.sudo().get_param('base_owner_id', default=False)
        # Find the salesperson from owner
        if base_owner_id:
            return int(base_owner_id)
        else:
            BaseSyncTodo.create({
                'name': 'Owner is not set in configuration, So please set it from base configuration.',
                'state': 'todo',
                'todo_type': 'other',
                'description': 'Please set the base owner , so whenever lead synced that user will assigned as salesperson.'
            })
        return False

    def get_company(self, company_name=False, company_list=False, data=None):
        BaseSyncLog = self.env['base.sync.log']

        user_id = data.get('salesperson', False)
        # Check from old one first
        match_found = False
        base_company_name = ''.join(i.lower() for i in company_name.split())
        for company in company_list:
            odoo_company_name = ''.join(i.lower() for i in company.name.split())
            if odoo_company_name == base_company_name:
                match_found = company
                break
        baseid = data.get('baseid', '')
        bsid = data.get('bsid', False)
        if match_found:
            BaseSyncLog.create({
                'name': baseid,
                'fields_updated': '',
                'log_type': 'lead',
                'status': 'duplicate',
                'description': 'Duplicate company found for lead so no need to create.',
                'base_sync_id': bsid,
                'odoo_contact_id': match_found[0].id,
                'odoo_call_visit_id': False,
            })
            return (match_found, company_list)
        else:
            # create new company
            address = data.get('address', False)

            vals = {
                'name': company_name,
                'is_company': True,
                'end_user': True,
                'user_id': user_id,
                'city': address and address.city or '',
                'street': address and address.line1 or '',
                'zip': address and address.postal_code or '',
            }

            if data.get('website', False):
                vals['website'] = data.get('website')

            country_id = False
            base_country = address.country
            if base_country:
                _country = self.env['res.country'].search([('base_country_name', '=', base_country)], limit=1)
                country_id = _country.id

            state_id = False
            base_state = address.state
            if base_state:
                states = self.env['res.country.state'].search([])
                state_match_found = False
                base_state_name = ''.join(i.lower() for i in base_state.split())
                for state in states:
                    odoo_state_name = ''.join(i.lower() for i in state.name.split())
                    if odoo_state_name == base_state_name:
                        state_match_found = state
                        break
                if state_match_found:
                    state_id = state_match_found.id
                else:
                    malasiya = self.env.ref('base.my')
                    vals_state = {
                        'name': base_state_name,
                        'country_id': country_id or malasiya.id,
                        'code': ''.join(i.upper() for i in base_state_name[:3].split())
                    }
                    state_id = self.env['res.country.state'].create(vals_state).id

            vals['country_id'] = country_id
            vals['state_id'] = state_id

            new_comapny = self.env['res.partner'].create(vals)
            BaseSyncLog.create({
                'name': baseid,
                'fields_updated': str(vals),
                'log_type': 'lead',
                'status': 'success',
                'description': 'New comapny created.',
                'base_sync_id': bsid,
                'odoo_contact_id': new_comapny.id,
                'odoo_call_visit_id': False,
            })
            company_list += new_comapny
            return (new_comapny, company_list)

    @api.multi
    def synclead(self):
        self.ensure_one()
        self.sync_leads(base_sync_ids=self.id)

    @api.model
    def sync_leads(self, base_sync_ids=False):
        res = self.authenticate()
        # If any error occur in execution then stop the execution
        if not res:
            return False

        # If manually click then sync only for that other wise for all.
        basesync = False
        if base_sync_ids:
            basesync = self.browse(base_sync_ids)
            if not basesync.active:
                raise ValidationError(_("This is not active rule, so please active it first."))
        else:
            basesync = self.search([('active', '=', True)])

        ResPartner = self.env['res.partner']
        PhoneCall = self.env['voip.phonecall']
        JobPosition = self.env['job.position']
        BaseLeadSource = self.env['base.lead.source']
        ResPartnerBaseGroup = self.env['base.lead.group']
        Params = self.env['ir.config_parameter']
        ResPartnerCategory = self.env['res.partner.category']
        ResPartnerTitle = self.env['res.partner.title']
        BaseSyncLog = self.env['base.sync.log']

        base_access_token = Params.sudo().get_param('base_access_token', default=False)
        client = basecrm.Client(access_token=base_access_token)

        company_list = self.env['res.partner'].search([('is_company', '=', True)])

        for bs in basesync:

            lead_fields_need_to_sync = bs.lead_fields.mapped('technical_name')
            note_fields_need_to_sync = bs.note_fields.mapped('technical_name')
            task_fields_need_to_sync = bs.task_fields.mapped('technical_name')

            last_sync_date = fields.Datetime.from_string(bs.last_sync_date_time)
            if bs.last_sync_date_time:
                last_sync_date = datetime.strptime(bs.last_sync_date_time,'%Y-%m-%d %H:%M:%S')

            lead_found = True
            page = 1
            connection_lost_update_time = True
            while lead_found:
                leads = []
                try:
                    leads = client.leads.list(status=bs.base_lead_status, page=page, per_page=50)
                except Exception:
                    BaseSyncLog.create({
                        'name': 'Leads',
                        'log_type': 'lead',
                        'status': 'failed',
                        'description': 'Due to internet connection lost server is not able to fetch the some lead.',
                        'base_sync_id': bs.id,
                        'odoo_contact_id': False,
                        'odoo_call_visit_id': False,
                    })
                    connection_lost_update_time = False

                page += 1
                if not leads:
                    lead_found = False

                for lead in leads:
                    print ("\n----->inside leads---->", lead)
                    # get last update datetime of lead
                    # base_update_date = fields.Datetime.from_string(lead.updated_at)
                    base_update_date = datetime.strptime(lead.updated_at,'%Y-%m-%dT%H:%M:%SZ')

                    # If last sync date time is greater than lead updated time then sync lead otherwise no need to sync.
                    lead_need_to_sync = True
                    if last_sync_date:
                        if last_sync_date > base_update_date:
                            lead_need_to_sync = False

                    odoo_contact = False
                    odoo_company = False
                    base_lead_id = lead.id
                    if lead_need_to_sync and bs.sync_lead:
                        base_lead_fname = lead.first_name
                        base_lead_lname = lead.last_name

                        base_lead_is_company = False
                        if not base_lead_lname and not base_lead_fname:
                            base_lead_is_company = True

                        base_lead_company = lead.organization_name
                        salesperson_id = self.get_salesperson()
                        data = {
                            'website': lead.website,
                            'salesperson': salesperson_id,
                            'address': lead.address,
                            'baseid': base_lead_id,
                            'bsid': bs.id,
                        }
                        duplicate = False
                        all_values = {}
                        if base_lead_is_company:
                            # Get the company id if not exist other wise create it.
                            odoo_contact, company_list = self.get_company(base_lead_company, company_list, data=data)
                            odoo_company = False
                        else:
                            # First of all get the company.
                            base_lead_name = lead.first_name + ' ' + lead.last_name
                            odoo_company = False
                            if base_lead_company:
                                odoo_company, company_list = self.get_company(base_lead_company, company_list, data=data)

                            base_small_lead_name = ''.join(i.lower() for i in base_lead_name.split())
                            if odoo_company:
                                domain = [('base_lead_ids', 'ilike', str(base_lead_id))]
                                match_based_on_base_lead_id = ResPartner.search(domain)
                                if match_based_on_base_lead_id:
                                    # Check is this duplicate or not
                                    odoo_contact = match_based_on_base_lead_id[0]
                                    Dupid = 'D'+str(base_lead_id)
                                    if Dupid in odoo_contact.base_lead_ids:
                                        duplicate = True
                                    else:
                                        temp_vals = {
                                            'name': base_lead_name,
                                            # 'end_user': True,
                                            'parent_id': odoo_company and odoo_company.id or False,
                                            'email': lead.email,
                                            'use_parent_address': False,
                                            'user_id': salesperson_id,
                                        }
                                        all_values.update(temp_vals)
                                        odoo_contact.write(temp_vals)
                                else:
                                    # Find contact under that
                                    match_contact = False
                                    for child in odoo_company.child_ids:
                                        child_name = ''.join(i.lower() for i in child.name.split())
                                        if lead.email:
                                            if child.email == lead.email:
                                                # check name now
                                                if child_name == base_small_lead_name:
                                                    match_contact = child
                                                    break
                                        else:
                                            # Based on name we have to search the record
                                            if child_name == base_small_lead_name:
                                                match_contact = child
                                                break
                                    if match_contact:
                                        odoo_contact = match_contact[0]
                                        duplicate = True
                                    else:
                                        # Create contact
                                        vals_contact = {
                                            'name': base_lead_name,
                                            # 'end_user': True,
                                            'parent_id': odoo_company and odoo_company.id or False,
                                            'email': lead.email,
                                            'use_parent_address': False,
                                            'user_id': salesperson_id,
                                        }
                                        all_values.update(vals_contact)
                                        odoo_contact = ResPartner.create(vals_contact)
                            else:
                                # Find contact will match
                                domain = [('base_lead_ids', 'ilike', str(base_lead_id))]
                                match_based_on_base_lead_id = ResPartner.search(domain)
                                if match_based_on_base_lead_id:
                                    odoo_contact = match_based_on_base_lead_id[0]
                                    Dupid = 'D'+str(base_lead_id)
                                    if Dupid in odoo_contact.base_lead_ids:
                                        duplicate = True
                                    else:
                                        temp_vals = {
                                            'name': base_lead_name,
                                            # 'end_user': True,
                                            'parent_id': False,
                                            'email': lead.email,
                                            'use_parent_address': False,
                                            'user_id': salesperson_id,
                                        }
                                        all_values.update(temp_vals)
                                        odoo_contact.write(temp_vals)
                                else:
                                    match_contact = False
                                    for contact in ResPartner.search[('is_company', '=', False)]:
                                        contact_name = ''.join(i.lower() for i in contact.name.split())
                                        if lead.email:
                                            if contact.email == lead.email:
                                                # check name now
                                                if contact_name == base_small_lead_name:
                                                    match_contact = contact
                                                    break
                                        else:
                                            if contact_name == base_small_lead_name:
                                                match_contact = contact
                                                break
                                    if match_contact:
                                        odoo_contact = match_contact[0]
                                        duplicate = True
                                    else:
                                        vals_contact = {
                                            'name': base_lead_name,
                                            # 'end_user': True,
                                            'email': lead.email,
                                            'use_parent_address': False,
                                            'user_id': salesperson_id,
                                        }
                                        all_values.update(vals_contact)
                                        odoo_contact = ResPartner.create(vals_contact)
                        # Now we have odoo contact we just need to update the values based on the fields.
                        vals = {}
                        if not duplicate:

                            vals['first_name'] = base_lead_fname
                            vals['last_name'] = base_lead_lname
                            if 'phone' in lead_fields_need_to_sync:
                                vals['phone'] = lead.phone or ''

                            if 'mobile' in lead_fields_need_to_sync:
                                vals['mobile'] = lead.mobile or ''

                            if 'line1' in lead_fields_need_to_sync:
                                vals['street'] = lead.address.line1 or ''

                            if 'city' in lead_fields_need_to_sync:
                                vals['city'] = lead.address.city or ''

                            if 'postal_code' in lead_fields_need_to_sync:
                                vals['zip'] = lead.address.postal_code or ''

                            if 'website' in lead_fields_need_to_sync:
                                vals['website'] = lead.website or ''

                            if 'linkedin' in lead_fields_need_to_sync:
                                vals['linkedin_url'] = lead.linkedin or ''

                            if 'title' in lead_fields_need_to_sync:
                                lead_title = lead.title
                                if lead_title:
                                    jobpositions = JobPosition.search([])
                                    jp_match_found = False
                                    base_job_title = ''.join(i.lower() for i in lead_title.split())
                                    for jobposition in jobpositions:
                                        odoo_jobposition = ''.join(i.lower() for i in jobposition.name.split())
                                        if odoo_jobposition == base_job_title:
                                            jp_match_found = jobposition
                                            break
                                    if jp_match_found:
                                        vals['job_position_id'] = jp_match_found.id
                                    else:
                                        vals['job_position_id'] = JobPosition.create({'name': lead_title}).id

                            if 'source' in lead_fields_need_to_sync:
                                if lead.source_id:
                                    sources = BaseLeadSource.search([('base_lead_source_id', '=', lead.source_id)])
                                    if sources:
                                        vals['base_lead_source_id'] = sources[0].id

                            if 'add_to_sea' in lead_fields_need_to_sync:
                                addtosea = lead.custom_fields.get('Add to SEA', False)
                                if addtosea:
                                    for ats in addtosea:
                                        if ats == 'Ja':
                                            vals['opt_out'] = True
                                        elif ats == 'Nee':
                                            vals['opt_out'] = False
                                        break

                            match_ids = []
                            if 'group' in lead_fields_need_to_sync:
                                # if lead.custom_fields.get('GROUP'):
                                #     grp = lead.custom_fields.get('GROUP')
                                #     match = BaseLeadGroup.search([('name', '=', grp)])
                                #     if match:
                                #         vals['base_lead_group_id'] = match[0].id
                                #     else:
                                #         newGroup = BaseLeadGroup.create({'name': grp})
                                #         vals['base_lead_group_id'] = newGroup.id
                                match_group = []
                                if lead.custom_fields.get('GROUP'):
                                    for grp in lead.custom_fields.get('GROUP'):
                                        matchgrp = ResPartnerBaseGroup.search([('name', '=', grp)])
                                        if matchgrp:
                                            match_group.append(matchgrp[0].id)
                                        else:
                                            matchgrp = ResPartnerBaseGroup.create({'name': grp})
                                            match_group.append(matchgrp.id)

                                match_group_ids = list(set(match_group))
                                vals['base_group_ids'] = [(6, 0, match_group_ids)]

                            if 'tags' in lead_fields_need_to_sync:
                                if lead.tags:
                                    for tag in lead.tags:
                                        match = ResPartnerCategory.search([('name', '=', tag)])
                                        if match:
                                            match_ids.append(match[0].id)
                                        else:
                                            match = ResPartnerCategory.create({'name': tag, 'active': True})
                                            match_ids.append(match.id)

                            match_ids = list(set(match_ids))
                            vals['category_id'] = [(6, 0, match_ids)]

                            if 'aanhef' in lead_fields_need_to_sync:
                                title = lead.custom_fields.get('Aanhef')
                                if title:
                                    matchtitle = ResPartnerTitle.search([('name', '=', title)])
                                    if matchtitle:
                                        vals['title'] = matchtitle[0].id
                                    else:
                                        vals['title'] = ResPartnerTitle.create({'name': title}).id
                                else:
                                    vals['title'] = False

                            if 'country' in lead_fields_need_to_sync:
                                country_id = False
                                base_country = lead.address.country
                                if base_country:
                                    countries = self.env['res.country'].search([('base_country_name', '=', base_country)])
                                    if countries:
                                        country_id = countries[0].id

                                vals['country_id'] = country_id

                            if 'state' in lead_fields_need_to_sync:
                                state_id = False
                                base_state = lead.address.state
                                if base_state:
                                    states = self.env['res.country.state'].search([])
                                    state_match_found = False
                                    base_state_name = ''.join(i.lower() for i in base_state.split())
                                    for state in states:
                                        odoo_state_name = ''.join(i.lower() for i in state.name.split())
                                        if odoo_state_name == base_state_name:
                                            state_match_found = state
                                            break
                                    if state_match_found:
                                        state_id = state_match_found.id
                                    else:
                                        malasiya = self.env.ref('base.my')
                                        vals_state = {
                                            'name': base_state_name,
                                            'country_id': country_id or malasiya.id,
                                            'code': ''.join(i.upper() for i in base_state_name[:3].split())
                                        }
                                        state_id = self.env['res.country.state'].create(vals_state).id
                                vals['state_id'] = state_id

                        if odoo_contact.base_lead_ids:
                            odoo_baselead_id = odoo_contact.base_lead_ids
                            if str(base_lead_id) not in odoo_baselead_id:
                                vals['base_lead_ids'] = odoo_contact.base_lead_ids + ',D' + str(base_lead_id)
                        else:
                            if duplicate:
                                vals['base_lead_ids'] = 'D' + str(base_lead_id)
                            else:
                                vals['base_lead_ids'] = str(base_lead_id)

                        # end field mapping
                        print ("====>", vals)
                        odoo_contact.write(vals)
                        all_values.update(vals)
                        if not duplicate:
                            BaseSyncLog.create({
                                'name': base_lead_id,
                                'fields_updated': str(all_values),
                                'log_type': 'lead',
                                'status': 'success',
                                'description': 'Sync Sucessfully',
                                'base_sync_id': bs.id,
                                'odoo_contact_id': odoo_contact.id,
                                'odoo_call_visit_id': False,
                            })
                        else:
                            BaseSyncLog.create({
                                'name': base_lead_id,
                                'fields_updated': str(all_values),
                                'log_type': 'lead',
                                'status': 'duplicate',
                                'description': 'Due to duplicate , not synced.',
                                'base_sync_id': bs.id,
                                'odoo_contact_id': odoo_contact.id,
                                'odoo_call_visit_id': False,
                            })
                    else:
                        BaseSyncLog.create({
                            'name': base_lead_id,
                            'fields_updated': '',
                            'log_type': 'lead',
                            'status': 'success',
                            'description': 'Not sync beacuse already synced or Lead Sync is False.',
                            'base_sync_id': bs.id,
                            'odoo_contact_id': False,
                            'odoo_call_visit_id': False,
                        })

                    # Here we need to find the odoo_contact which match to lead id
                    match_odoo_contact_base_lead = ResPartner.search([('base_lead_ids', 'ilike', str(base_lead_id))])
                    connection_lost_lead_update = True
                    # Sync the notes
                    if bs.sync_note:
                        note_page = 1
                        notes_found = True

                        while notes_found:
                            notes = []
                            print ("\n=====Iwhile notes=====>")
                            try:
                                notes = client.notes.list(resource_id=base_lead_id, resource_type='lead', page=note_page, per_page=50)
                            except Exception:
                                BaseSyncLog.create({
                                    'name': str(base_lead_id),
                                    'log_type': 'lead',
                                    'status': 'failed',
                                    'description': 'Due to internet connection lost server is not able to fetch note for this lead.',
                                    'base_sync_id': bs.id,
                                    'odoo_contact_id': False,
                                    'odoo_call_visit_id': False,
                                })
                                connection_lost_update_time = False
                                connection_lost_lead_update = False

                            note_page += 1
                            if not notes:
                                notes_found = False

                            for note in notes:
                                base_note_id = note.id
                                if not match_odoo_contact_base_lead:
                                    BaseSyncLog.create({
                                        'name': base_note_id,
                                        'fields_updated': '',
                                        'log_type': 'note',
                                        'status': 'success',
                                        'description': 'This Note is not synced due to NO Lead EXIST where id = ' + str(base_lead_id),
                                        'base_sync_id': bs.id,
                                        'odoo_contact_id': False,
                                        'odoo_call_visit_id': False,
                                    })
                                else:
                                    # get last update datetime of note
                                    notebase_update_date = datetime.strptime(note.updated_at, '%Y-%m-%dT%H:%M:%SZ')

                                    note_need_to_sync = True
                                    if last_sync_date:
                                        if last_sync_date > notebase_update_date:
                                            note_need_to_sync = False
                                    matchnote = PhoneCall.search([('base_note_task_id', '=', base_note_id), ('base_sync_type', 'in', ['note','email'])])
                                    if note_need_to_sync or not matchnote:

                                        # Check its email or note
                                        content = note.content
                                        first_6_letters = content[:6]
                                        content30 = content[:30]
                                        base_sync_type = 'note'
                                        if first_6_letters == bs.email_code:
                                            base_sync_type = 'email'
                                            new_content = content.replace(bs.email_code, '')
                                            content30 = new_content[:30]

                                        vals_note = {
                                            'name': content30,
                                            'base_note_task_id': base_note_id,
                                            'base_sync_type': base_sync_type,
                                            'partner_ids': [(6, 0, match_odoo_contact_base_lead and match_odoo_contact_base_lead.ids or [])],
                                            'note': content,
                                        }

                                        if 'content' in note_fields_need_to_sync:
                                            vals_note['description'] = content.replace(bs.email_code, '')

                                        if 'create_date' in note_fields_need_to_sync:
                                            vals_note['date'] = datetime.strptime(note.created_at, '%Y-%m-%dT%H:%M:%SZ')

                                        if matchnote:
                                            matchnote.write(vals_note)
                                            BaseSyncLog.create({
                                                'name': base_note_id,
                                                'fields_updated': str(vals_note),
                                                'log_type': 'note',
                                                'status': 'success',
                                                'description': 'Sync Update successfully',
                                                'base_sync_id': bs.id,
                                                'odoo_contact_id': False,
                                                'odoo_call_visit_id': matchnote[0].id,
                                            })
                                        else:
                                            matchnote = PhoneCall.create(vals_note)
                                            BaseSyncLog.create({
                                                'name': base_note_id,
                                                'fields_updated': str(vals_note),
                                                'log_type': 'note',
                                                'status': 'success',
                                                'description': 'Sync successfully',
                                                'base_sync_id': bs.id,
                                                'odoo_contact_id': False,
                                                'odoo_call_visit_id': matchnote.id,
                                            })
                                    else:
                                        BaseSyncLog.create({
                                            'name': base_note_id,
                                            'fields_updated': '',
                                            'log_type': 'note',
                                            'status': 'success',
                                            'description': 'Not sync beacuse already synced',
                                            'base_sync_id': bs.id,
                                            'odoo_contact_id': False,
                                            'odoo_call_visit_id': False,
                                        })

                    # Sync the tasks
                    if bs.sync_task:
                        task_page = 1
                        task_found = True

                        while task_found:
                            print ("\n=====while task====>")
                            tasks = []
                            try:
                                tasks = client.tasks.list(resource_id=base_lead_id, resource_type='lead', page=task_page, per_page=50)
                            except Exception:
                                BaseSyncLog.create({
                                    'name': str(base_lead_id),
                                    'log_type': 'lead',
                                    'status': 'failed',
                                    'description': 'Due to internet connection lost server is not able fetch task for this lead.',
                                    'base_sync_id': bs.id,
                                    'odoo_contact_id': False,
                                    'odoo_call_visit_id': False,
                                })
                                connection_lost_update_time = False
                                connection_lost_lead_update = False

                            task_page += 1
                            if not tasks:
                                task_found = False

                            for task in tasks:
                                base_task_id = task.id
                                print ("\n=====INSIDE task=====>", task)
                                if not match_odoo_contact_base_lead:
                                    BaseSyncLog.create({
                                        'name': base_task_id,
                                        'fields_updated': '',
                                        'log_type': 'task',
                                        'status': 'success',
                                        'description': 'This Task are not synced due to NO Lead EXIST where id = '+ str(base_lead_id),
                                        'base_sync_id': bs.id,
                                        'odoo_contact_id': False,
                                        'odoo_call_visit_id': False,
                                    })
                                else:
                                    # get last update datetime of note
                                    taskbase_update_date = datetime.strptime(task.updated_at, '%Y-%m-%dT%H:%M:%SZ')

                                    task_need_to_sync = True
                                    if last_sync_date:
                                        if last_sync_date > taskbase_update_date:
                                            task_need_to_sync = False

                                    matchtask = PhoneCall.search([('base_note_task_id', '=', base_task_id), ('base_sync_type', '=', 'task')])

                                    if task_need_to_sync or not matchtask:
                                        content = task.content
                                        content30 = content[:30]
                                        vals_task = {
                                            'name': content30,
                                            'base_note_task_id': base_task_id,
                                            'base_sync_type': 'task',
                                            'partner_ids': [(6, 0, match_odoo_contact_base_lead and match_odoo_contact_base_lead.ids or [])],
                                            'note': content,
                                        }

                                        if 'due_date' in task_fields_need_to_sync:
                                            if task.due_date:
                                                due_date = datetime.strptime(task.due_date, '%Y-%m-%dT%H:%M:%SZ')
                                                vals_task['next_action_date'] = due_date.date()

                                        if matchtask:
                                            matchtask.write(vals_task)
                                            BaseSyncLog.create({
                                                'name': base_task_id,
                                                'fields_updated': str(vals_task),
                                                'log_type': 'task',
                                                'status': 'success',
                                                'description': 'Sync Update successfully',
                                                'base_sync_id': bs.id,
                                                'odoo_contact_id': False,
                                                'odoo_call_visit_id': matchtask[0].id,
                                            })
                                        else:
                                            matchtask = PhoneCall.create(vals_task)
                                            BaseSyncLog.create({
                                                'name': base_task_id,
                                                'fields_updated': str(vals_task),
                                                'log_type': 'task',
                                                'status': 'success',
                                                'description': 'Sync successfully',
                                                'base_sync_id': bs.id,
                                                'odoo_contact_id': False,
                                                'odoo_call_visit_id': matchtask.id,
                                            })
                                    else:
                                        BaseSyncLog.create({
                                            'name': base_task_id,
                                            'fields_updated': '',
                                            'log_type': 'task',
                                            'status': 'success',
                                            'description': 'Not sync beacuse already synced',
                                            'base_sync_id': bs.id,
                                            'odoo_contact_id': False,
                                            'odoo_call_visit_id': False,
                                        })

                    # At last change status of lead to done.
                    if connection_lost_lead_update:
                        lead.status = 'Working'
                        client.leads.update(lead.id, lead)
            if connection_lost_update_time:
                bs.write({'last_sync_date_time': fields.Datetime.now()})

    def sync_lead_source(self):
        Params = self.env['ir.config_parameter']
        base_access_token = Params.sudo().get_param('base_access_token', default=False)

        client = basecrm.Client(access_token=base_access_token)

        source_page = 1
        source_found = True

        BaseLeadSource = self.env['base.lead.source']
        while source_found:
            sources = client.lead_sources.list(page=source_page, per_page=50)
            source_page += 1
            if not sources:
                source_found = False

            for source in sources:
                base_source_id = source.id

                match = BaseLeadSource.search([('base_lead_source_id', '=', base_source_id)])
                if match:
                    match.write({'name': source.name})
                else:
                    BaseLeadSource.create({
                        'name': source.name,
                        'base_lead_source_id': base_source_id
                    })

    def authenticate(self):
        BaseSyncTodo = self.env['base.sync.todo']
        Params = self.env['ir.config_parameter']
        base_access_token = Params.sudo().get_param('base_access_token', default=False)
        base_sync_active = Params.sudo().get_param('base_sync_active', default=False)

        # Basic check that its active or not and also access token is provided or not.
        if not base_sync_active or not base_access_token:
            BaseSyncTodo.create({
                'name': 'Either its not active or Access Token is missing',
                'state': 'todo',
                'todo_type': 'other',
                'description': 'Either its not active or Access Token is missing , You should configure it by going to Base Configuration.'
            })
            return False
        try:
            # Instantiate a client.
            client = basecrm.Client(access_token=base_access_token)
            # stages = client.stages.list()
            client.stages.list()
            # Sync the sources
            self.sync_lead_source()

            return True

        except basecrm.ConfigurationError as e:
            #  Invalid client configuration option
            BaseSyncTodo.create({
                'name': 'Configuration Error, Please correct it.',
                'state': 'todo',
                'todo_type': 'other',
                'description': e.message
            })
            return False

        except basecrm.ResourceError as e:
            # Resource related error
            error = 'Http status = ' + str(e.http_status)
            error += '\nRequest ID = ' + str(e.logref)

            for error in e.errors:
                error += '\nfield = ' + str(error.field)
                error += ', code = ' + str(error.code)
                error += ', message = ' + str(error.message)
                error += ', details = ' + str(error.details)

            BaseSyncTodo.create({
                'name': 'Need to check with developer.',
                'state': 'todo',
                'todo_type': 'other',
                'description': error
            })
            return False
        except basecrm.RequestError as e:
            # Invalid query parameters, authentication error etc.
            BaseSyncTodo.create({
                'name': 'Required access token is missing, malformed, expired, or invalid.',
                'state': 'todo',
                'todo_type': 'other',
                'description': 'Please check the access token bcz may it is expired or not having required rights.'
            })
            return False
        except Exception as e:
            # Other kind of exceptioni, probably connectivity related
            BaseSyncTodo.create({
                'name': 'Make sure connection is working.',
                'state': 'todo',
                'todo_type': 'other',
                'description': str(e)
            })
            return False


class BaseSyncFields(models.Model):
    _name = 'base.sync.fields'

    name = fields.Char(readonly=True, string='Base Field', required=True)
    odoo_field_name = fields.Char(readonly=True, string="Odoo Field")
    technical_name = fields.Char(readonly=True)
    model_of_field = fields.Selection(
        [('lead', 'Lead'), ('note', 'Note'), ('task', 'Task')],
        readonly=True)
    is_customise_field = fields.Boolean(readonly=True)


class BaseLeadSource(models.Model):
    _name = 'base.lead.source'

    name = fields.Char()
    base_lead_source_id = fields.Char()


class BaseLeadGroup(models.Model):
    _name = 'base.lead.group'

    name = fields.Char()
