from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError
from odoo.addons.queue_job.job import job
import requests
import logging
import json

_logger = logging.getLogger(__name__)


class WebshopResPartnerTitle(models.Model):
    _inherit = 'res.partner.title'

    webshop_name = fields.Selection([('male', 'Male'), ('female', 'Female')],
                                    string='Webshop Gender')


class WebshopResPartner(models.Model):
    _inherit = 'res.partner'

    webshop_checkbox = fields.Boolean(string='Webshop')
    webshop_import_key = fields.Char(string="Webshop Import Key", readonly=1)

    def set_customer_sync_cron_active(self):
        customer_sync_cron = self.env.ref('markant_webshop.ir_cron_markant_webshop_customer_sync')

        # Get midnight time for today
        today = date.today() + timedelta(days=1)
        midnight = datetime.combine(today, datetime.min.time())

        if customer_sync_cron.active is False:
            customer_sync_cron.active = True
            customer_sync_cron.numbercall = 1
            customer_sync_cron.nextcall = midnight

        return True

    def set_address_sync_cron_active(self):
        address_sync_cron = self.env.ref('markant_webshop.ir_cron_markant_webshop_address_sync')

        # Get midnight time for today
        today = date.today() + timedelta(days=1)
        midnight = datetime.combine(today, datetime.min.time())

        if address_sync_cron.active is False:
            address_sync_cron.active = True
            address_sync_cron.numbercall = 1
            address_sync_cron.nextcall = midnight

        return True

    def set_user_sync_cron_active(self):
        user_sync_cron = self.env.ref('markant_webshop.ir_cron_markant_webshop_user_sync')

        # Get midnight time for today
        today = date.today() + timedelta(days=1)
        midnight = datetime.combine(today, datetime.min.time())

        if user_sync_cron.active is False:
            user_sync_cron.active = True
            user_sync_cron.numbercall = 1
            user_sync_cron.nextcall = midnight

        return True

    # Sync Webshop Customer
    @api.model
    def _sync_webshop_customer(self):
        all_customer = self.search([('active', '=', True),
                                    ('webshop_checkbox', '=', True),
                                    ('sale_warn', '!=', 'block'),
                                    ('parent_id', '=', False),
                                    '|',
                                    ('customer', '=', True),
                                    ('end_user', '=', True)])

        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)], limit=1)
        retries = 0
        if api_config:
            retries = api_config.api_attempts

        for cust in all_customer:
            cust.with_delay(max_retries=retries).sync_webshop_customer_api()

    @api.multi
    @job
    def sync_webshop_customer_api(self):
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)], limit=1)
        if api_config and api_config.token and api_config.api_url and \
                api_config.customer_end_point and api_config.api_company:
            headers = {'Authorization': 'Token ' + api_config.token,
                       'Content-Type': 'application/json'}
            customer_link = api_config.api_url + api_config.customer_end_point
            for partner in self:
                customer_params = {
                    'key': partner.webshop_import_key,
                    'code': partner.webshop_import_key,
                    'name': partner.name,
                    'active': partner.active,
                }

                # Vat number
                if partner.vat:
                    customer_params.update({'vat_numbers': [partner.vat]})
                else:
                    customer_params.update({'vat_numbers': []})

                # Language
                lang = []
                if partner.lang:
                    lang.append({'company': api_config.api_company,
                                 'value': partner.lang})
                    customer_params.update({'languages': lang})

                # blocked
                if partner.sale_warn != 'block':
                    customer_params.update({'blocked': False})
                else:
                    customer_params.update({'blocked': True})

                # Pricelist
                price = []
                if partner.property_product_pricelist:
                    # partner.property_product_pricelist. \
                    #     webshop_api_pricelist(method='write')
                    price.append(
                        str(partner.property_product_pricelist.id))
                    customer_params.update(
                        {'price_lists': price})
                else:
                    customer_params.update({'price_lists': []})

                # Payment Term
                payment_term = []
                if partner.property_payment_term_id:
                    payment_term.append({'company': api_config.api_company,
                                         'value': str(
                                             partner.property_payment_term_id.id)})
                    customer_params.update(
                        {'payment_terms': payment_term})
                else:
                    customer_params.update({'payment_terms': []})

                # Tax Rules
                tax_rule = []
                if partner.property_account_position_id:
                    tax_rule.append({'company': api_config.api_company,
                                     'value': str(
                                         partner.property_account_position_id.id)})
                    customer_params.update(
                        {'tax_rules': tax_rule})
                else:
                    customer_params.update({'tax_rules': []})

                time = datetime.now()
                customer_api_link = customer_link
                customer_data = json.dumps(customer_params)
                customer_put_link = customer_api_link + \
                                    str(partner.webshop_import_key) + \
                                    '/'
                customer_api = requests.put(url=customer_put_link,
                                            data=customer_data,
                                            headers=headers,
                                            verify=False)
                # Technical API Log
                tech_customer_log = partner.sudo().create_technical_log_api(
                    request_method='PUT',
                    request_type='Customer',
                    request_url=customer_put_link,
                    request_headers=headers,
                    request_response=customer_api.content,
                    request_uid=self.env.uid,
                    request_status=customer_api.status_code,
                    request_time=time,
                    request_arguments=customer_api,
                    request_direction='outgoing')

                # Pricelist Log
                if customer_api.status_code in (200, 201, 202):
                    status = 'successful'
                else:
                    status = 'failed'
                customer_log = {
                    'customer_name': partner.id,
                    'customer_id': partner.id,
                    'webshop_import_key': partner.webshop_import_key,
                    'customer_email': partner.email,
                    'type': 'PUT',
                    'sync_method': 'real_time',
                    'sync_time': time,
                    'sync_status': status,
                    'response_body': customer_api.content,
                }
                self.env['webshop.customer.api.log'].sudo().create(
                    customer_log)

                # Send email notification
                if customer_api.status_code not in (200, 201, 202) \
                        and tech_customer_log:
                    for user in self.env['webshop.fail.notification'] \
                            .sudo().search([]):
                        if user.email:
                            tech_customer_log.sudo().action_send_fail_notification_mail \
                                (lang=user.user_id.partner_id.lang,
                                 email=user.email,
                                 user=user.user_id.name,
                                 cusid=partner.id,
                                 wik=partner.webshop_import_key,
                                 cusname=partner.name,
                                 synctime=time,
                                 response=customer_api.content,
                                 api_name='Sync Customer Api')
                _logger.info('CUSTOMER PUT ---------------> %s',
                             customer_api)
                _logger.info(
                    'CUSTOMER PUT RESULT ---------------> %s',
                    customer_api.content)

        return True

    # Sync Webshop Customer
    @api.model
    def _sync_webshop_address(self):
        all_address = self.search([('type', 'in', ('delivery', 'invoice')),
                                   ('active', '=', True),
                                   ('sale_warn', '!=', 'block'),
                                   ('parent_id', '!=', False),
                                   '|',
                                   ('customer', '=', True),
                                   ('end_user', '=', True),
                                   ('webshop_checkbox', '=', True)])

        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)], limit=1)
        retries = 0
        if api_config:
            retries = api_config.api_attempts

        for address in all_address:
            address.with_delay(max_retries=retries).sync_webshop_address_api()
        return True

    @api.multi
    @job
    def sync_webshop_address_api(self):
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)], limit=1)
        if api_config and api_config.token and api_config.api_url and \
                api_config.address_end_point:
            headers = {'Authorization': 'Token ' + api_config.token,
                       'Content-Type': 'application/json'}
            address_link = api_config.api_url + api_config.address_end_point
            for partner in self:
                if partner.parent_id.webshop_checkbox:
                    delivery = False
                    default_delivery = False
                    if partner.type == 'delivery':
                        delivery = True
                        if partner.is_default_address:
                            default_delivery = True

                    invoice = False
                    default_invoice = False
                    if partner.type == 'invoice':
                        invoice = True
                        if partner.is_default_address:
                            default_invoice = True

                    default_log = ''
                    if default_delivery:
                        default_log = 'Default Delivery Address'
                    elif default_invoice:
                        default_log = 'Default Invoice Address'

                    if partner.street_name and not partner.street2:
                        street = partner.street_name
                    elif partner.street2 and not partner.street_name:
                        street = partner.street2
                    elif partner.street2 and partner.street_name:
                        street = partner.street_name  + ', ' + partner.street2
                    else:
                        street = ''

                    address_params = {
                        'key': partner.webshop_import_key,
                        'customer': partner.parent_id.webshop_import_key,
                        'name': partner.name,
                        'active': partner.active,
                        'street': street or None,
                        'house_number': partner.street_number or None,
                        'house_number_addition': partner.street_number2 or None,
                        'zip': partner.zip or None,
                        'city': partner.city or None,
                        'country': partner.country_id.code,
                        'phone': partner.phone or None,
                        'delivery': delivery,
                        'invoice': invoice,
                        'default_delivery': default_delivery,
                        'default_invoice': default_invoice,
                    }

                    time = datetime.now()
                    address_api_link = address_link
                    address_data = json.dumps(address_params)
                    address_put_link = address_api_link + \
                                       str(partner.webshop_import_key) + \
                                       '/'
                    address_api = requests.put(url=address_put_link,
                                                data=address_data,
                                                headers=headers,
                                                verify=False)
                    # Technical API Log
                    tech_address_log = partner.sudo().create_technical_log_api(
                        request_method='PUT',
                        request_type='Address',
                        request_url=address_put_link,
                        request_headers=headers,
                        request_response=address_api.content,
                        request_uid=self.env.uid,
                        request_status=address_api.status_code,
                        request_time=time,
                        request_arguments=address_api,
                        request_direction='outgoing')

                    # Address Log
                    if address_api.status_code in (200, 201, 202):
                        status = 'successful'
                    else:
                        status = 'failed'
                    address_log = {
                        'address_name': partner.id,
                        'parent_address_name': partner.id,
                        'address_id': partner.id,
                        'webshop_import_key': partner.webshop_import_key,
                        'default_address': default_log,
                        'type': 'PUT',
                        'sync_method': 'real_time',
                        'sync_time': time,
                        'sync_status': status,
                        'response_body': address_api.content,
                    }
                    self.env['webshop.address.api.log'].sudo().create(
                        address_log)

                    # Send email notification
                    if address_api.status_code not in (200, 201, 202) \
                            and tech_address_log:
                        for user in self.env['webshop.fail.notification'] \
                                .sudo().search([]):
                            if user.email:
                                tech_address_log.sudo().action_send_fail_notification_mail \
                                    (lang=user.user_id.partner_id.lang,
                                     email=user.email,
                                     user=user.user_id.name,
                                     aid=partner.id,
                                     wik=partner.webshop_import_key,
                                     aname=partner.name,
                                     atype=partner.type,
                                     aparent=partner.parent_id.name,
                                     synctime=time,
                                     response=address_api.content,
                                     api_name='Sync Address Api')
                    _logger.info('ADDRESS PUT ---------------> %s',
                                 address_api)
                    _logger.info(
                        'ADDRESS PUT RESULT ---------------> %s',
                        address_api.content)

                else:
                    address_put_link = address_link + \
                                       str(partner.webshop_import_key) + \
                                       '/'
                    # Technical API Log
                    tech_user_log = partner.sudo().create_technical_log_api(
                        request_method='PUT',
                        request_type='USER',
                        request_url=address_put_link,
                        request_headers=headers,
                        request_response='Email, Fist Name and Last Name are required fields! ',
                        request_uid=self.env.uid,
                        request_status='FAILED',
                        request_time=False,
                        request_arguments=False,
                        request_direction='outgoing')
                    address_log = {
                        'address_name': partner.id,
                        'parent_address_name': partner.id,
                        'address_id': partner.id,
                        'webshop_import_key': partner.webshop_import_key,
                        'default_address': False,
                        'type': 'PUT',
                        'sync_method': 'real_time',
                        'sync_time': False,
                        'sync_status': 'failed',
                        'response_body': 'Parent Webshop Checkbox must be TRUE!',
                    }
                    self.env['webshop.address.api.log'].sudo().create(
                        address_log)

                    # Send email notification
                    for notif_user in self.env['webshop.fail.notification'] \
                            .sudo().search([]):
                        if notif_user.email:
                            tech_user_log.sudo().action_send_fail_notification_mail \
                                (lang=notif_user.user_id.partner_id.lang,
                                 email=notif_user.email,
                                 user=notif_user.user_id.name,
                                 cname=partner.name,
                                 cid=partner.id,
                                 pname=partner.parent_id.name,
                                 pid=partner.parent_id.id,
                                 synctime=False,
                                 response='Parent Webshop Checkbox must be TRUE! ',
                                 api_name='Sync Address Api')

        return True

    # Sync Webshop User
    @api.model
    def _sync_webshop_user(self):
        all_user = self.search([('type', '=', 'contact'),
                                ('active', '=', True),
                                ('sale_warn', '!=', 'block'),
                                ('parent_id', '!=', False),
                                '|',
                                ('customer', '=', True),
                                ('end_user', '=', True),
                                ('webshop_checkbox', '=', True)])
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)], limit=1)
        retries = 0
        if api_config:
            retries = api_config.api_attempts

        for user in all_user:
            user.with_delay(max_retries=retries).sync_webshop_user_api()

    @api.multi
    @job
    def sync_webshop_user_api(self):
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)], limit=1)
        if api_config and api_config.token and api_config.api_url and \
                api_config.user_end_point:
            headers = {'Authorization': 'Token ' + api_config.token,
                       'Content-Type': 'application/json'}
            user_link = api_config.api_url + api_config.user_end_point

            for user in self:
                if user.email and user.first_name and user.last_name and \
                        user.parent_id.webshop_checkbox:
                    authorized_customers = []
                    if user.parent_id:
                        authorized_customers.append(
                            user.parent_id.webshop_import_key)

                    user_params = {
                        'id': user.webshop_import_key,
                        'key': user.webshop_import_key,
                        'active': user.active,
                        'language': user.lang,
                        'webshop': api_config.default_web_id or '1',
                        'role': api_config.default_role_id or '1',
                        'authorised_customers': authorized_customers
                    }

                    if user.first_name:
                        user_params.update({'first_name': user.first_name})

                    if user.last_name:
                        user_params.update({'last_name': user.last_name})

                    if user.email:
                        user_params.update({'email': user.email})

                    if user.phone:
                        user_params.update({'phone': user.phone})

                    if user.mobile:
                        user_params.update({'mobile': user.mobile})

                    if user.title:
                        user_params.update({'gender': user.title.name})

                    time = datetime.now()
                    user_api_link = user_link
                    user_data = json.dumps(user_params)
                    user_put_link = user_api_link + \
                                    str(user.webshop_import_key) + \
                                    '/'
                    user_api = requests.put(url=user_put_link,
                                            data=user_data,
                                            headers=headers,
                                            verify=False)
                    # Technical API Log
                    tech_user_log = user.sudo().create_technical_log_api(
                        request_method='PUT',
                        request_type='USER',
                        request_url=user_put_link,
                        request_headers=headers,
                        request_response=user_api.content,
                        request_uid=self.env.uid,
                        request_status=user_api.status_code,
                        request_time=time,
                        request_arguments=user_api,
                        request_direction='outgoing')

                    # User Log
                    if user_api.status_code in (200, 201, 202):
                        status = 'successful'
                    else:
                        status = 'failed'
                    user_log = {
                        'user_name': user.id,
                        'user_id': user.parent_id.id,
                        'parent_company_name': user.parent_id.id,
                        'parent_company_id': user.parent_id.id,
                        'parent_webshop_import_key': user.parent_id.webshop_import_key,
                        'type': 'PUT',
                        'sync_method': 'real_time',
                        'sync_time': time,
                        'sync_status': status,
                        'response_body': user_api.content,
                    }
                    self.env['webshop.user.api.log'].sudo().create(user_log)

                    # Send email notification
                    if user_api.status_code not in (200, 201, 202) \
                            and tech_user_log:
                        for notif_user in self.env['webshop.fail.notification'] \
                                .sudo().search([]):
                            if user.email:
                                tech_user_log.sudo().action_send_fail_notification_mail \
                                    (lang=notif_user.user_id.partner_id.lang,
                                     email=notif_user.email,
                                     user=notif_user.user_id.name,
                                     cname=user.name,
                                     cid=user.id,
                                     pname=user.parent_id.name,
                                     pid=user.parent_id.id,
                                     synctime=time,
                                     response=user_api.content,
                                     api_name='Sync User Api')
                    _logger.info('USER PUT ---------------> %s',
                                 user_api)
                    _logger.info(
                        'USER PUT RESULT ---------------> %s',
                        user_api.content)
                else:
                    user_put_link = user_link + \
                                    str(user.webshop_import_key) + \
                                    '/'
                    # Technical API Log
                    tech_user_log = user.create_technical_log_api(
                        request_method='PUT',
                        request_type='USER',
                        request_url=user_put_link,
                        request_headers=headers,
                        request_response='Email, Fist Name and Last Name are required fields and Parent Webshop Checkbox must be TRUE! ',
                        request_uid=self.env.uid,
                        request_status='FAILED',
                        request_time=False,
                        request_arguments=False,
                        request_direction='outgoing')
                    user_log = {
                        'user_name': user.id,
                        'user_id': user.parent_id.id,
                        'parent_company_name': user.parent_id.id,
                        'parent_company_id': user.parent_id.id,
                        'parent_webshop_import_key': user.parent_id.webshop_import_key,
                        'type': 'PUT',
                        'sync_method': 'real_time',
                        'sync_time': False,
                        'sync_status': 'failed',
                        'response_body': 'Email, Fist Name and Last Name are required fields and Parent Webshop Checkbox must be TRUE! ',
                    }
                    self.env['webshop.user.api.log'].sudo().create(user_log)

                    # Send email notification
                    for notif_user in self.env['webshop.fail.notification'] \
                            .sudo().search([]):
                        if user.email:
                            tech_user_log.sudo().action_send_fail_notification_mail \
                                (lang=notif_user.user_id.partner_id.lang,
                                 email=notif_user.email,
                                 user=notif_user.user_id.name,
                                 cname=user.name,
                                 cid=user.id,
                                 pname=user.parent_id.name,
                                 pid=user.parent_id.id,
                                 synctime=False,
                                 response='Email, First Name and Last Name are required Fields! ',
                                 api_name='Sync User Api')
        return True

    def unlink(self):
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)])

        if api_config and api_config.token and api_config.api_url and \
                api_config.address_end_point:
            address_link = api_config.api_url + api_config.address_end_point
            headers = {'Authorization': 'Token ' + api_config.token,
                       'Content-Type': 'application/json'}

            for partner in self:
                address_delete_link = address_link + \
                                      str(partner.webshop_import_key) + \
                                      '/'
                time = datetime.now()
                address_api = requests.delete(url=address_delete_link,
                                              headers=headers,
                                              verify=False)
                # Technical API Log
                tech_address_log = partner.sudo().create_technical_log_api(
                    request_method='DELETE',
                    request_type='Address',
                    request_url=address_delete_link,
                    request_headers=headers,
                    request_response=address_api.content,
                    request_uid=self.env.uid,
                    request_status=address_api.status_code,
                    request_time=time,
                    request_arguments=address_api,
                    request_direction='outgoing')

                # Address Log
                if address_api.status_code in (200, 201, 204):
                    status = 'successful'
                else:
                    status = 'failed'
                address_log = {
                    'address_name': partner.id,
                    'parent_address_name': partner.parent_id.id,
                    'address_id': partner.id,
                    'webshop_import_key': partner.webshop_import_key,
                    'type': 'DELETE',
                    'sync_method': 'real_time',
                    'sync_time': time,
                    'sync_status': status,
                    'response_body': address_api.content,
                }
                self.env['webshop.address.api.log'].sudo().create(
                    address_log)

                # Send email notification
                if address_api.status_code not in (200, 201, 204) \
                        and tech_address_log:
                    for user in self.env['webshop.fail.notification'] \
                            .sudo().search([]):
                        if user.email:
                            tech_address_log.sudo().action_send_fail_notification_mail \
                                (lang=user.user_id.partner_id.lang,
                                 email=user.email,
                                 user=user.user_id.name,
                                 aid=partner.id,
                                 wik=partner.webshop_import_key,
                                 aname=partner.name,
                                 atype=partner.type,
                                 aparent=partner.parent_id.name,
                                 synctime=time,
                                 response=address_api.content,
                                 api_name='De-Activate Address Api')
                _logger.info('ADDRESS PUT ---------------> %s',
                             address_api)
                _logger.info(
                    'ADDRESS PUT RESULT ---------------> %s',
                    address_api.content)
        return super(WebshopResPartner, self).unlink()

    @api.model_create_multi
    def create(self, vals_list):
        partners = super(WebshopResPartner, self.with_context(from_create=True)).create(vals_list)

        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)])
        retries = 0
        if api_config:
            retries = api_config.api_attempts

        for partner in partners:
            if not partner.parent_id and partner.parent_id1:
                partner.parent_id = partner.parent_id1

            partner.webshop_import_key = str(partner.id)

            # Validation Checking for Webshop Checkbox
            if not partner.webshop_checkbox:
                if partner.type in ('delivery', 'invoice'):
                    for child in partner.child_ids_address:
                        if child.webshop_checkbox:
                            child.webshop_checkbox = False
                elif partner.type == 'contact':
                    for contact in partner.child_ids:
                        if contact.webshop_checkbox:
                            contact.webshop_checkbox = False

                if not partner.parent_id:
                    if (partner.customer or partner.end_user) and \
                            partner.active is True and \
                            partner.sale_warn != 'block':
                        partner.webshop_checkbox = True
                else:
                    if partner.type == 'contact':
                        partner.webshop_checkbox = False
                    elif partner.type in ('delivery', 'invoice'):
                        if (partner.customer or partner.end_user) and \
                                partner.active is True and \
                                partner.sale_warn != 'block' and \
                                partner.parent_id.webshop_checkbox:
                            partner.webshop_checkbox = True

            # Validation Checking for API
            if partner.webshop_checkbox:
                if (partner.customer or partner.end_user) and \
                        partner.active is True and \
                        partner.sale_warn != 'block':
                    if partner.company_type == 'company':
                        if not partner.parent_id:
                            for vals in vals_list:
                                if not vals.get('child_ids') and not \
                                        vals.get('child_ids_address'):
                                    # Customer API
                                    partner.with_delay(max_retries=retries)\
                                        .webshop_api_customer(method='create')
                                    if not partner.child_ids_address:
                                        if (partner.street or partner.street2) \
                                                and partner.zip \
                                                and partner.city \
                                                and partner.country_id \
                                                and partner.name:
                                            partner.with_delay(max_retries=retries) \
                                                .webshop_api_default_address(
                                                method='create',
                                                default_delivery=True,
                                                default_invoice=True)
                                        else:
                                            raise_warning = False
                                            msg = 'The following fields are ' \
                                                  'required for Default ' \
                                                  'Address API! \n'
                                            if not partner.street and not \
                                                    partner.street2:
                                                raise_warning = True
                                                msg += ' - Street \n' \
                                                       ' - Street 2 \n'
                                            if not partner.zip:
                                                raise_warning = True
                                                msg += ' - Zip \n'
                                            if not partner.city:
                                                raise_warning = True
                                                msg += ' - City \n'
                                            if not partner.country_id:
                                                raise_warning = True
                                                msg += ' - Country \n'
                                            if not partner.name:
                                                raise_warning = True
                                                msg += ' - Name \n'
                                            if raise_warning is True:
                                                raise ValidationError(_(msg))
                        else:
                            raise ValidationError(
                                _('You are not allowed to set '
                                  '"Webshop" field to True because '
                                  'one of the following conditions '
                                  'are not met! \n'
                                  ' - Contact Should NOT have any PARENT'))
                    else:
                        if partner.parent_id:
                            if partner.parent_id.webshop_checkbox:
                                # Address API
                                if partner.type in ('invoice', 'delivery'):
                                    if (partner.street or partner.street2) \
                                            and partner.zip \
                                            and partner.city \
                                            and partner.country_id \
                                            and partner.name:
                                        partner.parent_id.with_delay(max_retries=retries) \
                                            .webshop_api_customer(method='write')

                                        default_dev = True
                                        default_inv = True
                                        for child in partner.parent_id.child_ids_address:
                                            if child.type == 'invoice' \
                                                    and child.is_default_address:
                                                default_inv = False
                                            elif child.type == 'delivery' \
                                                    and child.is_default_address:
                                                default_dev = False

                                        partner.parent_id.with_delay(
                                            max_retries=retries) \
                                            .webshop_api_default_address(
                                            method='write',
                                            default_delivery=default_dev,
                                            default_invoice=default_inv)

                                        partner.with_delay(max_retries=retries) \
                                            .webshop_api_address(method='create')
                                    else:
                                        raise_warning = False
                                        msg = 'The following fields are required for Address API! \n'
                                        if not partner.street and not partner.street2:
                                            raise_warning = True
                                            msg += ' - Street \n' \
                                                   ' - Street 2 \n'
                                        if not partner.zip:
                                            raise_warning = True
                                            msg += ' - Zip \n'
                                        if not partner.city:
                                            raise_warning = True
                                            msg += ' - City \n'
                                        if not partner.country_id:
                                            raise_warning = True
                                            msg += ' - Country \n'
                                        if not partner.name:
                                            raise_warning = True
                                            msg += ' - Name \n'
                                        if raise_warning is True:
                                            raise ValidationError(_(msg))
                                # User API
                                elif partner.type == 'contact':
                                    if partner.email and partner.first_name and partner.last_name:
                                        partner.parent_id.with_delay(
                                            max_retries=retries) \
                                            .webshop_api_customer(
                                            method='write')
                                        partner.with_delay(max_retries=retries)\
                                            .webshop_api_user(method='create')
                                    else:
                                        contact_warning = False
                                        con_msg = 'The following fields are required for User API! \n'
                                        if not partner.email:
                                            contact_warning = True
                                            con_msg += ' - Email \n'
                                        if not partner.first_name:
                                            contact_warning = True
                                            con_msg += ' - First Name \n'
                                        if not partner.last_name:
                                            contact_warning = True
                                            con_msg += ' - Last Name \n'
                                        if contact_warning is True:
                                            raise ValidationError(_(con_msg))
                                else:
                                    raise ValidationError(
                                        _('You are not allowed to set '
                                          '"Webshop" field to True for '
                                          'partner\'s other than '
                                          'invoice, delivery and '
                                          'contacts!'))
                            else:
                                raise ValidationError(
                                    _('You are not allowed to set '
                                      '"Webshop" field to True because '
                                      'one of the following conditions '
                                      'are not met! \n'
                                      ' - "Webshop" of Parent Company MUST = TRUE '))
                        else:
                            # Customer API
                            if partner.type in ('invoice', 'delivery'):
                                raise ValidationError(_('Delivery/Invoice must have a parent!'))
                            else:
                                for vals in vals_list:
                                    if not vals.get('child_ids') and not \
                                            vals.get('child_ids_address'):
                                        partner.with_delay(max_retries=retries)\
                                            .webshop_api_customer(method='create')
                                        if not partner.child_ids_address:
                                            if (partner.street or partner.street2) \
                                                    and partner.zip \
                                                    and partner.city \
                                                    and partner.country_id \
                                                    and partner.name:
                                                partner.with_delay(
                                                    max_retries=retries) \
                                                    .webshop_api_default_address(
                                                    method='create',
                                                    delivery=True,
                                                    invoice=True,
                                                    default_delivery=True,
                                                    default_invoice=True)
                else:
                    main_warning = False
                    main_msg = 'You are not allowed to set "Webshop" field to ' \
                               'True because one of the following conditions ' \
                               'are not met! \n'
                    if not (partner.customer or partner.end_user):
                        main_msg += ' - Dealer = True OR End User = True \n'
                        main_warning = True
                    if partner.active is False:
                        main_msg += ' - Partner must be Active \n'
                        main_warning = True
                    if partner.sale_warn == 'block':
                        main_msg += ' - Sales Warning NOT EQUAL to Blocked \n'
                        main_warning = True
                    if main_warning is True:
                        raise ValidationError(_(main_msg))

        return partners

    @api.multi
    def write(self, vals):
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)])
        retries = 0
        if api_config:
            retries = api_config.api_attempts

        # De-activate Partner
        for partner in self:
            checkbox = vals.get('webshop_checkbox')
            active = vals.get('active')
            if checkbox is False or active is False:
                if (partner.customer or partner.end_user) and \
                        partner.sale_warn != 'block':
                    if not partner.parent_id:
                        partner.with_delay(max_retries=retries) \
                            .webshop_api_customer(method='delete')
                        partner.with_delay(max_retries=retries) \
                            .webshop_api_default_address(method='delete')
                        if partner.child_ids_address:
                            for child in partner.child_ids_address:
                                if child.webshop_checkbox:
                                    child.webshop_checkbox = False
                        if partner.child_ids:
                            for contact in partner.child_ids:
                                if contact.webshop_checkbox:
                                    contact.webshop_checkbox = False
                    else:
                        if partner.type in ('invoice', 'delivery'):
                            partner.with_delay(max_retries=retries) \
                                .webshop_api_address(method='delete')
                        elif partner.type == 'contact':
                            partner.with_delay(max_retries=retries) \
                                .webshop_api_user(method='delete')

        result = super(WebshopResPartner, self).write(vals)
        context = self.env.context
        for partner in self:
            if not context.get('from_create'):
                if vals.get('name') or \
                        vals.get('blocked') or \
                        vals.get('blocked') is False or \
                        vals.get('lang') or \
                        vals.get('lang') is False or \
                        vals.get('property_account_position_id') or \
                        vals.get('property_account_position_id') is False or \
                        vals.get('property_payment_term_id') or \
                        vals.get('property_payment_term_id') is False or \
                        vals.get('vat') or \
                        vals.get('vat') is False or \
                        vals.get('type') or \
                        vals.get('type') is False or \
                        vals.get('vat') == '' or \
                        vals.get('child_ids_address') or \
                        vals.get('street2') or \
                        vals.get('street2') is False or \
                        vals.get('street_number') or \
                        vals.get('street_number') is False or \
                        vals.get('street_number2') or \
                        vals.get('street_number2') is False or \
                        vals.get('zip') or \
                        vals.get('zip') is False or \
                        vals.get('city') or \
                        vals.get('city') is False or \
                        vals.get('sale_warn') or \
                        vals.get('sale_warn') is False or \
                        vals.get('state') or \
                        vals.get('state') is False or \
                        vals.get('country') or \
                        vals.get('country') is False or \
                        vals.get('phone') or \
                        vals.get('phone') is False or \
                        vals.get('mobile') or \
                        vals.get('mobile') is False or \
                        vals.get('type') or \
                        vals.get('is_default_address') or \
                        vals.get('is_default_address') is False or \
                        vals.get('parent_id') or \
                        vals.get('parent_id') is False or \
                        vals.get('email') or \
                        vals.get('email') is False or \
                        vals.get('child_ids_address') or \
                        vals.get('child_ids') or \
                        vals.get('customer') or \
                        vals.get('customer') is False or \
                        vals.get('end_user') or \
                        vals.get('end_user') is False or \
                        vals.get('webshop_checkbox') or \
                        vals.get('title') or \
                        vals.get('title') is False or \
                        vals.get('first_name') or \
                        vals.get('first_name') == '' or \
                        vals.get('first_name') is False or \
                        vals.get('last_name') or \
                        vals.get('last_name') is False or \
                        vals.get('last_name') == '' or \
                        vals.get('active') or \
                        vals.get('country_id') or \
                        vals.get('property_product_pricelist') or \
                        vals.get('property_product_pricelist') is False:
                    if partner.webshop_checkbox:
                        if (partner.customer or partner.end_user) and \
                                partner.active is True and \
                                partner.sale_warn != 'block':
                            if partner.company_type == 'company':
                                if not partner.parent_id:
                                    if not vals.get('child_ids') and not \
                                            vals.get('child_ids_address'):
                                        # Customer API
                                        partner.with_delay(max_retries=retries)\
                                            .webshop_api_customer(method='write')
                                        if not partner.child_ids_address:
                                            if (partner.street or partner.street2) \
                                                    and partner.zip \
                                                    and partner.city \
                                                    and partner.country_id \
                                                    and partner.name:
                                                partner.with_delay(max_retries=retries) \
                                                    .webshop_api_default_address(
                                                    method='write',
                                                    default_delivery=True,
                                                    default_invoice=True)
                                            else:
                                                raise_warning = False
                                                msg = 'The following fields are ' \
                                                      'required for Default Address ' \
                                                      'API! \n'
                                                if not partner.street and not \
                                                        partner.street2:
                                                    raise_warning = True
                                                    msg += ' - Street \n' \
                                                           ' - Street 2 \n'
                                                if not partner.zip:
                                                    raise_warning = True
                                                    msg += ' - Zip \n'
                                                if not partner.city:
                                                    raise_warning = True
                                                    msg += ' - City \n'
                                                if not partner.country_id:
                                                    raise_warning = True
                                                    msg += ' - Country \n'
                                                if not partner.name:
                                                    raise_warning = True
                                                    msg += ' - Name \n'
                                                if raise_warning is True:
                                                    raise ValidationError(
                                                        _(msg))
                                else:
                                    raise ValidationError(
                                        _('You are not allowed to set '
                                          '"Webshop" field to True because '
                                          'one of the following conditions '
                                          'are not met! \n'
                                          '- Contact Should NOT have any PARENT'))
                            else:
                                if partner.parent_id:
                                    if partner.parent_id.webshop_checkbox:
                                        # Address API
                                        if partner.type in ('invoice', 'delivery'):
                                            if (partner.street or partner.street2) \
                                                    and partner.zip \
                                                    and partner.city \
                                                    and partner.country_id \
                                                    and partner.name:
                                                partner.parent_id.with_delay(max_retries=retries) \
                                                    .webshop_api_customer(method='write')

                                                default_dev = True
                                                default_inv = True
                                                for child in partner.parent_id.child_ids_address:
                                                    if child.type == 'invoice' \
                                                            and child.is_default_address:
                                                        default_inv = False
                                                    elif child.type == 'delivery' \
                                                            and child.is_default_address:
                                                        default_dev = False

                                                partner.parent_id.with_delay(
                                                    max_retries=retries) \
                                                    .webshop_api_default_address(
                                                    method='write',
                                                    default_delivery=default_dev,
                                                    default_invoice=default_inv)

                                                partner.with_delay(max_retries=retries) \
                                                    .webshop_api_address(method='write')
                                            else:
                                                raise_warning = False
                                                msg = 'The following fields are ' \
                                                      'required for Address API! \n'
                                                if not partner.street and not \
                                                        partner.street2:
                                                    raise_warning = True
                                                    msg += ' - Street \n' \
                                                           ' - Street 2 \n'
                                                if not partner.zip:
                                                    raise_warning = True
                                                    msg += ' - Zip \n'
                                                if not partner.city:
                                                    raise_warning = True
                                                    msg += ' - City \n'
                                                if not partner.country_id:
                                                    raise_warning = True
                                                    msg += ' - Country \n'
                                                if not partner.name:
                                                    raise_warning = True
                                                    msg += ' - Name \n'
                                                if raise_warning is True:
                                                    raise ValidationError(
                                                        _(msg))
                                        # User API
                                        elif partner.type == 'contact':
                                            if partner.email and partner.first_name and partner.last_name:
                                                if (partner.street or partner.street2) \
                                                        and partner.zip \
                                                        and partner.city \
                                                        and partner.country_id \
                                                        and partner.name:
                                                    partner.parent_id.with_delay(
                                                        max_retries=retries) \
                                                        .webshop_api_customer(
                                                        method='write')

                                                    default_dev = True
                                                    default_inv = True
                                                    for child in partner.parent_id.child_ids_address:
                                                        if child.type == 'invoice' \
                                                                and child.is_default_address:
                                                            default_inv = False
                                                        elif child.type == 'delivery' \
                                                                and child.is_default_address:
                                                            default_dev = False

                                                    partner.parent_id.with_delay(
                                                        max_retries=retries) \
                                                        .webshop_api_default_address(
                                                        method='write',
                                                        default_delivery=default_dev,
                                                        default_invoice=default_inv)

                                                    partner.with_delay(
                                                        max_retries=retries) \
                                                        .webshop_api_user(
                                                        method='write')
                                                else:
                                                    raise_warning = False
                                                    msg = 'The following fields are ' \
                                                          'required for Address API! \n'
                                                    if not partner.street and not \
                                                            partner.street2:
                                                        raise_warning = True
                                                        msg += ' - Street \n' \
                                                               ' - Street 2 \n'
                                                    if not partner.zip:
                                                        raise_warning = True
                                                        msg += ' - Zip \n'
                                                    if not partner.city:
                                                        raise_warning = True
                                                        msg += ' - City \n'
                                                    if not partner.country_id:
                                                        raise_warning = True
                                                        msg += ' - Country \n'
                                                    if not partner.name:
                                                        raise_warning = True
                                                        msg += ' - Name \n'
                                                    if raise_warning is True:
                                                        raise ValidationError(
                                                            _(msg))
                                            else:
                                                contact_warning = False
                                                con_msg = 'The following fields are required for User API! \n'
                                                if not partner.email:
                                                    contact_warning = True
                                                    con_msg += ' - Email \n'
                                                if not partner.first_name:
                                                    contact_warning = True
                                                    con_msg += ' - First Name \n'
                                                if not partner.last_name:
                                                    contact_warning = True
                                                    con_msg += ' - Last Name \n'
                                                if contact_warning is True:
                                                    raise ValidationError(_(con_msg))
                                        else:
                                            raise ValidationError(
                                                _('You are not allowed to set '
                                                  '"Webshop" field to True for '
                                                  'partner\'s other than '
                                                  'invoice, delivery and '
                                                  'contacts!'))
                                    else:
                                        raise ValidationError(
                                            _('You are not allowed to set '
                                              '"Webshop" field to True because '
                                              'one of the following conditions '
                                              'are not met! \n'
                                              ' - "Webshop" of Parent Company MUST = TRUE '))
                                else:
                                    # Customer API
                                    partner.with_delay(max_retries=retries)\
                                        .webshop_api_customer(method='write')
                        else:
                            main_warning = False
                            main_msg = 'You are not allowed to set "Webshop" field to ' \
                                       'True because one of the following conditions ' \
                                       'are not met! \n'
                            if not (partner.customer or partner.end_user):
                                main_msg += ' - Dealer = True OR End User = True \n'
                                main_warning = True
                            if partner.active is False:
                                main_msg += ' - Partner must be Active \n'
                                main_warning = True
                            if partner.sale_warn == 'block':
                                main_msg += ' - Sales Warning NOT EQUAL to Blocked \n'
                                main_warning = True
                            if main_warning is True:
                                raise ValidationError(_(main_msg))

        return result

    @api.multi
    @job
    def webshop_api_customer(self, method):
        for partner in self:
            api_config = self.env['webshop.api.config'].search(
                [('active', '=', True)])

            if api_config and api_config.token and api_config.api_url and \
                    api_config.customer_end_point and api_config.api_company:
                customer_link = api_config.api_url + api_config.customer_end_point
                headers = {'Authorization': 'Token ' + api_config.token,
                           'Content-Type': 'application/json'}

                if method == 'delete':
                    time = datetime.now()
                    customer_delete_link = customer_link + \
                                           str(partner.webshop_import_key) + \
                                           '/'
                    customer_api = requests.delete(url=customer_delete_link,
                                                   headers=headers,
                                                   verify=False)
                    # Technical API Log
                    tech_customer_log = partner.sudo().create_technical_log_api(
                        request_method='PUT',
                        request_type='Customer',
                        request_url=customer_delete_link,
                        request_headers=headers,
                        request_response=customer_api.content,
                        request_uid=self.env.uid,
                        request_status=customer_api.status_code,
                        request_time=time,
                        request_arguments=customer_api,
                        request_direction='outgoing')

                    # Customer Log
                    if customer_api.status_code in (200, 201, 202, 204):
                        status = 'successful'
                    else:
                        status = 'failed'
                    customer_log = {
                        'customer_name': partner.id,
                        'customer_id': partner.id,
                        'webshop_import_key': partner.webshop_import_key,
                        'customer_email': partner.email,
                        'type': 'PUT',
                        'sync_method': 'real_time',
                        'sync_time': time,
                        'sync_status': status,
                        'response_body': customer_api.content,
                    }
                    self.env['webshop.customer.api.log'].sudo().create(
                        customer_log)

                    # Send email notification
                    if customer_api.status_code not in (200, 201, 202, 204) \
                            and tech_customer_log:
                        for user in self.env['webshop.fail.notification'] \
                                .sudo().search([]):
                            if user.email:
                                tech_customer_log.sudo().action_send_fail_notification_mail \
                                    (lang=user.user_id.partner_id.lang,
                                     email=user.email,
                                     user=user.user_id.name,
                                     cusid=partner.id,
                                     wik=partner.webshop_import_key,
                                     cusname=partner.name,
                                     synctime=time,
                                     response=customer_api.content,
                                     api_name='De-Activate Customer Api')
                    _logger.info('CUSTOMER PUT ---------------> %s',
                                 customer_api)
                    _logger.info(
                        'CUSTOMER PUT RESULT ---------------> %s',
                        customer_api.content)
                else:
                    customer_params = {
                        'key': partner.webshop_import_key,
                        'code': partner.webshop_import_key,
                        'name': partner.name,
                        'active': partner.active,
                    }

                    # Vat number
                    if partner.vat:
                        customer_params.update({'vat_numbers': [partner.vat]})
                    else:
                        customer_params.update({'vat_numbers': []})

                    # Language
                    lang = []
                    if partner.lang:
                        lang.append({'company': api_config.api_company,
                                     'value': partner.lang})
                        customer_params.update({'languages': lang})

                    # blocked
                    if partner.sale_warn != 'block':
                        customer_params.update({'blocked': False})
                    else:
                        customer_params.update({'blocked': True})

                    # Pricelist
                    if method in ('create', 'write'):
                        price = []
                        if partner.property_product_pricelist:
                            # partner.property_product_pricelist.\
                            #     webshop_api_pricelist(method='write')
                            price.append(str(partner.property_product_pricelist.id))
                            customer_params.update(
                                {'price_lists': price})
                        else:
                            customer_params.update({'price_lists': []})

                    # Payment Term
                    payment_term = []
                    if partner.property_payment_term_id:
                        payment_term.append({'company': api_config.api_company,
                                             'value': str(partner.property_payment_term_id.id)})
                        customer_params.update(
                            {'payment_terms': payment_term})
                    else:
                        customer_params.update({'payment_terms': []})

                    # Tax Rules
                    tax_rule = []
                    if partner.property_account_position_id:
                        tax_rule.append({'company': api_config.api_company,
                                         'value': str(partner.property_account_position_id.id)})
                        customer_params.update(
                            {'tax_rules': tax_rule})
                    else:
                        customer_params.update({'tax_rules': []})

                    time = datetime.now()
                    customer_api_link = customer_link
                    cust_data = json.dumps(customer_params)
                    if method == 'create':
                        customer_api = requests.post(url=customer_api_link,
                                                     data=cust_data,
                                                     headers=headers,
                                                     verify=False)
                        # Technical API Log
                        tech_customer_log = partner.sudo().create_technical_log_api(
                            request_method='POST',
                            request_type='Customer',
                            request_url=customer_api_link,
                            request_headers=headers,
                            request_response=customer_api.content,
                            request_uid=self.env.uid,
                            request_status=customer_api.status_code,
                            request_time=time,
                            request_arguments=customer_api,
                            request_direction='outgoing')

                        # Customer Log
                        if customer_api.status_code in (200, 201, 202):
                            status = 'successful'
                        else:
                            status = 'failed'
                        customer_log = {
                            'customer_name': partner.id,
                            'customer_id': partner.id,
                            'webshop_import_key': partner.webshop_import_key,
                            'customer_email': partner.email,
                            'type': 'POST',
                            'sync_method': 'real_time',
                            'sync_time': time,
                            'sync_status': status,
                            'response_body': customer_api.content,
                        }
                        self.env['webshop.customer.api.log'].sudo().create(customer_log)

                        # Send email notification
                        if customer_api.status_code not in (200, 201, 202) \
                                and tech_customer_log:
                            for user in self.env['webshop.fail.notification'] \
                                    .sudo().search([]):
                                if user.email:
                                    tech_customer_log.sudo().action_send_fail_notification_mail \
                                        (lang=user.user_id.partner_id.lang,
                                         email=user.email,
                                         user=user.user_id.name,
                                         cusid=partner.id,
                                         wik=partner.webshop_import_key,
                                         cusname=partner.name,
                                         synctime=time,
                                         response=customer_api.content,
                                         api_name='Create Customer Api')
                        _logger.info('CUSTOMER POST ---------------> %s',
                                     customer_api)
                        _logger.info(
                            'CUSTOMER POST RESULT ---------------> %s',
                            customer_api.content)
                    elif method == 'write':
                        customer_put_link = customer_api_link + \
                                            str(partner.webshop_import_key) + \
                                            '/'
                        customer_api = requests.put(url=customer_put_link,
                                                    data=cust_data,
                                                    headers=headers,
                                                    verify=False)
                        # Technical API Log
                        tech_customer_log = partner.sudo().create_technical_log_api(
                            request_method='PUT',
                            request_type='Customer',
                            request_url=customer_put_link,
                            request_headers=headers,
                            request_response=customer_api.content,
                            request_uid=self.env.uid,
                            request_status=customer_api.status_code,
                            request_time=time,
                            request_arguments=customer_api,
                            request_direction='outgoing')

                        # Pricelist Log
                        if customer_api.status_code in (200, 201, 202):
                            status = 'successful'
                        else:
                            status = 'failed'
                        customer_log = {
                            'customer_name': partner.id,
                            'customer_id': partner.id,
                            'webshop_import_key': partner.webshop_import_key,
                            'customer_email': partner.email,
                            'type': 'PUT',
                            'sync_method': 'real_time',
                            'sync_time': time,
                            'sync_status': status,
                            'response_body': customer_api.content,
                        }
                        self.env['webshop.customer.api.log'].sudo().create(
                            customer_log)

                        # Send email notification
                        if customer_api.status_code not in (200, 201, 202) \
                                and tech_customer_log:
                            for user in self.env['webshop.fail.notification'] \
                                    .sudo().search([]):
                                if user.email:
                                    tech_customer_log.sudo().action_send_fail_notification_mail \
                                        (lang=user.user_id.partner_id.lang,
                                         email=user.email,
                                         user=user.user_id.name,
                                         cusid=partner.id,
                                         wik=partner.webshop_import_key,
                                         cusname=partner.name,
                                         synctime=time,
                                         response=customer_api.content,
                                         api_name='Update Customer Api')
                        _logger.info('CUSTOMER PUT ---------------> %s',
                                     customer_api)
                        _logger.info(
                            'CUSTOMER PUT RESULT ---------------> %s',
                            customer_api.content)

        return True

    @api.multi
    @job
    def webshop_api_default_address(self, method,
                                    default_delivery=False,
                                    default_invoice=False):
        for partner in self:
            api_config = self.env['webshop.api.config'].search(
                [('active', '=', True)])

            if api_config and api_config.token and api_config.api_url and \
                    api_config.address_end_point:
                address_link = api_config.api_url + api_config.address_end_point
                headers = {'Authorization': 'Token ' + api_config.token,
                           'Content-Type': 'application/json'}

                default_log = ''
                if default_delivery:
                    default_log = 'Default Delivery Address'
                elif default_invoice:
                    default_log = 'Default Invoice Address'

                if partner.street_name and not partner.street2:
                    street = partner.street_name
                elif partner.street2 and not partner.street_name:
                    street = partner.street2
                elif partner.street2 and partner.street_name:
                    street = partner.street_name + ', ' + partner.street2
                else:
                    street = ''

                if partner.parent_id:
                    customer = partner.parent_id.webshop_import_key
                else:
                    customer = partner.webshop_import_key

                address_params = {
                    'key': partner.webshop_import_key,
                    'customer': customer,
                    'name': partner.name,
                    'active': partner.active,
                    'street': street or None,
                    'house_number': partner.street_number or None,
                    'house_number_addition': partner.street_number2 or None,
                    'zip': partner.zip or None,
                    'city': partner.city or None,
                    'country': partner.country_id.code,
                    'phone': partner.phone or None,
                    'delivery': True,
                    'invoice': True,
                    'default_delivery': default_delivery,
                    'default_invoice': default_invoice,
                }

                time = datetime.now()
                address_api_link = address_link
                address_data = json.dumps(address_params)
                if method == 'create':
                    address_api = requests.post(url=address_api_link,
                                                 data=address_data,
                                                 headers=headers,
                                                 verify=False)
                    # Technical API Log
                    tech_address_log = partner.sudo().create_technical_log_api(
                        request_method='POST',
                        request_type='Address',
                        request_url=address_api_link,
                        request_headers=headers,
                        request_response=address_api.content,
                        request_uid=self.env.uid,
                        request_status=address_api.status_code,
                        request_time=time,
                        request_arguments=address_api,
                        request_direction='outgoing')

                    # Address Log
                    if address_api.status_code in (200, 201, 202):
                        status = 'successful'
                    else:
                        status = 'failed'
                    address_log = {
                        'address_name': partner.id,
                        'parent_address_name': partner.parent_id.id,
                        'address_id': partner.id,
                        'webshop_import_key': partner.webshop_import_key,
                        'default_address': default_log,
                        'type': 'POST',
                        'sync_method': 'real_time',
                        'sync_time': time,
                        'sync_status': status,
                        'response_body': address_api.content,
                    }
                    self.env['webshop.address.api.log'].sudo().create(
                        address_log)

                    # Send email notification
                    if address_api.status_code not in (200, 201, 202) \
                            and tech_address_log:
                        for user in self.env['webshop.fail.notification'] \
                                .sudo().search([]):
                            if user.email:
                                tech_address_log.sudo().action_send_fail_notification_mail \
                                    (lang=user.user_id.partner_id.lang,
                                     email=user.email,
                                     user=user.user_id.name,
                                     aid=partner.id,
                                     wik=partner.webshop_import_key,
                                     aname=partner.name,
                                     atype=partner.type,
                                     aparent=partner.parent_id.name,
                                     synctime=time,
                                     response=address_api.content,
                                     api_name='Create Address Api')
                    _logger.info('ADDRESS POST ---------------> %s',
                                 address_api)
                    _logger.info(
                        'ADDRESS POST RESULT ---------------> %s',
                        address_api.content)
                elif method == 'write':
                    address_put_link = address_api_link + \
                                       str(partner.webshop_import_key) + \
                                       '/'
                    address_api = requests.put(url=address_put_link,
                                               data=address_data,
                                               headers=headers,
                                               verify=False)
                    # Technical API Log
                    tech_address_log = partner.sudo().create_technical_log_api(
                        request_method='PUT',
                        request_type='Address',
                        request_url=address_put_link,
                        request_headers=headers,
                        request_response=address_api.content,
                        request_uid=self.env.uid,
                        request_status=address_api.status_code,
                        request_time=time,
                        request_arguments=address_api,
                        request_direction='outgoing')

                    # Address Log
                    if address_api.status_code in (200, 201, 202):
                        status = 'successful'
                    else:
                        status = 'failed'
                    address_log = {
                        'address_name': partner.id,
                        'parent_address_name': partner.parent_id.id,
                        'address_id': partner.id,
                        'webshop_import_key': partner.webshop_import_key,
                        'default_address': default_log,
                        'type': 'POST',
                        'sync_method': 'real_time',
                        'sync_time': time,
                        'sync_status': status,
                        'response_body': address_api.content,
                    }
                    self.env['webshop.address.api.log'].sudo().create(
                        address_log)

                    # Send email notification
                    if address_api.status_code not in (200, 201, 202) \
                            and tech_address_log:
                        for user in self.env['webshop.fail.notification'] \
                                .sudo().search([]):
                            if user.email:
                                tech_address_log.sudo().action_send_fail_notification_mail \
                                    (lang=user.user_id.partner_id.lang,
                                     email=user.email,
                                     user=user.user_id.name,
                                     aid=partner.id,
                                     wik=partner.webshop_import_key,
                                     aname=partner.name,
                                     atype=partner.type,
                                     aparent=partner.parent_id.name,
                                     synctime=time,
                                     response=address_api.content,
                                     api_name='Edit Address Api')
                    _logger.info('ADDRESS PUT ---------------> %s',
                                 address_api)
                    _logger.info(
                        'ADDRESS PUT RESULT ---------------> %s',
                        address_api.content)
                else:
                    delete_params = {
                        'key': partner.webshop_import_key,
                        'customer': partner.webshop_import_key,
                        'name': partner.name,
                        'street': street,
                        'zip': partner.zip,
                        'city': partner.city,
                        'country': partner.country_id.code,
                        'active': False,
                    }
                    delete_data = json.dumps(delete_params)
                    address_delete_link = address_api_link + \
                                          str(partner.webshop_import_key) + \
                                          '/'
                    address_api = requests.put(url=address_delete_link,
                                               data=delete_data,
                                               headers=headers,
                                               verify=False)
                    # Technical API Log
                    tech_address_log = partner.sudo().create_technical_log_api(
                        request_method='PUT',
                        request_type='Address',
                        request_url=address_delete_link,
                        request_headers=headers,
                        request_response=address_api.content,
                        request_uid=self.env.uid,
                        request_status=address_api.status_code,
                        request_time=time,
                        request_arguments=address_api,
                        request_direction='outgoing')

                    # Address Log
                    if address_api.status_code in (200, 201, 202):
                        status = 'successful'
                    else:
                        status = 'failed'
                    address_log = {
                        'address_name': partner.id,
                        'parent_address_name': partner.parent_id.id,
                        'address_id': partner.id,
                        'webshop_import_key': partner.webshop_import_key,
                        'default_address': default_log,
                        'type': 'POST',
                        'sync_method': 'real_time',
                        'sync_time': time,
                        'sync_status': status,
                        'response_body': address_api.content,
                    }
                    self.env['webshop.address.api.log'].sudo().create(address_log)

                    # Send email notification
                    if address_api.status_code not in (200, 201, 202) \
                            and tech_address_log:
                        for user in self.env['webshop.fail.notification'] \
                                .sudo().search([]):
                            if user.email:
                                tech_address_log.sudo().action_send_fail_notification_mail \
                                    (lang=user.user_id.partner_id.lang,
                                     email=user.email,
                                     user=user.user_id.name,
                                     aid=partner.id,
                                     wik=partner.webshop_import_key,
                                     aname=partner.name,
                                     atype=partner.type,
                                     aparent=partner.parent_id.name,
                                     synctime=time,
                                     response=address_api.content,
                                     api_name='De-Activate Address Api')
                    _logger.info('ADDRESS PUT ---------------> %s',
                                 address_api)
                    _logger.info(
                        'ADDRESS PUT RESULT ---------------> %s',
                        address_api.content)
        return True

    @api.multi
    @job
    def webshop_api_address(self, method):
        for partner in self:
            api_config = self.env['webshop.api.config'].search(
                [('active', '=', True)])

            if api_config and api_config.token and api_config.api_url and \
                    api_config.address_end_point:
                address_link = api_config.api_url + api_config.address_end_point
                headers = {'Authorization': 'Token ' + api_config.token,
                           'Content-Type': 'application/json'}

                if method == 'delete':
                    address_delete_link = address_link + \
                                          str(partner.webshop_import_key) + \
                                          '/'
                    time = datetime.now()
                    address_api = requests.delete(url=address_delete_link,
                                                  headers=headers,
                                                  verify=False)
                    # Technical API Log
                    tech_address_log = partner.sudo().create_technical_log_api(
                        request_method='DELETE',
                        request_type='Address',
                        request_url=address_delete_link,
                        request_headers=headers,
                        request_response=address_api.content,
                        request_uid=self.env.uid,
                        request_status=address_api.status_code,
                        request_time=time,
                        request_arguments=address_api,
                        request_direction='outgoing')

                    # Address Log
                    if address_api.status_code in (200, 201, 204):
                        status = 'successful'
                    else:
                        status = 'failed'
                    address_log = {
                        'address_name': partner.id,
                        'parent_address_name': partner.parent_id.id,
                        'address_id': partner.id,
                        'webshop_import_key': partner.webshop_import_key,
                        'type': 'DELETE',
                        'sync_method': 'real_time',
                        'sync_time': time,
                        'sync_status': status,
                        'response_body': address_api.content,
                    }
                    self.env['webshop.address.api.log'].sudo().create(
                        address_log)

                    # Send email notification
                    if address_api.status_code not in (200, 201, 204) \
                            and tech_address_log:
                        for user in self.env['webshop.fail.notification'] \
                                .sudo().search([]):
                            if user.email:
                                tech_address_log.sudo().action_send_fail_notification_mail \
                                    (lang=user.user_id.partner_id.lang,
                                     email=user.email,
                                     user=user.user_id.name,
                                     aid=partner.id,
                                     wik=partner.webshop_import_key,
                                     aname=partner.name,
                                     atype=partner.type,
                                     aparent=partner.parent_id.name,
                                     synctime=time,
                                     response=address_api.content,
                                     api_name='De-Activate Address Api')
                    _logger.info('ADDRESS PUT ---------------> %s',
                                 address_api)
                    _logger.info(
                        'ADDRESS PUT RESULT ---------------> %s',
                        address_api.content)
                else:
                    delivery = False
                    default_delivery = False
                    if partner.type == 'delivery':
                        delivery = True
                        if partner.is_default_address:
                            default_delivery = True
                        else:
                            default_delivery = False

                    invoice = False
                    default_invoice = False
                    if partner.type == 'invoice':
                        invoice = True
                        if partner.is_default_address:
                            default_invoice = True
                        else:
                            default_invoice = False

                    default_log = ''
                    if default_delivery:
                        default_log = 'Default Delivery Address'
                    elif default_invoice:
                        default_log = 'Default Invoice Address'

                    if partner.street_name and not partner.street2:
                        street = partner.street_name
                    elif partner.street2 and not partner.street_name:
                        street = partner.street2
                    elif partner.street2 and partner.street_name:
                        street = partner.street_name + ', ' + partner.street2
                    else:
                        street = ''

                    address_params = {
                        'key': partner.webshop_import_key,
                        'customer': partner.parent_id.webshop_import_key,
                        'name': partner.name,
                        'active': partner.active,
                        'street': street or None,
                        'house_number': partner.street_number or None,
                        'house_number_addition': partner.street_number2 or None,
                        'zip': partner.zip or None,
                        'city': partner.city or None,
                        'country': partner.country_id.code,
                        'phone': partner.phone or None,
                        'delivery': delivery,
                        'invoice': invoice,
                        'default_delivery': default_delivery,
                        'default_invoice': default_invoice,
                    }

                    time = datetime.now()
                    address_api_link = address_link
                    address_data = json.dumps(address_params)
                    if method == 'create':
                        address_api = requests.post(url=address_api_link,
                                                     data=address_data,
                                                     headers=headers,
                                                     verify=False)
                        # Technical API Log
                        tech_address_log = partner.sudo().create_technical_log_api(
                            request_method='POST',
                            request_type='Address',
                            request_url=address_api_link,
                            request_headers=headers,
                            request_response=address_api.content,
                            request_uid=self.env.uid,
                            request_status=address_api.status_code,
                            request_time=time,
                            request_arguments=address_api,
                            request_direction='outgoing')

                        # Address Log
                        if address_api.status_code in (200, 201, 202):
                            status = 'successful'
                        else:
                            status = 'failed'
                        address_log = {
                            'address_name': partner.id,
                            'parent_address_name': partner.parent_id.id,
                            'address_id': partner.id,
                            'webshop_import_key': partner.webshop_import_key,
                            'default_address': default_log,
                            'type': 'POST',
                            'sync_method': 'real_time',
                            'sync_time': time,
                            'sync_status': status,
                            'response_body': address_api.content,
                        }
                        self.env['webshop.address.api.log'].sudo().create(
                            address_log)

                        # Send email notification
                        if address_api.status_code not in (200, 201, 202) \
                                and tech_address_log:
                            for user in self.env['webshop.fail.notification'] \
                                    .sudo().search([]):
                                if user.email:
                                    tech_address_log.sudo().action_send_fail_notification_mail \
                                        (lang=user.user_id.partner_id.lang,
                                         email=user.email,
                                         user=user.user_id.name,
                                         aid=partner.id,
                                         wik=partner.webshop_import_key,
                                         aname=partner.name,
                                         atype=partner.type,
                                         aparent=partner.parent_id.name,
                                         synctime=time,
                                         response=address_api.content,
                                         api_name='Create Address Api')
                        _logger.info('ADDRESS POST ---------------> %s',
                                     address_api)
                        _logger.info(
                            'ADDRESS POST RESULT ---------------> %s',
                            address_api.content)
                    elif method == 'write':
                        address_put_link = address_api_link + \
                                           str(partner.webshop_import_key) + \
                                           '/'
                        address_api = requests.put(url=address_put_link,
                                                   data=address_data,
                                                   headers=headers,
                                                   verify=False)
                        # Technical API Log
                        tech_address_log = partner.sudo().create_technical_log_api(
                            request_method='PUT',
                            request_type='Address',
                            request_url=address_put_link,
                            request_headers=headers,
                            request_response=address_api.content,
                            request_uid=self.env.uid,
                            request_status=address_api.status_code,
                            request_time=time,
                            request_arguments=address_api,
                            request_direction='outgoing')

                        # Address Log
                        if address_api.status_code in (200, 201, 202):
                            status = 'successful'
                        else:
                            status = 'failed'
                        address_log = {
                            'address_name': partner.id,
                            'parent_address_name': partner.parent_id.id,
                            'address_id': partner.id,
                            'webshop_import_key': partner.webshop_import_key,
                            'default_address': default_log,
                            'type': 'POST',
                            'sync_method': 'real_time',
                            'sync_time': time,
                            'sync_status': status,
                            'response_body': address_api.content,
                        }
                        self.env['webshop.address.api.log'].sudo().create(
                            address_log)

                        # Send email notification
                        if address_api.status_code not in (200, 201, 202) \
                                and tech_address_log:
                            for user in self.env['webshop.fail.notification'] \
                                    .sudo().search([]):
                                if user.email:
                                    tech_address_log.sudo().action_send_fail_notification_mail \
                                        (lang=user.user_id.partner_id.lang,
                                         email=user.email,
                                         user=user.user_id.name,
                                         aid=partner.id,
                                         wik=partner.webshop_import_key,
                                         aname=partner.name,
                                         atype=partner.type,
                                         aparent=partner.parent_id.name,
                                         synctime=time,
                                         response=address_api.content,
                                         api_name='Edit Address Api')
                        _logger.info('ADDRESS PUT ---------------> %s',
                                     address_api)
                        _logger.info(
                            'ADDRESS PUT RESULT ---------------> %s',
                            address_api.content)
        return True

    @api.multi
    @job
    def webshop_api_user(self, method):
        for partner in self:
            api_config = self.env['webshop.api.config'].search(
                [('active', '=', True)])

            if api_config and api_config.token and api_config.api_url and \
                    api_config.user_end_point:
                headers = {'Authorization': 'Token ' + api_config.token,
                           'Content-Type': 'application/json'}
                user_link = api_config.api_url + api_config.user_end_point

                if method == 'delete':
                    time = datetime.now()
                    user_delete_link = user_link + \
                                       str(partner.webshop_import_key) + \
                                       '/'
                    user_api = requests.delete(url=user_delete_link,
                                               headers=headers,
                                               verify=False)
                    # Technical API Log
                    tech_user_log = partner.sudo().create_technical_log_api(
                        request_method='PUT',
                        request_type='USER',
                        request_url=user_delete_link,
                        request_headers=headers,
                        request_response=user_api.content,
                        request_uid=self.env.uid,
                        request_status=user_api.status_code,
                        request_time=time,
                        request_arguments=user_api,
                        request_direction='outgoing')

                    # Address Log
                    if user_api.status_code in (200, 201, 202):
                        status = 'successful'
                    else:
                        status = 'failed'
                    user_log = {
                        'user_name': partner.id,
                        'user_id': partner.parent_id.id,
                        'parent_company_name': partner.parent_id.id,
                        'parent_company_id': partner.parent_id.id,
                        'parent_webshop_import_key': partner.parent_id.webshop_import_key,
                        'type': 'POST',
                        'sync_method': 'real_time',
                        'sync_time': time,
                        'sync_status': status,
                        'response_body': user_api.content,
                    }
                    self.env['webshop.user.api.log'].sudo().create(user_log)

                    # Send email notification
                    if user_api.status_code not in (200, 201, 202) \
                            and tech_user_log:
                        for user in self.env['webshop.fail.notification'] \
                                .sudo().search([]):
                            if user.email:
                                tech_user_log.sudo().action_send_fail_notification_mail \
                                    (lang=user.user_id.partner_id.lang,
                                     email=user.email,
                                     user=user.user_id.name,
                                     cname=partner.name,
                                     cid=partner.id,
                                     pname=partner.parent_id.name,
                                     pid=partner.parent_id.id,
                                     synctime=time,
                                     response=user_api.content,
                                     api_name='De-Activate User Api')
                    _logger.info('USER PUT ---------------> %s',
                                 user_api)
                    _logger.info(
                        'USER PUT RESULT ---------------> %s',
                        user_api.content)
                else:
                    authorized_customers = []
                    if partner.parent_id:
                        authorized_customers.append(partner.parent_id.webshop_import_key)

                    user_params = {
                        'id': partner.webshop_import_key,
                        'key': partner.webshop_import_key,
                        'active': partner.active,
                        'language': partner.lang,
                        'webshop': api_config.default_web_id or '1',
                        'role': api_config.default_role_id or '1',
                        'authorised_customers': authorized_customers
                    }

                    if partner.first_name:
                        user_params.update({'first_name': partner.first_name})

                    if partner.last_name:
                        user_params.update({'last_name': partner.last_name})

                    if partner.email:
                        user_params.update({'email': partner.email})

                    if partner.phone:
                        user_params.update({'phone': partner.phone})

                    if partner.mobile:
                        user_params.update({'mobile': partner.mobile})

                    if partner.title:
                        user_params.update({'gender': partner.title.webshop_name})

                    time = datetime.now()
                    user_api_link = user_link
                    user_data = json.dumps(user_params)
                    if method == 'create':
                        user_api = requests.post(url=user_api_link,
                                                 data=user_data,
                                                 headers=headers,
                                                 verify=False)
                        # Technical API Log
                        tech_user_log = partner.sudo().create_technical_log_api(
                            request_method='POST',
                            request_type='User',
                            request_url=user_api_link,
                            request_headers=headers,
                            request_response=user_api.content,
                            request_uid=self.env.uid,
                            request_status=user_api.status_code,
                            request_time=time,
                            request_arguments=user_api,
                            request_direction='outgoing')

                        # User Log
                        if user_api.status_code in (200, 201, 202):
                            status = 'successful'
                        else:
                            status = 'failed'
                        user_log = {
                            'user_name': partner.id,
                            'user_id': partner.parent_id.id,
                            'parent_company_name': partner.parent_id.id,
                            'parent_company_id': partner.parent_id.id,
                            'parent_webshop_import_key': partner.parent_id.webshop_import_key,
                            'type': 'POST',
                            'sync_method': 'real_time',
                            'sync_time': time,
                            'sync_status': status,
                            'response_body': user_api.content,
                        }
                        self.env['webshop.user.api.log'].sudo().create(user_log)

                        # Send email notification
                        if user_api.status_code not in (200, 201, 202) \
                                and tech_user_log:
                            for user in self.env['webshop.fail.notification'] \
                                    .sudo().search([]):
                                if user.email:
                                    tech_user_log.sudo().action_send_fail_notification_mail \
                                        (lang=user.user_id.partner_id.lang,
                                         email=user.email,
                                         user=user.user_id.name,
                                         cname=partner.name,
                                         cid=partner.id,
                                         pname=partner.parent_id.name,
                                         pid=partner.parent_id.id,
                                         synctime=time,
                                         response=user_api.content,
                                         api_name='Create User Api')
                        _logger.info('USER POST ---------------> %s',
                                     user_api)
                        _logger.info(
                            'USER POST RESULT ---------------> %s',
                            user_api.content)
                    elif method == 'write':
                        user_put_link = user_api_link + \
                                        str(partner.webshop_import_key) + \
                                        '/'
                        user_api = requests.put(url=user_put_link,
                                                 data=user_data,
                                                 headers=headers,
                                                 verify=False)
                        # Technical API Log
                        tech_user_log = partner.sudo().create_technical_log_api(
                            request_method='PUT',
                            request_type='USER',
                            request_url=user_put_link,
                            request_headers=headers,
                            request_response=user_api.content,
                            request_uid=self.env.uid,
                            request_status=user_api.status_code,
                            request_time=time,
                            request_arguments=user_api,
                            request_direction='outgoing')

                        # User Log
                        if user_api.status_code in (200, 201, 202):
                            status = 'successful'
                        else:
                            status = 'failed'
                        user_log = {
                            'user_name': partner.id,
                            'user_id': partner.parent_id.id,
                            'parent_company_name': partner.parent_id.id,
                            'parent_company_id': partner.parent_id.id,
                            'parent_webshop_import_key': partner.parent_id.webshop_import_key,
                            'type': 'POST',
                            'sync_method': 'real_time',
                            'sync_time': time,
                            'sync_status': status,
                            'response_body': user_api.content,
                        }
                        self.env['webshop.user.api.log'].sudo().create(user_log)

                        # Send email notification
                        if user_api.status_code not in (200, 201, 202) \
                                and tech_user_log:
                            for user in self.env['webshop.fail.notification'] \
                                    .sudo().search([]):
                                if user.email:
                                    tech_user_log.sudo().action_send_fail_notification_mail \
                                        (lang=user.user_id.partner_id.lang,
                                         email=user.email,
                                         user=user.user_id.name,
                                         cname=partner.name,
                                         cid=partner.id,
                                         pname=partner.parent_id.name,
                                         pid=partner.parent_id.id,
                                         synctime=time,
                                         response=user_api.content,
                                         api_name='Edit User Api')
                        _logger.info('USER PUT ---------------> %s',
                                     user_api)
                        _logger.info(
                            'USER PUT RESULT ---------------> %s',
                            user_api.content)

        return True

    @api.multi
    def create_technical_log_api(self, request_method=False,
                                 request_type=False,
                                 request_url=False, request_headers=False,
                                 request_response=False, request_uid=False,
                                 request_status=False, request_time=False,
                                 request_arguments=False,
                                 request_direction=False):
        self.ensure_one()
        # Technical API Log
        technical_stat = {
            'request_method': request_method,
            'request_type': request_type,
            'request_url': request_url,
            'request_headers': request_headers,
            'request_response': request_response,
            'request_uid': request_uid,
            'request_status': request_status,
            'request_time': request_time,
            'request_arguments': request_arguments,
            'request_direction': request_direction
        }
        log = self.env['rest.api.log'].sudo().create(technical_stat)
        return log

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                        submenu=False):
        context = dict(self._context)
        ir_model_data = self.env['ir.model.data']
        if context is None:
            context = {}
        res = super(WebshopResPartner, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=submenu)

        customer_id = ir_model_data.get_object_reference('markant_webshop','act_active_customer_sync_cron')[1]
        address_id = ir_model_data.get_object_reference('markant_webshop','act_active_address_sync_cron')[1]
        user_id = ir_model_data.get_object_reference('markant_webshop','act_active_user_sync_cron')[1]
        if res.get('toolbar', {}).get('action', False):
            actions = res.get('toolbar').get('action')
            for action in list(actions):
                if action.get('id', False) == customer_id:
                    res['toolbar']['action'].remove(action)
                if action.get('id', False) == user_id:
                    res['toolbar']['action'].remove(action)
                if action.get('id', False) == address_id:
                    res['toolbar']['action'].remove(action)

        return res
