# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import except_orm, UserError
from odoo.tools import ustr
from datetime import datetime
import requests


class WebshopApiConfig(models.Model):
    _name = "webshop.api.config"
    _description = "Api Configuration For Webshop"

    # General Fields
    api_party = fields.Char(string='API Party', required=True)
    short_code = fields.Char(string='Short Code', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True)
    api_url = fields.Char(string='API URL', requried=True)
    token = fields.Char(string='Token', required=True)
    origin_code = fields.Char(string='Origin Code', required=True)
    api_attempts = fields.Integer(string='Number of Attempts of API Call')
    repeat_attempts = fields.Integer(string='Repeat Attempts after (mins)')
    api_company = fields.Char(string='Company API')
    api_warehouse = fields.Char(string='Warehouse', required=True)

    # Product Tab
    product_end_point = fields.Char(string='Product End Point')
    brand_end_point = fields.Char(string='Brand End Point')
    uom_end_point = fields.Char(string='UOM End Point')
    product_category_end_point = fields.Char(string='ProductCategory End Point')
    tree_category_end_point = fields.Char(string='TreeCategories End Point')
    attribute_property_end_point = fields.Char(
        string='AttributeProperty End Point'
    )
    tag_end_point = fields.Char(string='Tags End Point')
    catalog_end_point = fields.Char(string='Catalog End Point')
    attribute_list_end_point = fields.Char(string='Attributelist End Point')
    sync_method = fields.Selection([('real_time', 'Real Time')],
                                   readonly=True,
                                   default='real_time')
    active = fields.Boolean('Active')

    # Assets related
    asset_sync_method = fields.Selection([('real_time', 'Real Time')],
                                         readonly=True,
                                         default='real_time')
    assets_end_point = fields.Char(string='Assets End Point')
    more_assets_path = fields.Char(string='More Assets Path')

    # Pricelist related
    pricelist_end_point = fields.Char(string='Pricelist End Point')
    pricelist_sync_method = fields.Selection([('real_time', 'Real Time')],
                                             readonly=True,
                                             default='real_time')

    # Customer related
    customer_end_point = fields.Char(string='Customer End Point')
    customer_sync_method = fields.Selection([('real_time', 'Real Time')],
                                            readonly=True,
                                            default='real_time')

    # Address related
    address_end_point = fields.Char(string='Address End Point')
    address_sync_method = fields.Selection([('real_time', 'Real Time')],
                                           readonly=True,
                                           default='real_time')

    # User Related
    user_end_point = fields.Char(string='User End Point')
    user_sync_method = fields.Selection([('real_time', 'Real Time')],
                                        readonly=True,
                                        default='real_time')
    default_web_id = fields.Integer(string='Default Webshop ID', default=1)
    default_role_id = fields.Integer(string='Default role ID', default=1)

    # Log Cleaning
    api_log_keeping = fields.Integer(string='API Log Keeping (Days)')

    @api.constrains('active')
    def active_constrains(self):
        record = self.search([])
        if len(record) > 1:
            raise UserError(_('You can only have 1 active API Config at a time!'))
        return True

    @api.model
    def _clean_api_log(self):
        today = datetime.now()
        active_rec = self.search([('active', '=', True)])
        log_keeping_days = active_rec.api_log_keeping

        # Clean technical log
        tech_logs = self.env['rest.api.log'].search([])
        for tech in tech_logs:
            diff = today - tech.create_date
            if diff.days >= log_keeping_days:
                tech.unlink()

        # Clean Product API Log
        product_logs = self.env['webshop.api.log'].search([])
        for prod in product_logs:
            diff = today - prod.create_date
            if diff.days >= log_keeping_days:
                prod.unlink()

        # Clean Pricelist API Log
        pricelist_logs = self.env['webshop.pricelist.api.log'].search([])
        for price in pricelist_logs:
            diff = today - price.create_date
            if diff.days >= log_keeping_days:
                price.unlink()

        # Clean Asset API Log
        asset_logs = self.env['webshop.asset.api.log'].search([])
        for asset in asset_logs:
            diff = today - asset.create_date
            if diff.days >= log_keeping_days:
                asset.unlink()

        # Clean Asset API Log
        asset_logs = self.env['webshop.asset.api.log'].search([])
        for asset in asset_logs:
            diff = today - asset.create_date
            if diff.days >= log_keeping_days:
                asset.unlink()

        # Clean Customer API Log
        customer_logs = self.env['webshop.customer.api.log'].search([])
        for customer in customer_logs:
            diff = today - customer.create_date
            if diff.days >= log_keeping_days:
                customer.unlink()

        # Clean Address API Log
        address_logs = self.env['webshop.address.api.log'].search([])
        for address in address_logs:
            diff = today - address.create_date
            if diff.days >= log_keeping_days:
                address.unlink()

        # Clean User API Log
        user_logs = self.env['webshop.user.api.log'].search([])
        for user in user_logs:
            diff = today - user.create_date
            if diff.days >= log_keeping_days:
                user.unlink()

        # Clean Stock API Log
        stock_logs = self.env['webshop.stock.api.log'].search([])
        for stock in stock_logs:
            diff = today - stock.create_date
            if diff.days >= log_keeping_days:
                stock.unlink()

        # Clean Queue Job Log
        queue_logs = self.env['queue.job'].search([('state', '=', 'done')])
        for queue in queue_logs:
            diff = today - queue.date_created
            if diff.days >= log_keeping_days:
                queue.unlink()

        return True

    @api.multi
    def test_api_connection(self):
        for config in self:
            if config.token:
                headers = {'Authorization': 'Token ' + config.token,
                           'Content-Type': 'application/json'}
            else:
                raise UserError(_('Please configure the Token for the API Configuration'))

            if not config.api_url:
                raise UserError(_('Please configure the API URL for the API Configuration'))

            try:
                raise_warning = False
                msg = 'Connection Failed \n'
                # Product End Point
                if config.product_end_point:
                    api_code = requests.get(
                        url=config.api_url + config.product_end_point,
                        headers=headers,
                        verify=False)
                    if api_code.status_code != 200:
                        raise_warning = True
                        msg += ' - Something is wrong with Product ' \
                               'End Point Url \n'

                # Brand End Point
                if config.brand_end_point:
                    api_code = requests.get(
                        url=config.api_url + config.brand_end_point,
                        headers=headers,
                        verify=False)
                    if api_code.status_code != 200:
                        raise_warning = True
                        msg += ' - Something is wrong with Brand ' \
                               'End Point Url \n'

                # UOM End Point
                if config.uom_end_point:
                    api_code = requests.get(
                        url=config.api_url + config.uom_end_point,
                        headers=headers,
                        verify=False)
                    if api_code.status_code != 200:
                        raise_warning = True
                        msg += ' - Something is wrong with UOM ' \
                               'End Point Url \n'

                # Product Category End Point
                if config.product_category_end_point:
                    api_code = requests.get(
                        url=config.api_url + config.product_category_end_point,
                        headers=headers,
                        verify=False)
                    if api_code.status_code != 200:
                        raise_warning = True
                        msg += ' - Something is wrong with Product Category ' \
                               'End Point Url \n'

                # Tree Categories End Point
                if config.tree_category_end_point:
                    api_code = requests.get(
                        url=config.api_url + config.tree_category_end_point,
                        headers=headers,
                        verify=False)
                    if api_code.status_code != 200:
                        raise_warning = True
                        msg += ' - Something is wrong with Tree Categories ' \
                               'End Point Url \n'

                # Attribute Property End Point
                if config.attribute_property_end_point:
                    api_code = requests.get(
                        url=config.api_url + config.attribute_property_end_point,
                        headers=headers,
                        verify=False)
                    if api_code.status_code != 200:
                        raise_warning = True
                        msg += ' - Something is wrong with Attribute Property ' \
                               'End Point Url \n'

                # Tags End Point
                if config.tag_end_point:
                    api_code = requests.get(
                        url=config.api_url + config.tag_end_point,
                        headers=headers,
                        verify=False)
                    if api_code.status_code != 200:
                        raise_warning = True
                        msg += ' - Something is wrong with Tags ' \
                               'End Point Url \n'

                # Catalog End Point
                if config.uom_end_point:
                    api_code = requests.get(
                        url=config.api_url + config.uom_end_point,
                        headers=headers,
                        verify=False)
                    if api_code.status_code != 200:
                        raise_warning = True
                        msg += ' - Something is wrong with Catalog ' \
                               'End Point Url \n'

                # Assets End Point
                if config.assets_end_point:
                    api_code = requests.get(
                        url=config.api_url + config.assets_end_point,
                        headers=headers,
                        verify=False)
                    if api_code.status_code != 200:
                        raise_warning = True
                        msg += ' - Something is wrong with Assets ' \
                               'End Point Url \n'

                # Pricelist End Point
                if config.pricelist_end_point:
                    api_code = requests.get(
                        url=config.api_url + config.pricelist_end_point,
                        headers=headers,
                        verify=False)
                    if api_code.status_code != 200:
                        raise_warning = True
                        msg += ' - Something is wrong with Pricelist ' \
                               'End Point Url \n'

                # Customer End Point
                if config.customer_end_point:
                    api_code = requests.get(
                        url=config.api_url + config.customer_end_point,
                        headers=headers,
                        verify=False)
                    if api_code.status_code != 200:
                        raise_warning = True
                        msg += ' - Something is wrong with Customer ' \
                               'End Point Url \n'

                # Address End Point
                if config.address_end_point:
                    api_code = requests.get(
                        url=config.api_url + config.address_end_point,
                        headers=headers,
                        verify=False)
                    if api_code.status_code != 200:
                        raise_warning = True
                        msg += ' - Something is wrong with Address ' \
                               'End Point Url \n'

                # User End Point
                if config.user_end_point:
                    api_code = requests.get(
                        url=config.api_url + config.user_end_point,
                        headers=headers,
                        verify=False)
                    if api_code.status_code != 200:
                        raise_warning = True
                        msg += ' - Something is wrong with User ' \
                               'End Point Url \n'

                if raise_warning is True:
                    raise UserError(_(msg))

            except UserError as e:
                # let UserErrors (messages) bubble up
                raise e
            except Exception as e:
                raise UserError(_(
                    "Connection Test Failed! Here is what we got instead:\n %s") % ustr(
                    e))
        raise UserError(
            _("Connection Test Succeeded! Everything seems properly set up!"))


class WebshopApiLog(models.Model):
    _name = "webshop.api.log"
    _description = "API Log of webshop"
    _order = 'create_date desc'

    internal_ref = fields.Char(string='Internal Reference')
    type = fields.Char(string='Request Method')
    product_id = fields.Many2one('product.product', string='Name')
    attribute_values = fields.Many2many('webshop.attribute.value',
                                        string='Attribute Values')
    sync_method = fields.Selection([('real_time', 'Real Time')],
                                   string='Sync Method')
    sync_time = fields.Datetime(string='Sync Time')
    sync_status = fields.Selection([('successful', 'Successfull'),
                                    ('failed', 'Failed')],
                                   string='Sync Status')
    response_body = fields.Text(string='Response Body')


class WebshopAssetApiLog(models.Model):
    _name = "webshop.asset.api.log"
    _description = "Asset API Log of webshop"
    _order = 'create_date desc'

    internal_ref = fields.Char(string='Internal Reference')
    type = fields.Char(string='Request Method')
    product_id = fields.Many2one('product.product', string='Name')
    asset = fields.Char(string='Asset')
    attribute_values = fields.Many2many('webshop.attribute.value',
                                        string='Attribute Values')
    sync_method = fields.Selection([('real_time', 'Real Time')],
                                   string='Sync Method')
    sync_time = fields.Datetime(string='Sync Time')
    sync_status = fields.Selection([('successful', 'Successfull'),
                                    ('failed', 'Failed')],
                                   string='Sync Status')
    response_body = fields.Text(string='Response Body')


class WebshopPricelistApiLog(models.Model):
    _name = "webshop.pricelist.api.log"
    _description = "Pricelist API Log of webshop"
    _order = 'create_date desc'

    pricelist_id = fields.Char('Pricelist ID')
    pricelist_name = fields.Char('Pricelist Name')
    categ_pricelist = fields.Many2one('product.category',
                                      string='Category of Pricelist Item')
    type = fields.Char(string='Request Method')
    sync_method = fields.Selection([('real_time', 'Real Time')],
                                   string='Sync Method')
    sync_time = fields.Datetime(string='Sync Time')
    sync_status = fields.Selection([('successful', 'Successfull'),
                                    ('failed', 'Failed')],
                                   string='Sync Status')
    response_body = fields.Text(string='Response Body')


class WebshopCustomerApiLog(models.Model):
    _name = "webshop.customer.api.log"
    _description = "Customer API Log of Webshop"
    _order = 'create_date desc'

    customer_name = fields.Many2one('res.partner', string='Customer Name')
    customer_id = fields.Integer(string='Customer ID')
    webshop_import_key = fields.Char(string='Webshop Import Key')
    customer_email = fields.Char(string='Email')
    type = fields.Char(string='Request Method')
    sync_method = fields.Selection([('real_time', 'Real Time')],
                                   string='Sync Method')
    sync_time = fields.Datetime(string='Sync Time')
    sync_status = fields.Selection([('successful', 'Successfull'),
                                    ('failed', 'Failed')],
                                   string='Sync Status')
    response_body = fields.Text(string='Response Body')


class WebshopAddressApiLog(models.Model):
    _name = "webshop.address.api.log"
    _description = "Address API Log of Webshop"
    _order = 'create_date desc'

    address_name = fields.Many2one('res.partner', string='Address Name')
    parent_address_name = fields.Many2one('res.partner', string='Parent Address Name')
    address_id = fields.Integer(string='Address ID')
    webshop_import_key = fields.Char(string='Webshop Import Key')
    default_address = fields.Char(string='Default Address')
    type = fields.Char(string='Request Method')
    sync_method = fields.Selection([('real_time', 'Real Time')],
                                   string='Sync Method')
    sync_time = fields.Datetime(string='Sync Time')
    sync_status = fields.Selection([('successful', 'Successfull'),
                                    ('failed', 'Failed')],
                                   string='Sync Status')
    response_body = fields.Text(string='Response Body')


class WebshopUserApiLog(models.Model):
    _name = "webshop.user.api.log"
    _description = "User API Log of Webshop"
    _order = 'create_date desc'

    user_name = fields.Many2one('res.partner', string='User Contact Name')
    user_id = fields.Integer(string='User Contact ID')
    parent_company_name = fields.Many2one('res.partner', string='Parent Company Name')
    parent_company_id = fields.Integer(string='Parent Company ID')
    parent_webshop_import_key = fields.Char(string='Parent Company Webshop Import Key')
    type = fields.Char(string='Request Method')
    sync_method = fields.Selection([('real_time', 'Real Time')],
                                   string='Sync Method')
    sync_time = fields.Datetime(string='Sync Time')
    sync_status = fields.Selection([('successful', 'Successfull'),
                                    ('failed', 'Failed')],
                                   string='Sync Status')
    response_body = fields.Text(string='Response Body')


class WebshopTechnicalLog(models.Model):
    _name = "rest.api.log"
    _description = "Track all API call"
    _order = 'create_date desc'

    request_method = fields.Char(string='Request Method')
    request_type = fields.Char(string='Request Type')
    request_url = fields.Char(string='Request URL')
    request_headers = fields.Char(string='Request Headers')
    request_response = fields.Char(string='Request Response')
    request_uid = fields.Many2one('res.users', string='Request User')
    request_status = fields.Char(string='Request Status')
    request_time = fields.Datetime(string='Request Time')
    request_arguments = fields.Char(string='Request Arguments')
    request_direction = fields.Selection([('incoming', 'Incoming'),
                                          ('outgoing', 'Outgoing')],
                                         string='Direction',
                                         default='incoming',
                                         required=1)
    current_retry = fields.Integer(string='Number of Retry', default=-1)

    @api.multi
    def action_send_fail_notification_mail(self, lang=False, email=None,
                                           user=False, product=False,
                                           internal=False, synctime=False,
                                           response=False, api_name=False,
                                           cname=False, cid=False, pname=False,
                                           pid=False, aname=False, aid=False,
                                           wik=False, atype=False,
                                           aparent=False, cusid=False,
                                           cusname=False, priceid=False,
                                           pricename=False, pricecateg=False):
        self.ensure_one()
        try:
            template = self.env.ref('markant_webshop.email_markant_fail_notif_webshop_api_cs')
        except ValueError:
            template = False

        if email:
            template.with_context(lang=lang, email=email, user=user,
                                  product=product, internal=internal,
                                  synctime=synctime, response=response,
                                  api_name=api_name, cname=cname, cid=cid,
                                  pname=pname, pid=pid, aname=aname, aid=aid,
                                  wik=wik, atype=atype, aparent=aparent,
                                  cusid=cusid, cusname=cusname, priceid=priceid,
                                  pricename=pricename, pricecateg=pricecateg)\
                .send_mail(self.id, force_send=True)
        return True


class WebshopApiFailureNotif(models.Model):
    _name = "webshop.fail.notification"
    _description = "User to contact if API fails"

    user_id = fields.Many2one('res.users', string='Name', required=True)
    email = fields.Char(string='Email', required=True)

    @api.onchange('user_id')
    def onchange_user_id(self):
        if self.user_id:
            self.email = self.user_id.partner_id.email
