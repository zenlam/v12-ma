# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.addons.queue_job.job import job
import requests
import logging
import ast
import json
from datetime import datetime, date, timedelta

_logger = logging.getLogger(__name__)


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'
    _description = 'Webshop Related Product Pricelist'

    def set_pricelist_sync_cron_active(self):
        pricelist_sync_cron = self.env.ref(
            'markant_webshop.ir_cron_markant_webshop_pricelist_sync')

        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)], limit=1)

        if api_config and api_config.token and api_config.api_url and \
                api_config.pricelist_end_point:
            headers = {'Authorization': 'Token ' + api_config.token,
                       'Content-Type': 'application/json'}
            pricelist_link = api_config.api_url + api_config.pricelist_end_point

            pricelist_get_api = requests.get(url=pricelist_link,
                                             headers=headers,
                                             verify=False)
            # Get midnight time for today
            today = date.today() + timedelta(days=1)
            midnight = datetime.combine(today, datetime.min.time())

            content = pricelist_get_api.content
            dict_content = content.decode("UTF-8")
            data = json.loads(dict_content)
            if data.get('count') == 0:
                if pricelist_sync_cron.active is False:
                    pricelist_sync_cron.active = True
                    pricelist_sync_cron.numbercall = 1
                    pricelist_sync_cron.nextcall = midnight

        return True

    @api.model
    def _sync_webshop_product_pricelist(self):
        all_pricelist = self.search([])
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)], limit=1)
        if api_config and api_config.token and api_config.api_url and \
                api_config.pricelist_end_point and \
                api_config.product_category_end_point and \
                api_config.api_company:
            headers = {'Authorization': 'Token ' + api_config.token,
                       'Content-Type': 'application/json'}
            pricelist_link = api_config.api_url + api_config.pricelist_end_point

            pricelist_get_api = requests.get(url=pricelist_link,
                                             headers=headers,
                                             verify=False)

            content = pricelist_get_api.content
            dict_content = content.decode("UTF-8")
            data = json.loads(dict_content)
            if data.get('count') == 0:
                retries = api_config.api_attempts
                for pricelist in all_pricelist:
                    pricelist.with_delay(max_retries=retries)\
                        .sync_webshop_product_pricelist_api()
        return True

    # Sync Webshop Product Pricelist
    @api.multi
    @job
    def sync_webshop_product_pricelist_api(self):
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)], limit=1)

        if api_config and api_config.token and api_config.api_url and \
                api_config.pricelist_end_point and \
                api_config.product_category_end_point and \
                api_config.api_company:
            headers = {'Authorization': 'Token ' + api_config.token,
                       'Content-Type': 'application/json'}
            pricelist_link = api_config.api_url + api_config.pricelist_end_point
            product_category_link = api_config.api_url + api_config.product_category_end_point

            for pricelist in self:
                json_payload = {}
                categ_contracts = []
                item_id = []
                json_payload.update({
                    'key': pricelist.id,
                    'type': 'group',
                    'name': pricelist.name,
                    'rounding': '0.05',
                    'kind': 'sale',
                    'active': pricelist.active,
                    'currency': str(pricelist.currency_id.name),
                    'company': api_config.api_company
                })

                params = json.dumps(json_payload)
                key = str(pricelist.id)
                time = datetime.now()
                pricelist_api_link = pricelist_link + key + '/'
                pricelist_api = requests.put(url=pricelist_api_link,
                                             data=params,
                                             headers=headers,
                                             verify=False)
                # Technical API Log
                tech_pricelist_log = pricelist.sudo().create_technical_log_api(
                    request_method='PUT',
                    request_type='Pricelist',
                    request_url=pricelist_api_link,
                    request_headers=headers,
                    request_response=pricelist_api.content,
                    request_uid=self.env.uid,
                    request_status=pricelist_api.status_code,
                    request_time=time,
                    request_arguments=pricelist_api,
                    request_direction='outgoing')

                # Pricelist Log
                if pricelist_api.status_code in (200, 201, 202):
                    status = 'successful'
                else:
                    status = 'failed'
                pricelist_log = {
                    'pricelist_id': str(pricelist.id),
                    'pricelist_name': pricelist.name,
                    'type': 'POST',
                    'sync_method': 'real_time',
                    'sync_time': time,
                    'sync_status': status,
                    'response_body': pricelist_api.content,
                }
                self.env['webshop.pricelist.api.log'].sudo().create(
                    pricelist_log)

                # Send email notification
                if pricelist_api.status_code not in (200, 201, 202) \
                        and tech_pricelist_log:
                    for user in self.env['webshop.fail.notification'] \
                            .sudo().search([]):
                        if user.email:
                            tech_pricelist_log.sudo().action_send_fail_notification_mail \
                                (lang=user.user_id.partner_id.lang,
                                 email=user.email,
                                 user=user.user_id.name,
                                 priceid=pricelist.id,
                                 pricename=pricelist.name,
                                 pricecateg=False,
                                 synctime=time,
                                 response=pricelist_api.content,
                                 api_name='Pricelist API Sync')
                _logger.info('PRICELIST POST ---------------> %s',
                             pricelist_api)
                _logger.info(
                    'PRICELIST POST RESULT ---------------> %s',
                    pricelist_api.content)

                for item in pricelist.item_ids:
                    item_id.append(item.id)
                    categ_put = {
                        'key': item.id,
                        'active': 'True'
                    }
                    if item.date_start:
                        categ_put.update({'start_date': datetime.strftime(item.date_start, '%Y-%m-%d')})
                    if item.date_end:
                        categ_put.update({'end_date': datetime.strftime(item.date_end, '%Y-%m-%d')})
                    categ_contracts.append(categ_put)
                    categ_data = json.dumps(categ_put)
                    # PUT pricelist category
                    category_key = str(item.id)
                    time = datetime.now()
                    category_link_api = pricelist_link + \
                                        str(pricelist.id) + \
                                        '/category_contracts/' + \
                                        category_key + \
                                        '/'
                    category_api = requests.put(url=category_link_api,
                                                data=categ_data,
                                                headers=headers,
                                                verify=False)
                    # Technical API Log
                    price_categ_log = pricelist.sudo().create_technical_log_api(
                        request_method='PUT',
                        request_type='Sync All Category Contracts',
                        request_url=category_link_api,
                        request_headers=headers,
                        request_response=category_api.content,
                        request_uid=self.env.uid,
                        request_status=category_api.status_code,
                        request_time=time,
                        request_arguments=categ_data,
                        request_direction='outgoing')

                    # Send email notification
                    if category_api.status_code not in (
                    200, 201) and price_categ_log:
                        for user in self.env[
                            'webshop.fail.notification'] \
                                .sudo().search([]):
                            if user.email:
                                price_categ_log.sudo().action_send_fail_notification_mail \
                                    (lang=user.user_id.partner_id.lang,
                                     email=user.email,
                                     user=user.user_id.name,
                                     priceid=pricelist.id,
                                     pricename=pricelist.name,
                                     pricecateg=False,
                                     synctime=time,
                                     response=category_api.content,
                                     api_name='Pricelist API Item Sync')
                    _logger.info('CONTRACTS PUT ---------------> %s',
                                 category_api)
                    _logger.info('CONTRACTS PUT RESULT ---------------> %s',
                                 category_api.content)

                    # Product Category API
                    if item.categ_id:
                        product_categ = {
                            'key': item.categ_id.id,
                            'name': item.categ_id.name
                        }
                        product_categ_data = json.dumps(product_categ)
                        product_category_key = str(item.categ_id.id)
                        time = datetime.now()
                        product_category_link_api = product_category_link + \
                                                    product_category_key + \
                                                    '/'
                        product_categ_update_api = requests.put(
                            url=product_category_link_api,
                            data=product_categ_data,
                            headers=headers,
                            verify=False)
                        # Technical API Log
                        product_categ_update_log = pricelist.sudo().create_technical_log_api(
                            request_method='PUT',
                            request_type='Sync All Product Category',
                            request_url=product_category_link_api,
                            request_headers=headers,
                            request_response=product_categ_update_api.content,
                            request_uid=self.env.uid,
                            request_status=product_categ_update_api.status_code,
                            request_time=time,
                            request_arguments=categ_data,
                            request_direction='outgoing')

                        _logger.info(
                            'PRODUCT CATEGORY PUT ---------------> %s',
                            product_categ_update_api)
                        _logger.info(
                            'PRODUCT CATEGORY PUT RESULT ---------------> %s',
                            product_categ_update_api.content)

                        categ_line = {'category': item.categ_id.id,
                                      'base': 'sale_price',
                                      'create_netprice': 'False',
                                      'tiers': [{'quantity': item.min_quantity,
                                                 'value': item.percent_price}]
                                      }

                        categ_line_data = json.dumps(categ_line)
                        # PUT pricelist category line
                        category_key = str(item.id)
                        time = datetime.now()
                        category_line_link_api = pricelist_link + \
                                                 str(pricelist.id) + \
                                                 '/category_contracts/' + \
                                                 category_key + \
                                                 '/line/' + \
                                                 str(item.categ_id.id) + \
                                                 '/'
                        categ_lin_update_api = requests.put(
                            url=category_line_link_api,
                            data=categ_line_data,
                            headers=headers,
                            verify=False)
                        # Technical API Log
                        categ_lin_update_log = pricelist.sudo().create_technical_log_api(
                            request_method='PUT',
                            request_type='Sync All Category Line Contracts',
                            request_url=category_line_link_api,
                            request_headers=headers,
                            request_response=categ_lin_update_api.content,
                            request_uid=self.env.uid,
                            request_status=categ_lin_update_api.status_code,
                            request_time=time,
                            request_arguments=categ_data,
                            request_direction='outgoing')

                        # Send email notification
                        if categ_lin_update_api.status_code not in (
                                200, 201) and categ_lin_update_log:
                            for user in self.env[
                                'webshop.fail.notification'] \
                                    .sudo().search([]):
                                if user.email:
                                    categ_lin_update_log.sudo().action_send_fail_notification_mail \
                                        (
                                            lang=user.user_id.partner_id.lang,
                                            email=user.email,
                                            user=user.user_id.name,
                                            priceid=pricelist.id,
                                            pricename=pricelist.name,
                                            pricecateg=False,
                                            synctime=time,
                                            response=categ_lin_update_api.content,
                                            api_name='Pricelist API Item Line Sync')
                        _logger.info('CONTRACTS LINE PUT ---------------> %s',
                                     categ_lin_update_api)
                        _logger.info(
                            'CONTRACTS LINE PUT RESULT ---------------> %s',
                            categ_lin_update_api.content)
        return True

    @api.model
    def create(self, values):
        res = super(ProductPricelist, self).create(values)
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)])
        retries = 0
        if api_config:
            retries = api_config.api_attempts
        res.with_delay(max_retries=retries)\
            .webshop_api_pricelist(method='create', delete_data={})
        return res

    @api.multi
    def write(self, vals):
        res = super(ProductPricelist, self).write(vals)
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)])
        retries = 0
        if api_config:
            retries = api_config.api_attempts
        self.with_delay(max_retries=retries)\
            .webshop_api_pricelist(method='write', delete_data={})
        return res

    @api.multi
    def unlink(self):
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)])
        if api_config:
            retries = api_config.api_attempts
            price_key = str(self.id)
            params = {
                'key': price_key,
                'type': 'group',
                'name': self.name,
                'currency': str(self.currency_id.name),
                'company': api_config.api_company,
                'active': False
            }
            self.with_delay(max_retries=retries)\
                .webshop_api_pricelist(method='delete', delete_data=params)
        return super(ProductPricelist, self).unlink()

    @api.multi
    @job
    def webshop_api_pricelist(self, method, delete_data):
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)], limit=1)

        if api_config and api_config.token and api_config.api_url and \
                api_config.pricelist_end_point and \
                api_config.product_category_end_point and \
                api_config.api_company:
            headers = {'Authorization': 'Token ' + api_config.token,
                       'Content-Type': 'application/json'}
            pricelist_link = api_config.api_url + api_config.pricelist_end_point
            product_category_link = api_config.api_url + \
                                    api_config.product_category_end_point

            for pricelist in self:
                if method == 'delete':
                    # price_key = str(pricelist.id)
                    # params = {
                    #     'key': price_key,
                    #     'type': 'group',
                    #     'name': pricelist.name,
                    #     'currency': str(pricelist.currency_id.id),
                    #     'company': api_config.api_company,
                    #     'active': False
                    # }
                    update_data = json.dumps(delete_data)
                    price_key = str(pricelist.id)
                    time = datetime.now()
                    pricelist_link_api = pricelist_link + price_key + '/'
                    update_api = requests.put(url=pricelist_link_api,
                                              data=update_data,
                                              headers=headers,
                                              verify=False)
                    # Technical API Log
                    update_log = pricelist.sudo().create_technical_log_api(
                        request_method='PUT',
                        request_type='De-activate Pricelist',
                        request_url=pricelist_link_api,
                        request_headers=headers,
                        request_response=update_api.content,
                        request_uid=self.env.uid,
                        request_status=update_api.status_code,
                        request_time=time,
                        request_arguments=update_data,
                        request_direction='outgoing')

                    # Send email notification
                    if update_api.status_code not in (200, 201) and update_log:
                        for user in self.env[
                            'webshop.fail.notification'] \
                                .sudo().search([]):
                            if user.email:
                                update_log.sudo().action_send_fail_notification_mail \
                                    (lang=user.user_id.partner_id.lang,
                                     email=user.email,
                                     user=user.user_id.name,
                                     priceid=pricelist.id,
                                     pricename=delete_data.get('name'),
                                     pricecateg=False,
                                     synctime=time,
                                     response=update_api.content,
                                     api_name='De-Activate Pricelist API')
                    _logger.info('DELETE PUT ---------------> %s', update_api)
                    _logger.info('DELETE PUT RESULT ---------------> %s',
                                 update_api.content)
                else:
                    json_payload = {}
                    categ_contracts = []
                    item_id = []
                    json_payload.update({
                        'key': pricelist.id,
                        'type': 'group',
                        'name': pricelist.name,
                        'rounding': '0.05',
                        'kind': 'sale',
                        'active': pricelist.active,
                        'currency': str(pricelist.currency_id.name),
                        'company': api_config.api_company
                    })

                    params = json.dumps(json_payload)
                    key = str(pricelist.id)
                    time = datetime.now()
                    pricelist_api_link = pricelist_link + key + '/'
                    if method == 'write':
                        pricelist_api = requests.put(url=pricelist_api_link,
                                                     data=params,
                                                     headers=headers,
                                                     verify=False)
                        # Technical API Log
                        tech_pricelist_log = pricelist.sudo().create_technical_log_api(
                            request_method='PUT',
                            request_type='Pricelist',
                            request_url=pricelist_api_link,
                            request_headers=headers,
                            request_response=pricelist_api.content,
                            request_uid=self.env.uid,
                            request_status=pricelist_api.status_code,
                            request_time=time,
                            request_arguments=pricelist_api,
                            request_direction='outgoing')

                        # Pricelist Log
                        if pricelist_api.status_code in (200, 201, 202):
                            status = 'successful'
                        else:
                            status = 'failed'
                        pricelist_log = {
                            'pricelist_id': str(pricelist.id),
                            'pricelist_name': pricelist.name,
                            'type': 'PUT',
                            'sync_method': 'real_time',
                            'sync_time': time,
                            'sync_status': status,
                            'response_body': pricelist_api.content,
                        }
                        self.env['webshop.pricelist.api.log'].sudo().create(pricelist_log)

                        # Send email notification
                        if pricelist_api.status_code not in (200, 201, 202) \
                                and tech_pricelist_log:
                            for user in self.env['webshop.fail.notification'] \
                                    .sudo().search([]):
                                if user.email:
                                    tech_pricelist_log.sudo().action_send_fail_notification_mail \
                                        (lang=user.user_id.partner_id.lang,
                                         email=user.email,
                                         user=user.user_id.name,
                                         priceid=pricelist.id,
                                         pricename=pricelist.name,
                                         pricecateg=False,
                                         synctime=time,
                                         response=pricelist_api.content,
                                         api_name='Create/Update Pricelist API')
                        _logger.info('Pricelist PUT ---------------> %s',
                                     pricelist_api)
                        _logger.info('PRICELIS PUT RESULT ---------------> %s',
                                     pricelist_api.content)
                    else:
                        pricelist_api = requests.put(url=pricelist_api_link,
                                                     data=params,
                                                     headers=headers,
                                                     verify=False)
                        # Technical API Log
                        tech_pricelist_log = pricelist.sudo().create_technical_log_api(
                            request_method='PUT',
                            request_type='Pricelist',
                            request_url=pricelist_api_link,
                            request_headers=headers,
                            request_response=pricelist_api.content,
                            request_uid=self.env.uid,
                            request_status=pricelist_api.status_code,
                            request_time=time,
                            request_arguments=pricelist_api,
                            request_direction='outgoing')

                        # Pricelist Log
                        if pricelist_api.status_code in (200, 201, 202):
                            status = 'successful'
                        else:
                            status = 'failed'
                        pricelist_log = {
                            'pricelist_id': str(pricelist.id),
                            'pricelist_name': pricelist.name,
                            'pricelist_item_id': item_id,
                            'type': 'POST',
                            'sync_method': 'real_time',
                            'sync_time': time,
                            'sync_status': status,
                            'response_body': pricelist_api.content,
                        }
                        self.env['webshop.pricelist.api.log'].sudo().create(
                            pricelist_log)

                        # Send email notification
                        if pricelist_api.status_code not in (200, 201, 202) \
                                and tech_pricelist_log:
                            for user in self.env['webshop.fail.notification'] \
                                    .sudo().search([]):
                                if user.email:
                                    tech_pricelist_log.sudo().action_send_fail_notification_mail \
                                        (lang=user.user_id.partner_id.lang,
                                         email=user.email,
                                         user=user.user_id.name,
                                         priceid=pricelist.id,
                                         pricename=pricelist.name,
                                         pricecateg=item_id,
                                         synctime=time,
                                         response=pricelist_api.content,
                                         api_name='Create/Update Pricelist API')
                        _logger.info('PRICELIST POST ---------------> %s',
                                     pricelist_api)
                        _logger.info(
                            'PRICELIST POST RESULT ---------------> %s',
                            pricelist_api.content)

                    for item in pricelist.item_ids:
                        item_id.append(item.id)
                        categ_put = {
                            'key': item.id,
                            'active': 'True'
                        }
                        if item.date_start:
                            categ_put.update({'start_date': datetime.strftime(
                                item.date_start, '%Y-%m-%d')})
                        if item.date_end:
                            categ_put.update({'end_date': datetime.strftime(
                                item.date_end, '%Y-%m-%d')})
                        categ_contracts.append(categ_put)
                        categ_data = json.dumps(categ_put)

                        if method == 'write':
                            del_categ_link = pricelist_link + \
                                             str(pricelist.id) + \
                                             '/category_contracts/' + \
                                             str(item.id) + \
                                             '/'
                            delete_categ_api = requests.delete(url=del_categ_link,
                                                               headers=headers,
                                                               verify=False)
                            _logger.info('DELETE PRICELIST CATEGOEY ---------------> %s',
                                         delete_categ_api)
                            _logger.info(
                                'DELETE PRICELIST CATEGOEY ---------------> %s',
                                delete_categ_api.content)

                        # PUT pricelist category
                        category_key = str(item.id)
                        time = datetime.now()
                        category_link_api = pricelist_link + \
                                            str(pricelist.id) + \
                                            '/category_contracts/' + \
                                            category_key + \
                                            '/'
                        category_api = requests.put(url=category_link_api,
                                                    data=categ_data,
                                                    headers=headers,
                                                    verify=False)
                        # Technical API Log
                        price_categ_log = pricelist.sudo().create_technical_log_api(
                            request_method='PUT',
                            request_type='Update Category Contracts',
                            request_url=category_link_api,
                            request_headers=headers,
                            request_response=category_api.content,
                            request_uid=self.env.uid,
                            request_status=category_api.status_code,
                            request_time=time,
                            request_arguments=categ_data,
                            request_direction='outgoing')

                        # Send email notification
                        if category_api.status_code not in (200, 201) and price_categ_log:
                            for user in self.env[
                                'webshop.fail.notification'] \
                                    .sudo().search([]):
                                if user.email:
                                    price_categ_log.sudo().action_send_fail_notification_mail \
                                        (lang=user.user_id.partner_id.lang,
                                         email=user.email,
                                         user=user.user_id.name,
                                         priceid=pricelist.id,
                                         pricename=pricelist.name,
                                         pricecateg=item.name,
                                         synctime=time,
                                         response=category_api.content,
                                         api_name='Create/Update Pricelist API')
                        _logger.info('CONTRACTS PUT ---------------> %s', category_api)
                        _logger.info('CONTRACTS PUT RESULT ---------------> %s',
                                     category_api.content)

                        # Product Category API
                        if item.categ_id:
                            product_categ = {
                                'key': item.categ_id.id,
                                'name': item.categ_id.name
                            }
                            product_categ_data = json.dumps(product_categ)
                            product_category_key = str(item.categ_id.id)
                            time = datetime.now()
                            product_category_link_api = product_category_link + \
                                                        product_category_key + \
                                                        '/'
                            product_categ_update_api = requests.put(
                                url=product_category_link_api,
                                data=product_categ_data,
                                headers=headers,
                                verify=False)
                            # Technical API Log
                            product_categ_update_log = pricelist.sudo().create_technical_log_api(
                                request_method='PUT',
                                request_type='Update Product Category',
                                request_url=product_category_link_api,
                                request_headers=headers,
                                request_response=product_categ_update_api.content,
                                request_uid=self.env.uid,
                                request_status=product_categ_update_api.status_code,
                                request_time=time,
                                request_arguments=categ_data,
                                request_direction='outgoing')

                            categ_line = {'category': item.categ_id.id,
                                           'base': 'sale_price',
                                           'create_netprice': 'False',
                                           'tiers': [{'quantity': item.min_quantity,
                                                      'value': item.percent_price}]
                                          }

                            categ_line_data = json.dumps(categ_line)
                            # PUT pricelist category line
                            category_key = str(item.id)
                            time = datetime.now()
                            category_line_link_api = pricelist_link + \
                                                     str(pricelist.id) + \
                                                     '/category_contracts/' + \
                                                     category_key + \
                                                     '/line/' + \
                                                     str(item.categ_id.id) + \
                                                     '/'
                            categ_lin_update_api = requests.put(url=category_line_link_api,
                                                      data=categ_line_data,
                                                      headers=headers,
                                                      verify=False)
                            # Technical API Log
                            categ_lin_update_log = pricelist.sudo().create_technical_log_api(
                                request_method='PUT',
                                request_type='Update Category Line Contracts',
                                request_url=category_line_link_api,
                                request_headers=headers,
                                request_response=categ_lin_update_api.content,
                                request_uid=self.env.uid,
                                request_status=categ_lin_update_api.status_code,
                                request_time=time,
                                request_arguments=categ_data,
                                request_direction='outgoing')

                            # Send email notification
                            if categ_lin_update_api.status_code not in (
                            200, 201) and categ_lin_update_log:
                                for user in self.env[
                                    'webshop.fail.notification'] \
                                        .sudo().search([]):
                                    if user.email:
                                        categ_lin_update_log.sudo().action_send_fail_notification_mail \
                                            (
                                                lang=user.user_id.partner_id.lang,
                                                email=user.email,
                                                user=user.user_id.name,
                                                priceid=pricelist.id,
                                                pricename=pricelist.name,
                                                pricecateg=item.name,
                                                synctime=time,
                                                response=categ_lin_update_api.content,
                                                api_name='Create/Update Pricelist Line API')
                            _logger.info('CONTRACTS LINE PUT ---------------> %s',
                                         categ_lin_update_api)
                            _logger.info(
                                'CONTRACTS LINE PUT RESULT ---------------> %s',
                                categ_lin_update_api.content)

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
        res = super(ProductPricelist, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=submenu)

        pricelist_id = ir_model_data.get_object_reference('markant_webshop', 'act_active_pricelist_sync_cron')[1]
        if res.get('toolbar', {}).get('action', False):
            actions = res.get('toolbar').get('action')
            for action in list(actions):
                if action.get('id', False) == pricelist_id:
                    res['toolbar']['action'].remove(action)
        return res


class PricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    def unlink(self):
        item_id = self.id
        pricelist = self.pricelist_id
        categ_name = self.categ_id.name

        res = super(PricelistItem, self).unlink()

        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)])

        if api_config and api_config.token and api_config.api_url and \
                api_config.pricelist_end_point:
            headers = {'Authorization': 'Token ' + api_config.token,
                       'Content-Type': 'application/json'}
            pricelist_link = api_config.api_url + api_config.pricelist_end_point
            del_categ_link = pricelist_link + \
                             str(pricelist.id) + \
                             '/category_contracts/' + \
                             str(item_id) + \
                             '/'
            time = datetime.now()
            delete_categ_api = requests.delete(url=del_categ_link,
                                               headers=headers,
                                               verify=False)
            delete_log = pricelist.sudo().create_technical_log_api(
                request_method='DELETE',
                request_type='Pricelist Item',
                request_url=del_categ_link,
                request_headers=headers,
                request_response=delete_categ_api.content,
                request_uid=self.env.uid,
                request_status=delete_categ_api.status_code,
                request_time=time,
                request_arguments='DELETE',
                request_direction='outgoing')

            if delete_categ_api.status_code in (200, 204):
                status = 'successful'
            else:
                status = 'failed'
            pricelist_log = {
                'pricelist_id': str(pricelist.id),
                'pricelist_name': categ_name,
                'type': 'DELETE',
                'sync_method': 'real_time',
                'sync_time': time,
                'sync_status': status,
                'response_body': delete_categ_api.content,
            }
            self.env['webshop.pricelist.api.log'].sudo().create(pricelist_log)

            # Send email notification
            if delete_categ_api.status_code not in (200, 201, 204) \
                    and delete_log:
                for user in self.env['webshop.fail.notification'] \
                        .sudo().search([]):
                    if user.email:
                        delete_log.sudo().action_send_fail_notification_mail \
                            (lang=user.user_id.partner_id.lang,
                             email=user.email,
                             user=user.user_id.name,
                             product=categ_name,
                             internal=False,
                             synctime=time,
                             response=delete_categ_api.content,
                             api_name='Delete Pricelist Item')
            _logger.info('DELETE PRICELIST ITEM ---------------> %s', delete_categ_api)
            _logger.info('DELETE PRICELIST ITEM RESULT ---------------> %s',
                         delete_categ_api.content)

        return res
