from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError, Warning
from odoo.addons.queue_job.job import job
import requests
import logging
import json
from datetime import datetime
_logger = logging.getLogger(__name__)


class ProductMainPictures(models.Model):
    _name = 'product.main.pictures'
    _description = 'Product Main Pictures'

    def _get_main_pic_extension(self):
        ext = self.env['file.extension.config'].search([
            ('default_main_picture', '=', True)], limit=1)
        if ext:
            return ext.id
        else:
            return False

    product_tmpl_id = fields.Many2one('product.template', string='Product Template', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', ondelete='cascade')
    article_number = fields.Char(string='Article Number', compute='link_product', store=True)
    extension_id = fields.Many2one('file.extension.config', compute='link_product', store=True, string='Extension')
    main_filename = fields.Char(string='Filename', compute='link_product', store=True)

    @api.depends('product_tmpl_id.main_pic_article_number',
                 'product_tmpl_id.main_pic_extension_id',
                 'product_id.main_pic_article_number_variant',
                 'product_id.main_pic_extension_id_variant')
    def link_product(self):
        for rec in self:
            if rec.product_id:
                rec.article_number = rec.product_id.main_pic_article_number_variant
                rec.extension_id = rec.product_id.main_pic_extension_id_variant.id
                rec.main_filename = rec.product_id.main_filename_variant
            elif rec.product_tmpl_id:
                rec.article_number = rec.product_tmpl_id.main_pic_article_number
                rec.extension_id = rec.product_tmpl_id.main_pic_extension_id.id
                rec.main_filename = rec.product_tmpl_id.main_filename


class ProductMorePictures(models.Model):
    _name = 'product.more.pictures'
    _description = 'Product More Pictures'
    _rec_name = 'article_number'

    def _get_more_pic_extension(self):
        ext = self.env['file.extension.config'].search([
            ('default_more_picture', '=', True)], limit=1)
        if ext:
            return ext.id
        else:
            return False

    def _get_sequence_number(self):
        for rec in self:
            if rec.product_tmpl_id:
                more_pic_ids = rec.product_tmpl_id.more_pic_ids
            else:
                more_pic_ids = rec.product_id.more_pic_ids_variant
            rec.sequence = 1
            if rec.id and isinstance(rec.id, int):
                rec.sequence = more_pic_ids.ids.index(
                    rec.id) + 1

    product_tmpl_id = fields.Many2one('product.template',
                                      string='Product Template',
                                      ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product',
                                 ondelete='cascade')
    sequence = fields.Integer(string='No', compute='_get_sequence_number')
    article_number = fields.Char(string='Article Number',
                                 required=True)
    extension_id = fields.Many2one('file.extension.config', string='Extension',
                                   required=True,
                                   domain=[('more_picture', '=', True)],
                                   default=_get_more_pic_extension)
    more_filename = fields.Char(string='Filename',
                                compute='compute_more_filename',
                                store=True)

    @api.depends('article_number', 'extension_id')
    def compute_more_filename(self):
        for rec in self:
            extension_name = str(rec.extension_id.name) or ''
            article_number = str(rec.article_number) or ''
            sequence = str(rec.sequence)
            rec.more_filename = article_number + \
                                '-' + \
                                sequence + \
                                '.' + \
                                extension_name

    def unlink(self):
        more_id = 'more-' + str(self.id)
        more_name = self.more_filename
        prod_id = self.product_id
        res = super(ProductMorePictures, self).unlink()
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)])
        if api_config and api_config.token and api_config.api_url and \
                api_config.assets_end_point:
            headers = {'Authorization': 'Token ' + api_config.token,
                       'Content-Type': 'application/json'}

            asset_link = api_config.api_url + api_config.assets_end_point
            time = datetime.now()
            delete_link = asset_link + more_id + '/'
            delete_more_api = requests.delete(url=delete_link,
                                              headers=headers,
                                              verify=False)
            more_asset_log = prod_id.sudo().create_technical_log_api(
                request_method='DELETE',
                request_type='More Picture',
                request_url=delete_link,
                request_headers=headers,
                request_response=delete_more_api.content,
                request_uid=self.env.uid,
                request_status=delete_more_api.status_code,
                request_time=time,
                request_arguments='DELETE',
                request_direction='outgoing')

            if delete_more_api.status_code in (200, 204):
                status = 'successful'
            else:
                status = 'failed'
            asset_log = {
                'internal_ref': '',
                'type': 'DELETE',
                'product_id': None,
                'asset': more_name,
                'sync_method': 'real_time',
                'sync_time': time,
                'sync_status': status,
                'response_body': delete_more_api.content,
            }
            self.env['webshop.asset.api.log'].sudo().create(asset_log)

            # Send email notification
            if delete_more_api.status_code not in (200, 204) \
                    and more_asset_log:
                for user in self.env[
                    'webshop.fail.notification'] \
                        .sudo().search([]):
                    if user.email:
                        more_asset_log.sudo().action_send_fail_notification_mail \
                            (lang=user.user_id.partner_id.lang,
                             email=user.email,
                             user=user.user_id.name,
                             product=prod_id.name,
                             internal=prod_id.default_code,
                             synctime=time,
                             response=delete_more_api.content,
                             api_name='Delete More Picture')
            _logger.info('DELETE MORE ASSET ---------------> %s', delete_more_api)
            _logger.info('DELETE MORE ASSET RESULT ---------------> %s',
                         delete_more_api.content)
        return res


class ProductExtraAssets(models.Model):
    _name = 'product.extra.assets'
    _description = 'Product Extra Assets'
    _rec_name = 'article_number'

    def _get_extra_asset_extension(self):
        ext = self.env['file.extension.config'].search([
            ('default_pdf_setting', '=', True)], limit=1)
        if ext:
            return ext.id
        else:
            return False

    def _get_sequence_number(self):
        for rec in self:
            if rec.product_tmpl_id:
                extra_assets_ids = rec.product_tmpl_id.extra_asset_ids
            else:
                extra_assets_ids = rec.product_id.extra_asset_ids_variant
            rec.sequence = 1
            if rec.id and isinstance(rec.id, int):
                rec.sequence = extra_assets_ids.ids.index(
                    rec.id) + 1

    product_tmpl_id = fields.Many2one('product.template',
                                      string='Product Template',
                                      ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product',
                                 ondelete='cascade')
    sequence = fields.Integer(string='No', compute='_get_sequence_number')
    article_number = fields.Char(string='Document Name',
                                 required=True, copy=False)
    extension_id = fields.Many2one('file.extension.config', string='Extension',
                                   required=True,
                                   domain=[('pdf_setting', '=', True)],
                                   default=_get_extra_asset_extension)
    extra_filename = fields.Char(string='Filename',
                                 compute='compute_extra_filename')
    lang = fields.Selection(selection='_get_languages', string='Language',
                            validate=False)

    @api.model
    def _get_languages(self):
        langs = self.env['res.lang'].search([('translatable', '=', True)])
        return [(lang.code, lang.name) for lang in langs]

    @api.depends('article_number', 'extension_id')
    def compute_extra_filename(self):
        config = self.env['webshop.api.config'].search([('active', '=', True)])
        for rec in self:
            extension_name = str(rec.extension_id.name) or ''
            article_number = str(rec.article_number) or ''
            if config and config.more_assets_path:
                rec.extra_filename = config.more_assets_path + \
                                     article_number + \
                                     '.' + \
                                     extension_name
            else:
                raise Warning(_('Please Configure the More Asset\'s '
                                'Path in Web Api Config'))

    def unlink(self):
        extra_id = 'extra-' + str(self.id)
        extra_name = self.extra_filename
        prod_id = self.product_id
        res = super(ProductExtraAssets, self).unlink()
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)])
        if api_config and api_config.token and api_config.api_url and \
                api_config.assets_end_point:
            headers = {'Authorization': 'Token ' + api_config.token,
                       'Content-Type': 'application/json'}

            asset_link = api_config.api_url + api_config.assets_end_point
            time = datetime.now()
            delete_link = asset_link + extra_id + '/'
            delete_extra_api = requests.delete(url=delete_link,
                                              headers=headers,
                                              verify=False)
            extra_asset_log = prod_id.sudo().create_technical_log_api(
                request_method='DELETE',
                request_type='Extra Picture',
                request_url=delete_link,
                request_headers=headers,
                request_response=delete_extra_api.content,
                request_uid=self.env.uid,
                request_status=delete_extra_api.status_code,
                request_time=time,
                request_arguments='DELETE',
                request_direction='outgoing')

            if delete_extra_api.status_code in (200, 204):
                status = 'successful'
            else:
                status = 'failed'
            asset_log = {
                'internal_ref': '',
                'type': 'DELETE',
                'product_id': None,
                'asset': extra_name,
                'sync_method': 'real_time',
                'sync_time': time,
                'sync_status': status,
                'response_body': delete_extra_api.content,
            }
            self.env['webshop.asset.api.log'].sudo().create(asset_log)

            # Send email notification
            if delete_extra_api.status_code not in (200, 204) \
                    and extra_asset_log:
                for user in self.env[
                    'webshop.fail.notification'] \
                        .sudo().search([]):
                    if user.email:
                        extra_asset_log.sudo().action_send_fail_notification_mail \
                            (lang=user.user_id.partner_id.lang,
                             email=user.email,
                             user=user.user_id.name,
                             product=prod_id.name,
                             internal=prod_id.default_code,
                             synctime=time,
                             response=delete_extra_api.content,
                             api_name='Delete Extra Picture')
            _logger.info('DELETE EXTRA ASSET ---------------> %s', delete_extra_api)
            _logger.info('DELETE EXTRA ASSET RESULT ---------------> %s',
                         delete_extra_api.content)
        return res


class ProductVideos(models.Model):
    _name = 'product.videos'
    _description = 'Product Videos'

    def _get_more_pic_extension(self):
        ext = self.env['file.extension.config'].search([
            ('default_more_picture', '=', True)], limit=1)
        if ext:
            return ext.id
        else:
            return False

    def _get_sequence_number(self):
        for rec in self:
            if rec.product_tmpl_id:
                video_ids = rec.product_tmpl_id.template_video_ids
            else:
                video_ids = rec.product_id.variant_video_ids
            rec.sequence = 1
            if rec.id and isinstance(rec.id, int):
                rec.sequence = video_ids.ids.index(rec.id) + 1

    product_tmpl_id = fields.Many2one('product.template',
                                      string='Product Template',
                                      ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product',
                                 ondelete='cascade')
    sequence = fields.Integer(string='No', compute='_get_sequence_number')
    name = fields.Char(string='Name', required=True)
    identifier = fields.Char(string='Identifier', required=True)
    provider = fields.Char(string='Provider', required=True)
    link = fields.Char(string='Link', required=True)
    video_embed = fields.Boolean(string='Embed the Video')
    lang = fields.Selection(selection='_get_languages', string='Language',
                            validate=False)

    @api.model
    def _get_languages(self):
        langs = self.env['res.lang'].search([('translatable', '=', True)])
        return [(lang.code, lang.name) for lang in langs]

    def unlink(self):
        vid_id = 'vid-' + str(self.id)
        vid_name = self.name
        prod_id = self.product_id
        res = super(ProductVideos, self).unlink()
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)])

        if api_config and api_config.token and api_config.api_url and \
                api_config.assets_end_point:
            headers = {'Authorization': 'Token ' + api_config.token,
                       'Content-Type': 'application/json'}

            asset_link = api_config.api_url + api_config.assets_end_point
            time = datetime.now()
            delete_link = asset_link + vid_id + '/'
            delete_vid_api = requests.delete(url=delete_link,
                                             headers=headers,
                                             verify=False)
            vid_asset_log = prod_id.sudo().create_technical_log_api(
                request_method='DELETE',
                request_type='Video Settings',
                request_url=delete_link,
                request_headers=headers,
                request_response=delete_vid_api.content,
                request_uid=self.env.uid,
                request_status=delete_vid_api.status_code,
                request_time=time,
                request_arguments='DELETE',
                request_direction='outgoing')

            if delete_vid_api.status_code in (200, 204):
                status = 'successful'
            else:
                status = 'failed'
            asset_log = {
                'internal_ref': '',
                'type': 'DELETE',
                'product_id': None,
                'asset': vid_name,
                'sync_method': 'real_time',
                'sync_time': time,
                'sync_status': status,
                'response_body': delete_vid_api.content,
            }
            self.env['webshop.asset.api.log'].sudo().create(asset_log)

            # Send email notification
            if delete_vid_api.status_code not in (200, 204) \
                    and vid_asset_log:
                for user in self.env[
                    'webshop.fail.notification'] \
                        .sudo().search([]):
                    if user.email:
                        vid_asset_log.sudo().action_send_fail_notification_mail \
                            (lang=user.user_id.partner_id.lang,
                             email=user.email,
                             user=user.user_id.name,
                             product=prod_id.name,
                             internal=prod_id.default_code,
                             synctime=time,
                             response=delete_vid_api.content,
                             api_name='Delete More Picture')
            _logger.info('DELETE VID ASSET ---------------> %s', delete_vid_api)
            _logger.info('DELETE VID ASSET RESULT ---------------> %s',
                         delete_vid_api.content)
        return res


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_main_pic_extension(self):
        ext = self.env['file.extension.config'].search([
            ('default_main_picture', '=', True)], limit=1)
        if ext:
            return ext.id
        else:
            return False

    def _get_lowest_child(self):
        all_categ = self.env['product.public.category'].search([])
        filtered_categ = []
        for categ in all_categ:
            if categ not in all_categ.mapped('parent_id'):
                filtered_categ.append(categ.id)
        return [('id', 'in', filtered_categ)]

    # Webshop Product Template Tabs (General)
    webshop_boolean = fields.Boolean(string='Webshop Yes/No', default=False,
                                     copy=False)
    brand_id = fields.Many2one('product.brand', string='Brand', copy=False)
    brand_id_pass_to_variant = fields.Boolean('Brand - Populate to Variant',
                                              default=True, copy=False)
    delivery_service_id = fields.Many2one('webshop.product.delivery',
                                          string='Delivery Service',
                                          copy=False)
    delivery_pass_to_variant = fields.Boolean('Delivery Service - Populate to Variant',
                                              default=True, copy=False)
    order_quantity = fields.Integer(string='Order Quantity', copy=False,
                                    default=1)
    min_order_quantitiy = fields.Integer(string='Minimal Order Quantity',
                                         copy=False, default=1)

    # Webshop Product Template Tabs (Catalog)
    catalog = fields.Selection([('markant_nl', 'Markant NL'),
                                ('markant_mo', 'Markant MO'),
                                ('markant_int', 'Markant INT')],
                               string='Catalog')
    public_categ_ids = fields.Many2many(domain=lambda self: self._get_lowest_child())
    catalog_pass_to_variant = fields.Boolean('Catalog - Populate to Variant',
                                             default=True, copy=False)
    public_categ_ids_pass_to_variant = fields.Boolean(
        'Categories - Populate to Variant', default=True, copy=False)

    # Webshop Product Template Tabs (Texts)
    search_keyword = fields.Char(string='Keyword for Search', copy=False,
                                 translate=True)

    # Webshop Product Template Tabs (Tags)
    webshop_tags_ids = fields.Many2many('webshop.product.tags',
                                        'template_product_webshop_tags_rel',
                                        'template_id', 'tag_ids',
                                        string='Tags', copy=False,
                                        translate=True)

    # Main Picture Assets Fields
    main_pic_id = fields.Many2one('product.main.pictures',
                                  string='Main Picture',
                                  copy=False)
    main_pic_article_number = fields.Char('Article Number')
    main_pic_extension_id = fields.Many2one('file.extension.config',
                                            string='Extension',
                                            domain=[('main_picture', '=',
                                                     True)],
                                            default=_get_main_pic_extension)
    main_filename = fields.Char(string='Filename',
                                compute='compute_filename',
                                store=True)
    main_pic_pass_to_variant = fields.Boolean('Article Number & Ext. '
                                              '- Populate to Variant',
                                              default=True, copy=False)

    # More Picture Assets Fields
    more_pic_ids = fields.One2many('product.more.pictures', 'product_tmpl_id',
                                   string='More Picture(s)', copy=False)

    # Extra Assets Fields
    extra_asset_ids = fields.One2many('product.extra.assets',
                                      'product_tmpl_id',
                                      string='Extra Asset', copy=False)

    more_extra_pass_to_variant = fields.Boolean('More Pictures & Extra Assets '
                                                '- Populate to Variant',
                                                default=True, copy=False)

    # Template Videos
    template_video_ids = fields.One2many('product.videos',
                                         'product_tmpl_id',
                                         string='Video Setting',
                                         copy=False)

    template_video_pass_to_variant = fields.Boolean('Video Settings '
                                                    '- Populate to Variant',
                                                    default=True, copy=False)

    tax_line_ids = fields.One2many('account.invoice.tax', 'invoice_id',
                                   string='Tax Lines', oldname='tax_line',
                                   readonly=True,
                                   states={'draft': [('readonly', False)]},
                                   copy=True)

    # One2many field attributes linked to webshop attributes
    webshop_attributes = fields.One2many('webshop.attribute.value',
                                         'product_tmpl_id')
    webshop_attribute_line_ids = fields.One2many(
        'template.webshop.attribute.line',
        'product_tmpl_id',
        'Product Attributes')
    regular_attribute_line_ids = fields.One2many(
        'template.regular.attribute.line',
        'product_tmpl_id',
        'Product Attributes')

    # Upsell & Cross Sell
    template_alternative_product_ids = fields.Many2many('product.product',
                                                        'template_alternative_rel',
                                                        'src_id', 'dest_id',
                                                        string='Up Sell',
                                                        help='Suggest alternatives to your customer'
                                                             '(upsell strategy).Those product show up on the product page.')
    template_accessory_product_ids = fields.Many2many('product.product',
                                                      'template_accessory_rel',
                                                      'src_id',
                                                      'dest_id',
                                                      string='Cross Sell',
                                                      help='Accessories show up when the customer'
                                                           'reviews the cart before payment (cross-sell strategy).')
    webshop_inventory_availability = fields.Selection([
        ('always',
         'Show inventory on website and prevent sales if not enough stock')],
        string='Inventory Availability',
        help='Adds an inventory availability status on the web product page.')

    @api.depends('main_pic_article_number', 'main_pic_extension_id')
    def compute_filename(self):
        for rec in self:
            # Compute filename
            extension_name = str(rec.main_pic_extension_id.name) or ''
            article_number = str(rec.main_pic_article_number) or ''
            rec.main_filename = article_number + '.' + extension_name

    @api.model_create_multi
    def create(self, vals_list):
        res = super(ProductTemplate, self).create(vals_list)

        if any(len(template.webshop_attribute_line_ids) != len(
                template.webshop_attribute_line_ids.mapped('attribute_id')) for
               template in res):
            raise ValidationError(_(
                'You cannot define two webshop attribute lines for the same attribute.'))

        if any(len(template.regular_attribute_line_ids) != len(
                template.regular_attribute_line_ids.mapped('attribute_id')) for
               template in res):
            raise ValidationError(_(
                'You cannot define two regular attribute lines for the same attribute.'))

        for template in res:
            picture_id = self.env['product.main.pictures'].sudo().create({
                'product_tmpl_id': template.id
            })
            template.sudo().write({
                'main_pic_id': picture_id.id
            })
            # template.webshop_attribute_line_ids = False
            for attribute in template.attribute_line_ids:
                if attribute.attribute_id.webshop_attribute_id:
                    for values in attribute.value_ids:
                        if values.webshop_attribute_value_id:
                            if attribute.attribute_id.webshop_attribute_id \
                                    not in template.webshop_attribute_line_ids \
                                    .mapped('attribute_id'):
                                template.webshop_attribute_line_ids.sudo().create({
                                    'product_tmpl_id': template.id,
                                    'attribute_id': attribute.attribute_id.webshop_attribute_id.id,
                                    'value_ids': [(4,
                                                   values.webshop_attribute_value_id.id)]
                                })
                            else:
                                if values.webshop_attribute_value_id not in \
                                        template.webshop_attribute_line_ids \
                                                .mapped('value_ids') \
                                                .filtered(lambda
                                                                  x: x.attribute_id == attribute.attribute_id.webshop_attribute_id):
                                    template.webshop_attribute_line_ids \
                                        .filtered(lambda
                                                      x: x.attribute_id == attribute.attribute_id.webshop_attribute_id).sudo().write(
                                        {
                                            'value_ids': [(4,
                                                           values.webshop_attribute_value_id.id)]
                                        })
        return res

    def action_update_webshop_attributes(self):
        for template in self:
            template.webshop_attribute_line_ids = False
            for attribute in template.attribute_line_ids:
                if attribute.attribute_id.webshop_attribute_id:
                    for values in attribute.value_ids:
                        if values.webshop_attribute_value_id:
                            if attribute.attribute_id.webshop_attribute_id \
                                    not in template.webshop_attribute_line_ids\
                                    .mapped('attribute_id'):
                                template.webshop_attribute_line_ids.create({
                                    'product_tmpl_id': template.id,
                                    'attribute_id': attribute.attribute_id.webshop_attribute_id.id,
                                    'value_ids': [(4, values.webshop_attribute_value_id.id)]
                                })
                            else:
                                if values.webshop_attribute_value_id not in \
                                        template.webshop_attribute_line_ids\
                                                .mapped('value_ids')\
                                                .filtered(lambda x: x.attribute_id == attribute.attribute_id.webshop_attribute_id):
                                    template.webshop_attribute_line_ids\
                                        .filtered(lambda x: x.attribute_id == attribute.attribute_id.webshop_attribute_id).write({
                                        'value_ids': [(4, values.webshop_attribute_value_id.id)]
                                    })
        return True

    @api.multi
    def write(self, values):
        res = super(ProductTemplate, self).write(values)

        if any(len(template.webshop_attribute_line_ids) != len(
                template.webshop_attribute_line_ids.mapped('attribute_id')) for
               template in self):
            raise ValidationError(_(
                'You cannot define two webshop attribute lines for the same attribute.'))

        if any(len(template.regular_attribute_line_ids) != len(
                template.regular_attribute_line_ids.mapped('attribute_id')) for
               template in self):
            raise ValidationError(_(
                'You cannot define two regular attribute lines for the same attribute.'))

        context = self.env.context
        if not context.get('create_product_product'):
            if not context.get('write_product_product'):
                if values.get('list_price') or values.get('list_price') == 0:
                    self.product_variant_ids.webshop_api_product(
                        method='write', delete=False, delete_response=False)
        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_lowest_child(self):
        all_categ = self.env['product.public.category'].search([])
        filtered_categ = []
        for categ in all_categ:
            if categ not in all_categ.mapped('parent_id'):
                filtered_categ.append(categ.id)
        return [('id', 'in', filtered_categ)]

    # Webshop Product Variant Tabs (General)
    webshop_boolean_variant = fields.Boolean(string='Webshop Yes/No',
                                             default=False, copy=False)
    brand_id_variant = fields.Many2one('product.brand', string='Brand',
                                       copy=False)
    delivery_service_variant_id = fields.Many2one('webshop.product.delivery',
                                                  string='Delivery Service',
                                                  copy=False)
    order_quantity_variant = fields.Integer(string='Order Quantity',
                                            copy=False, default=1)
    min_order_quantitiy_variant = fields.Integer(
        string='Minimal Order Quantity', copy=False, default=1)

    # Webshop Product Variant Tabs (Catalog)
    catalog_variant = fields.Selection(
        [('markant_nl', 'Markant NL'), ('markant_mo', 'Markant MO'),
         ('markant_int', 'Markant INT')], string='Catalog')

    # Webshop Product Product Tabs (Texts)
    ecommerce_name = fields.Text(string='E-commerce Name', copy=False,
                                 translate=True)
    intro_text = fields.Text(string='Intro Text', translate=True)
    category_text = fields.Text(string='Category Text', copy=False,
                                translate=True)
    product_desc = fields.Text(string='Product Description', copy=False,
                               translate=True)
    search_keyword_variant = fields.Char(string='Keyword for Search',
                                         copy=False, translate=True)

    # Webshop Product Product Tabs (Tags)
    webshop_tags_ids_variant = fields.Many2many(
        'webshop.product.tags',
        'product_webshop_tags_variant_rel',
        'product_id', 'tag_id', string='Tags', copy=False,
        translate=True)

    # Main Picture Assets Fields
    main_pic_id_variant = fields.Many2one('product.main.pictures',
                                          string='Main Picture',
                                          copy=False)
    main_pic_article_number_variant = fields.Char(string='Article Number',
                                                  copy=False)
    main_pic_extension_id_variant = fields.Many2one(
        'file.extension.config', string='Extension',
        domain=[('main_picture', '=', True)])
    main_filename_variant = fields.Char(string='Filename',
                                        compute='compute_filename_variant',
                                        store=True)

    # More Picture Assets Fields
    more_pic_ids_variant = fields.One2many(
        'product.more.pictures', 'product_id',
        string='More Picture(s)', copy=False)

    # Extra Assets Fields
    extra_asset_ids_variant = fields.One2many(
        'product.extra.assets', 'product_id',
        string='Extra Asset', copy=False)

    # Product Videos
    variant_video_ids = fields.One2many('product.videos',
                                        'product_id',
                                        string='Video Setting',
                                        copy=False)

    # Public Categories
    public_categ_variant_ids = fields.Many2many(
        'product.public.category', 'public_categ_variant_table',
        'product_id', 'public_categ_id', string='Website Product Category',
        domain=lambda self: self._get_lowest_child())

    # One2many field attributes linked to webshop attributes
    webshop_attributes = fields.One2many('webshop.attribute.value',
                                         'product_id')
    variant_webshop_attribute_line_ids = fields.One2many(
        'product.webshop.attribute.line',
        'product_id',
        'Product Attributes')
    variant_regular_attribute_line_ids = fields.One2many(
        'product.regular.attribute.line',
        'product_id',
        'Product Attributes')

    # Upsell & Cross Sell
    variant_alternative_product_ids = fields.Many2many('product.product',
                                                       'variant_alternative_rel',
                                                       'src_id', 'dest_id',
                                                       string='Up Sell',
                                                       help='Suggest alternatives to your customer'
                                                            '(upsell strategy).Those product show up on the product page.')
    variant_accessory_product_ids = fields.Many2many('product.product',
                                                     'variant_accessory_rel',
                                                     'src_id',
                                                     'dest_id',
                                                     string='Cross Sell',
                                                     help='Accessories show up when the customer'
                                                          'reviews the cart before payment (cross-sell strategy).')
    webshop_inventory_availability_variant = fields.Selection([
        ('always',
         'Show inventory on website and prevent sales if not enough stock')],
        string='Variant Inventory Availability',
        help='Adds an inventory availability status on the web product page.')
    pcf_max_producible_qty = fields.Float('Max Producible Qty')

    @api.depends('main_pic_article_number_variant',
                 'main_pic_extension_id_variant')
    def compute_filename_variant(self):
        for rec in self:
            extension_name = str(rec.main_pic_extension_id_variant.name) or ''
            article_number = str(rec.main_pic_article_number_variant) or ''
            rec.main_filename_variant = article_number + "." + extension_name

    def action_update_variant_webshop_attributes(self):
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)])
        for product in self:
            product.with_context(from_update_button=True).write({
                'variant_webshop_attribute_line_ids': False
            })
            for attr in product.attribute_value_ids:
                if attr.attribute_id.webshop_attribute_id and \
                        attr.webshop_attribute_value_id:
                    if attr.attribute_id.webshop_attribute_id in \
                            product.variant_webshop_attribute_line_ids \
                                    .mapped('attribute_id'):
                        if attr.webshop_attribute_value_id not in \
                                product.variant_webshop_attribute_line_ids \
                                        .mapped('value_ids') \
                                        .filtered(
                                    lambda x: x.attribute_id == attr.attribute_id.webshop_attribute_id):
                            product.variant_webshop_attribute_line_ids.filtered(
                                lambda x: x.attribute_id == attr.attribute_id.webshop_attribute_id)\
                                .with_context(from_update_button=True)\
                                .write({'value_ids': [(4, attr.webshop_attribute_value_id.id)]})
                    else:
                        product.variant_webshop_attribute_line_ids.with_context(from_update_button=True).create({
                            'product_id': product.id,
                            'attribute_id': attr.attribute_id.webshop_attribute_id.id,
                            'value_ids': [(4, attr.webshop_attribute_value_id.id)]
                        })

            if product.webshop_boolean_variant:
                if product.type == 'product' and \
                        product.sale_ok and \
                        product.lst_price > 0 and \
                        product.brand_id_variant and \
                        product.catalog_variant and \
                        product.public_categ_variant_ids and \
                        product.ecommerce_name and \
                        product.product_desc and \
                        product.main_pic_extension_id_variant and \
                        product.main_pic_article_number_variant:
                    retries = 0
                    if api_config:
                        retries = api_config.api_attempts
                    product.with_delay(max_retries=retries) \
                        .webshop_api_product(method='write',
                                             delete=False,
                                             delete_response=False)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        products = super(ProductProduct, self.with_context(
            create_product_product=True)).create(vals_list)
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)])
        context = self.env.context

        if any(len(template.variant_webshop_attribute_line_ids) != len(
                template.variant_webshop_attribute_line_ids.mapped('attribute_id')) for
               template in products):
            raise ValidationError(_(
                'You cannot define two webshop attribute lines for the same attribute.'))

        if any(len(template.variant_regular_attribute_line_ids) != len(
                template.variant_regular_attribute_line_ids.mapped('attribute_id')) for
               template in products):
            raise ValidationError(_(
                'You cannot define two regular attribute lines for the same attribute.'))

        for product in products:
            picture_id = self.env['product.main.pictures'].sudo().create({
                'product_id': product.id
            })
            product.sudo().write({
                'main_pic_id_variant': picture_id.id
            })

            product_tmpl = product.product_tmpl_id

            product.order_quantity_variant = product_tmpl.order_quantity
            product.webshop_inventory_availability_variant = \
                product_tmpl.webshop_inventory_availability
            product.min_order_quantitiy_variant = product_tmpl.min_order_quantitiy
            product.webshop_inventory_availability_variant = \
                product_tmpl.webshop_inventory_availability
            product.search_keyword_variant = product_tmpl.search_keyword
            product.webshop_tags_ids_variant = [
                    (4, tag_id.id, None)
                    for tag_id in product_tmpl.webshop_tags_ids]
            product.variant_alternative_product_ids = [
                (4, upsell_id.id, None) for upsell_id in
                product_tmpl.template_alternative_product_ids]
            product.variant_accessory_product_ids = [
                (4, cross_id.id, None) for cross_id in
                product_tmpl.template_accessory_product_ids]
            if product_tmpl.brand_id_pass_to_variant:
                product.brand_id_variant = product_tmpl.brand_id.id \
                    if product_tmpl.brand_id else False

            if product_tmpl.delivery_pass_to_variant:
                product.delivery_service_variant_id = product_tmpl.delivery_service_id.id \
                    if product_tmpl.delivery_service_id else False

            if product_tmpl.catalog_pass_to_variant:
                product.catalog_variant = product_tmpl.catalog or False
            if product_tmpl.public_categ_ids_pass_to_variant:
                product.sudo().write({
                    'public_categ_variant_ids': [(4, categ_id.id, None) for categ_id in product_tmpl.public_categ_ids]
                })
            more_pic_vals = []
            if product_tmpl.more_extra_pass_to_variant:
                more_pic_vals = [
                    (0, 0, {'product_id': product.id,
                            'article_number': line.article_number,
                            'extension_id': line.extension_id.id
                            })
                    for line in product_tmpl.more_pic_ids]
                product.sudo().write({
                    'extra_asset_ids_variant': [(0, 0, {'product_id': product.id,
                                                        'article_number': line.article_number,
                                                        'extension_id': line.extension_id.id,
                                                        'lang': line.lang})
                                                for line in product_tmpl.extra_asset_ids]
                })
            if product_tmpl.template_video_pass_to_variant:
                product.sudo().write({
                    'variant_video_ids': [
                        (0, 0, {'product_id': product.id,
                                'name': line.name,
                                'identifier': line.identifier,
                                'provider': line.provider,
                                'link': line.link,
                                'video_embed': line.video_embed,
                                'lang': line.lang})
                        for line in product_tmpl.template_video_ids]
                })
            if product.default_code:
                if not product.main_pic_article_number_variant:
                    main_ext = self.env['file.extension.config'].search([
                        ('default_main_picture', '=', True)], limit=1)
                    product.sudo().write({
                        'main_pic_article_number_variant': product.default_code
                    })
                    product.sudo().write({
                        'main_pic_extension_id_variant': main_ext.id if main_ext else False
                    })
            else:
                if product_tmpl.main_pic_pass_to_variant:
                    product.sudo().write({
                        'main_pic_article_number_variant': product_tmpl.main_pic_article_number
                    })
                    product.sudo().write({
                        'main_pic_extension_id_variant':
                            product_tmpl.main_pic_extension_id.id if
                            product_tmpl.main_pic_extension_id else False
                    })

            more_ext = self.env['file.extension.config'].search([
                ('default_more_picture', '=', True)], limit=1)
            if more_ext and product.default_code:
                more_pic_vals.append(
                    (0, 0, {
                        'product_id': product.id,
                        'article_number': product.default_code,
                        'extension_id': more_ext.id if more_ext else False
                    }))
                product.sudo().write({
                    'more_pic_ids_variant': more_pic_vals
                })
            else:
                if more_pic_vals:
                    product.sudo().write({
                        'more_pic_ids_variant': more_pic_vals
                    })

            # map attribute and values to webshop attributes and values
            for attr in product.attribute_value_ids:
                if attr.attribute_id.webshop_attribute_id and \
                        attr.webshop_attribute_value_id:
                    if attr.attribute_id.webshop_attribute_id in \
                            product.variant_webshop_attribute_line_ids\
                                    .mapped('attribute_id'):
                        if attr.webshop_attribute_value_id not in \
                                product.variant_webshop_attribute_line_ids\
                                        .mapped('value_ids')\
                                        .filtered(lambda x: x.attribute_id == attr.attribute_id.webshop_attribute_id):
                            product.variant_webshop_attribute_line_ids.filtered(
                                lambda x: x.attribute_id == attr.attribute_id.webshop_attribute_id)\
                                .sudo().write({'value_ids': [(4,attr.webshop_attribute_value_id.id)]})
                    else:
                        product.variant_webshop_attribute_line_ids.sudo().create({
                            'product_id': product.id,
                            'attribute_id': attr.attribute_id.webshop_attribute_id.id,
                            'value_ids': [(4, attr.webshop_attribute_value_id.id)]
                        })

            if not context.get('create_from_tmpl') and not product.attribute_value_ids:
                product.variant_webshop_attribute_line_ids = [
                    (0, 0, {'product_id': product.id,
                            'attribute_id': attr.attribute_id.id,
                            'value_ids': [(4, attr.value_ids.id)]})
                    for attr in product_tmpl.webshop_attribute_line_ids]

            for regular in product.product_tmpl_id.regular_attribute_line_ids:
                for value in regular.value_ids:
                    if regular.attribute_id in product.variant_regular_attribute_line_ids.mapped(
                            'attribute_id'):
                        if value not in product.variant_regular_attribute_line_ids \
                                .mapped('value_ids') \
                                .filtered(lambda
                                                  x: x.attribute_id == regular.attribute_id):
                            product.variant_regular_attribute_line_ids \
                                .filtered(lambda
                                              x: x.attribute_id == regular.attribute_id) \
                                .sudo().write({'value_ids': [(4, value.id)]})
                    else:
                        product.variant_regular_attribute_line_ids.sudo().create({
                            'product_id': product.id,
                            'attribute_id': regular.attribute_id.id,
                            'value_ids': [(4, value.id)]
                        })

            context = self.env.context
            if not context.get('from_update_button'):
                if product.webshop_boolean_variant:
                    raise_warning = False
                    msg = 'You are not allowed to set "Webshop" field of ' \
                          'products to "Yes" because the following condition ' \
                          'is not met! \n'
                    if product.type != 'product':
                        raise_warning = True
                        msg += ' - Product must be of type Stockable! \n'
                    if not product.sale_ok:
                        raise_warning = True
                        msg += ' - Can be sold = True \n'
                    if product.lst_price <= 0:
                        raise_warning = True
                        msg += ' - Sale Price cannot be ZERO \n'
                    if not product.brand_id_variant:
                        raise_warning = True
                        msg += ' - Brand cannot be empty \n'
                    if not product.main_pic_extension_id_variant:
                        raise_warning = True
                        msg += ' - Main Picture Extension cannot be empty \n'
                    if product.main_pic_article_number_variant is False or \
                            product.main_pic_article_number_variant == '':
                        raise_warning = True
                        msg += ' - Main Picture Article cannot be empty \n'
                    if not product.catalog_variant:
                        raise_warning = True
                        msg += ' - Catalog cannot be empty \n'
                    if not product.public_categ_variant_ids:
                        raise_warning = True
                        msg += ' - Categories cannot be empty \n'
                    if product.ecommerce_name is False or product.ecommerce_name == '':
                        raise_warning = True
                        msg += ' - E-commerce Name cannot be empty \n'
                    if product.product_desc is False or product.product_desc == '':
                        raise_warning = True
                        msg += ' - Product Description cannot be empty \n'

                    if raise_warning is True:
                        raise ValidationError(_(msg))

                    retries = 0
                    if api_config:
                        retries = api_config.api_attempts

                    product.with_delay(max_retries=retries) \
                        .webshop_api_product(method='create',
                                             delete=False,
                                             delete_response=False)
                    if product.more_pic_ids_variant or \
                            product.extra_asset_ids_variant or \
                            product.main_pic_id_variant or \
                            product.variant_video_ids:
                        product.with_delay(max_retries=retries) \
                            .webshop_api_asset(method='create')
        return products

    @api.multi
    def write(self, vals):
        res = super(ProductProduct, self.with_context(
            write_product_product=True)).write(vals)

        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)])

        if any(len(template.variant_webshop_attribute_line_ids) != len(
                template.variant_webshop_attribute_line_ids.mapped('attribute_id')) for
               template in self):
            raise ValidationError(_(
                'You cannot define two webshop attribute lines for the same attribute.'))

        if any(len(template.variant_regular_attribute_line_ids) != len(
                template.variant_regular_attribute_line_ids.mapped('attribute_id')) for
               template in self):
            raise ValidationError(_(
                'You cannot define two regular attribute lines for the same attribute.'))

        retries = 0
        if api_config:
            retries = api_config.api_attempts

        for product in self:
            context = self.env.context
            if not context.get('create_from_tmpl'):
                if not context.get('create_product_product') and not \
                        context.get('from_update_button'):
                    if vals.get('brand_id_variant') \
                            or vals.get('order_quantity_variant') \
                            or vals.get('min_order_quantity_variant') \
                            or vals.get('catalog_variant') \
                            or vals.get('ecommerce_name') \
                            or vals.get('intro_text') \
                            or vals.get('category_text') \
                            or vals.get('product_desc') \
                            or vals.get('search_keyword_variant') \
                            or vals.get('webshop_tags_ids_variant') \
                            or vals.get('public_categ_variant_ids') \
                            or vals.get('variant_webshop_attribute_line_ids') \
                            or vals.get('variant_regular_attribute_line_ids') \
                            or vals.get('variant_alternative_product_ids') \
                            or vals.get('variant_accessory_product_ids') \
                            or vals.get('default_code') \
                            or vals.get('lst_price') \
                            or vals.get('name') \
                            or vals.get('categ_id') \
                            or vals.get('webshop_boolean_variant') \
                            or vals.get('uom_id') \
                            or vals.get('intro_text') == '' \
                            or vals.get('category_text') == '' \
                            or vals.get('product_desc') == '' \
                            or vals.get('search_keyword_variant') == '' \
                            or vals.get('brand_id_variant') is False \
                            or vals.get('order_quantity_variant') == 0 \
                            or vals.get('min_order_quantity_variant') == 0 \
                            or vals.get('catalog_variant') is False \
                            or vals.get('public_categ_variant_ids') is False \
                            or vals.get('variant_alternative_product_ids') is False \
                            or vals.get('variant_accessory_product_ids') is False \
                            or vals.get('webshop_tags_ids_variant') is False \
                            or vals.get('default_code') == '' \
                            or vals.get('keywords_for_search') \
                            or vals.get('delivery_service_variant_id') \
                            or vals.get('delivery_service_variant_id') is False \
                            or vals.get('webshop_inventory_availability_variant') \
                            or vals.get('webshop_inventory_availability_variant') is False \
                            or vals.get('main_pic_article_number_variant') \
                            or vals.get('main_pic_extension_id_variant') \
                            or vals.get('more_pic_ids_variant') \
                            or vals.get('extra_asset_ids_variant') \
                            or vals.get('main_pic_extension_id_variant') is False \
                            or vals.get('main_pic_article_number_variant') == '' \
                            or vals.get('variant_video_ids'):
                        # Extra Conditions when saving
                        if product.webshop_boolean_variant:
                            raise_warning = False
                            msg = 'You are not allowed to set "Webshop" field of ' \
                                  'products to "Yes" because the following condition ' \
                                  'is not met! \n'
                            if product.type != 'product':
                                raise_warning = True
                                msg += ' - Product must be of type Stockable! \n'
                            if not product.sale_ok:
                                raise_warning = True
                                msg += ' - Can be sold = True \n'
                            if product.lst_price <= 0:
                                raise_warning = True
                                msg += ' - Sale Price cannot be ZERO \n'
                            if not product.brand_id_variant:
                                raise_warning = True
                                msg += ' - Brand cannot be empty \n'
                            if not product.catalog_variant:
                                raise_warning = True
                                msg += ' - Catalog cannot be empty \n'
                            if not product.public_categ_variant_ids:
                                raise_warning = True
                                msg += ' - Categories cannot be empty \n'
                            if product.ecommerce_name is False or product.ecommerce_name == '':
                                raise_warning = True
                                msg += ' - E-commerce Name cannot be empty \n'
                            if product.product_desc is False or product.product_desc == '':
                                raise_warning = True
                                msg += ' - Product Description cannot be empty \n'
                            # Edit assets
                            if not product.main_pic_extension_id_variant:
                                raise_warning = True
                                msg += ' - Main Picture Extension cannot be empty \n'
                            if product.main_pic_article_number_variant is False or \
                                    product.main_pic_article_number_variant == '':
                                raise_warning = True
                                msg += ' - Main Picture Article cannot be empty \n'

                            if raise_warning is True:
                                raise ValidationError(_(msg))

                            product.with_delay(max_retries=retries) \
                                .webshop_api_product(method='write',
                                                     delete=False,
                                                     delete_response=False)

                            product.with_delay(max_retries=retries)\
                                .webshop_api_asset(method='write')

                    # In-active when untick webshop checkbox or in-active
                    web_check = vals.get('webshop_boolean_variant')
                    active = vals.get('active')
                    if web_check is False or active is False:
                        product.with_delay(max_retries=retries) \
                            .webshop_api_product(method='write', delete=True,
                                                 delete_response='Deactive Product')

        return res

    def unlink(self):
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)], limit=1)

        if api_config and api_config.token and api_config.api_url and \
                api_config.product_end_point:
            headers = {'Authorization': 'Token ' + api_config.token,
                       'Content-Type': 'application/json'}

            # Api link
            prod_link = api_config.api_url + api_config.product_end_point
            for product in self:
                prod_key = str(product.id)
                # API DELETE Method for Product Deactivate
                time = datetime.now()
                prod_link_api = prod_link + prod_key + '/'
                update_api = requests.delete(url=prod_link_api,
                                             headers=headers,
                                             verify=False)
                # Technical API Log
                update_log = product.sudo().create_technical_log_api(
                    request_method='PUT',
                    request_type='De-activate Product',
                    request_url=prod_link_api,
                    request_headers=headers,
                    request_response='Product Deleted',
                    request_uid=self.env.uid,
                    request_status=update_api.status_code,
                    request_time=time,
                    request_arguments='DELETE',
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
                                 product=product.name,
                                 internal=product.default_code,
                                 synctime=time,
                                 response=update_api.content,
                                 api_name='De-Activate Product API')
                _logger.info('DELETE PUT ---------------> %s', update_api)
                _logger.info('DELETE PUT RESULT ---------------> %s',
                             update_api.content)

        return super(ProductProduct, self).unlink()

    @api.multi
    @job
    def webshop_api_asset(self, method):
        for product in self:
            api_config = self.env['webshop.api.config'].search(
                [('active', '=', True)])
            if api_config and api_config.token and api_config.api_url and \
                    api_config.assets_end_point:
                headers = {'Authorization': 'Token ' + api_config.token,
                           'Content-Type': 'application/json'}

                asset_link = api_config.api_url + api_config.assets_end_point

                prod = {'key': product.id,
                        'origin': 'MARKANT'}

                # Api for MAIN PICTURE
                if product.main_pic_id_variant:
                    main_key = 'main-' + str(product.main_pic_id_variant.id)
                    main_parameters = {
                        'key': main_key,
                        'name': product.main_pic_id_variant.article_number or None,
                        'ident': product.main_pic_id_variant.main_filename or None,
                        'sequence': 1,
                        'type': 'product_image',
                        'product': prod

                    }
                    main_data = json.dumps(main_parameters)
                    # API POST Method for Main Pic
                    time = datetime.now()
                    api_asset_link = asset_link + main_key + "/"
                    main_pic_api = requests.put(url=api_asset_link,
                                               data=main_data,
                                               headers=headers,
                                               verify=False)
                    # Technical API Log
                    main_asset_log = product.sudo().create_technical_log_api(
                        request_method='PUT',
                        request_type='Main Picture',
                        request_url=api_asset_link,
                        request_headers=headers,
                        request_response=main_pic_api.content,
                        request_uid=self.env.uid,
                        request_status=main_pic_api.status_code,
                        request_time=time,
                        request_arguments=main_data,
                        request_direction='outgoing')

                    if main_pic_api.status_code in (200, 201):
                        status = 'successful'
                    else:
                        status = 'failed'
                    asset_log = {
                        'internal_ref': product.default_code or '',
                        'asset': product.main_filename_variant,
                        'type': 'PUT',
                        'product_id': product.id,
                        'sync_method': 'real_time',
                        'sync_time': time,
                        'sync_status': status,
                        'response_body': main_pic_api.content,
                    }
                    self.env['webshop.asset.api.log'].sudo().create(asset_log)

                    # Send email notification
                    if main_pic_api.status_code not in (200, 201) \
                            and main_asset_log:
                        for user in self.env[
                            'webshop.fail.notification'] \
                                .sudo().search([]):
                            if user.email:
                                main_asset_log.sudo().action_send_fail_notification_mail \
                                    (lang=user.user_id.partner_id.lang,
                                     email=user.email,
                                     user=user.user_id.name,
                                     product=product.name,
                                     internal=product.default_code,
                                     synctime=time,
                                     response=main_pic_api.content,
                                     api_name='Main Picture')
                    _logger.info('MAIN ASSET PUT ---------------> %s', main_pic_api)
                    _logger.info('MAIN ASSET PUT RESULT ---------------> %s',
                                 main_pic_api.content)

                for more in product.more_pic_ids_variant:
                    more_key = 'more-' + str(more.id)
                    more_parameters = {
                        'key': more_key,
                        'name': more.article_number or None,
                        'ident': more.more_filename or None,
                        'sequence': more.sequence,
                        'type': 'additional_product_image',
                        'product': prod

                    }
                    more_data = json.dumps(more_parameters)
                    # API POST Method for More Pic
                    time = datetime.now()
                    api_more_link = asset_link + more_key + '/'
                    more_pic_api = requests.put(url=api_more_link,
                                                data=more_data,
                                                headers=headers,
                                                verify=False)
                    # Technical API Log
                    more_asset_log = product.sudo().create_technical_log_api(
                        request_method='PUT',
                        request_type='More Picture',
                        request_url=api_more_link,
                        request_headers=headers,
                        request_response=more_pic_api.content,
                        request_uid=self.env.uid,
                        request_status=more_pic_api.status_code,
                        request_time=time,
                        request_arguments=more_data,
                        request_direction='outgoing')

                    if more_pic_api.status_code in (200, 201):
                        status = 'successful'
                    else:
                        status = 'failed'
                    asset_log = {
                        'internal_ref': product.default_code or '',
                        'type': 'PUT',
                        'asset': more.more_filename,
                        'product_id': product.id,
                        'sync_method': 'real_time',
                        'sync_time': time,
                        'sync_status': status,
                        'response_body': more_pic_api.content,
                    }
                    self.env['webshop.asset.api.log'].sudo().create(asset_log)

                    # Send email notification
                    if more_pic_api.status_code not in (200, 201) \
                            and more_asset_log:
                        for user in self.env[
                            'webshop.fail.notification'] \
                                .sudo().search([]):
                            if user.email:
                                more_asset_log.sudo().action_send_fail_notification_mail \
                                    (lang=user.user_id.partner_id.lang,
                                     email=user.email,
                                     user=user.user_id.name,
                                     product=product.name,
                                     internal=product.default_code,
                                     synctime=time,
                                     response=more_pic_api.content,
                                     api_name='More Picture')
                    _logger.info('MORE ASSET PUT ---------------> %s', more_pic_api)
                    _logger.info('MORE ASSET PUT RESULT ---------------> %s',
                                 more_pic_api.content)

                for extra in product.extra_asset_ids_variant:
                    extra_key = 'extra-' + str(extra.id)
                    extra_parameters = {
                        'key': extra_key,
                        'name': extra.article_number or None,
                        'ident': extra.extra_filename or None,
                        'sequence': extra.sequence,
                        'type': 'url',
                        'product': prod,
                    }
                    if extra.lang:
                        language = {'language': extra.lang}
                        extra_parameters.update(language)
                    extra_data = json.dumps(extra_parameters)
                    # API POST Method for Extra Pic
                    time = datetime.now()
                    api_extra_link = asset_link + extra_key + '/'
                    extra_pic_api = requests.put(url=api_extra_link,
                                                 data=extra_data,
                                                 headers=headers,
                                                 verify=False)
                    # Technical API Log
                    extra_asset_log = product.sudo().create_technical_log_api(
                        request_method='PUT',
                        request_type='Extra Picture',
                        request_url=api_extra_link,
                        request_headers=headers,
                        request_response=extra_pic_api.content,
                        request_uid=self.env.uid,
                        request_status=extra_pic_api.status_code,
                        request_time=time,
                        request_arguments=extra_data,
                        request_direction='outgoing')

                    if extra_pic_api.status_code in (200, 201):
                        status = 'successful'
                    else:
                        status = 'failed'
                    asset_log = {
                        'internal_ref': product.default_code or '',
                        'type': 'PUT',
                        'asset': extra.extra_filename,
                        'product_id': product.id,
                        'sync_method': 'real_time',
                        'sync_time': time,
                        'sync_status': status,
                        'response_body': extra_pic_api.content,
                    }
                    self.env['webshop.asset.api.log'].sudo().create(asset_log)

                    # Send email notification
                    if extra_pic_api.status_code not in (200, 201) \
                            and extra_asset_log:
                        for user in self.env[
                            'webshop.fail.notification'] \
                                .sudo().search([]):
                            if user.email:
                                extra_asset_log.sudo().action_send_fail_notification_mail \
                                    (lang=user.user_id.partner_id.lang,
                                     email=user.email,
                                     user=user.user_id.name,
                                     product=product.name,
                                     internal=product.default_code,
                                     synctime=time,
                                     response=extra_pic_api.content,
                                     api_name='More Picture')
                    _logger.info('EXTRA ASSET PUT ---------------> %s',
                                 extra_pic_api)
                    _logger.info('EXTRA ASSET PUT RESULT ---------------> %s',
                                 extra_pic_api.content)

                for vid in product.variant_video_ids:
                    vid_key = 'vid-' + str(vid.id)
                    vid_parameters = {
                        'key': vid_key,
                        'name': vid.name or None,
                        'ident': vid.identifier or None,
                        'indent_org': vid.link or None,
                        'sequence': vid.sequence,
                        'video_provider': vid.provider or None,
                        'video_embed': vid.video_embed,
                        'type': 'video',
                        'product': prod,
                    }

                    if vid.lang:
                        language = {'language': vid.lang}
                        vid_parameters.update(language)

                    vid_data = json.dumps(vid_parameters)
                    # API POST Method for Videos
                    time = datetime.now()
                    api_extra_link = asset_link + vid_key + '/'
                    vid_api = requests.put(url=api_extra_link,
                                           data=vid_data,
                                           headers=headers,
                                           verify=False)
                    # Technical API Log
                    vid_asset_log = product.sudo().create_technical_log_api(
                        request_method='PUT',
                        request_type='Videos',
                        request_url=api_extra_link,
                        request_headers=headers,
                        request_response=vid_api.content,
                        request_uid=self.env.uid,
                        request_status=vid_api.status_code,
                        request_time=time,
                        request_arguments=vid_data,
                        request_direction='outgoing')

                    if vid_api.status_code in (200, 201):
                        status = 'successful'
                    else:
                        status = 'failed'
                    vid_log = {
                        'internal_ref': product.default_code or '',
                        'type': 'PUT',
                        'asset': vid.name,
                        'product_id': product.id,
                        'sync_method': 'real_time',
                        'sync_time': time,
                        'sync_status': status,
                        'response_body': vid_api.content,
                    }
                    self.env['webshop.asset.api.log'].sudo().create(vid_log)

                    # Send email notification
                    if vid_api.status_code not in (200, 201) \
                            and vid_asset_log:
                        for user in self.env[
                            'webshop.fail.notification'] \
                                .sudo().search([]):
                            if user.email:
                                vid_asset_log.sudo().action_send_fail_notification_mail \
                                    (lang=user.user_id.partner_id.lang,
                                     email=user.email,
                                     user=user.user_id.name,
                                     product=product.name,
                                     internal=product.default_code,
                                     synctime=time,
                                     response=vid_api.content,
                                     api_name='More Picture')
                    _logger.info('VIDEOS ASSET PUT ---------------> %s',
                                 vid_api)
                    _logger.info(
                        'VIDEOS ASSET PUT RESULT ---------------> %s',
                        vid_api.content)

        return True

    @api.multi
    @job
    def webshop_api_product(self, method, delete_response, delete=False):
        for product in self:
            # Api Call to Create/Edit Product Variant (POST)
            api_config = self.env['webshop.api.config'].search(
                [('active', '=', True)], limit=1)

            if api_config and api_config.token and api_config.api_url and \
                    api_config.product_end_point and api_config.brand_end_point \
                    and api_config.tag_end_point and api_config.catalog_end_point \
                    and api_config.product_category_end_point \
                    and api_config.tree_category_end_point \
                    and api_config.attribute_property_end_point \
                    and api_config.attribute_list_end_point \
                    and api_config.api_company:
                headers = {'Authorization': 'Token ' + api_config.token,
                           'Content-Type': 'application/json'}

                # Api link
                prod_link = api_config.api_url + api_config.product_end_point
                brand_link = api_config.api_url + api_config.brand_end_point
                tag_link = api_config.api_url + api_config.tag_end_point
                catalog_link = api_config.api_url + api_config.catalog_end_point
                prodcateg_link = api_config.api_url + \
                                 api_config.product_category_end_point
                treecateg_link = api_config.api_url + \
                                 api_config.tree_category_end_point
                attrprop_link = api_config.api_url + \
                                api_config.attribute_property_end_point
                attrlist_link = api_config.api_url + \
                                api_config.attribute_list_end_point

                if method == 'write' and product.lst_price <= 0:
                    delete = True

                if delete:
                    prod_key = str(product.id)
                    update_params = {
                        'key': prod_key,
                        'name': product.ecommerce_name,
                        'uom': product.uom_id.id,
                        'active': 'False'
                    }
                    update_data = json.dumps(update_params)
                    # API PUT Method for Product Deactivate
                    time = datetime.now()
                    prod_link_api = prod_link + prod_key + '/'
                    update_api = requests.put(url=prod_link_api,
                                              data=update_data,
                                              headers=headers,
                                              verify=False)
                    # Technical API Log
                    update_log = product.sudo().create_technical_log_api(
                        request_method='PUT',
                        request_type='De-activate Product',
                        request_url=prod_link_api,
                        request_headers=headers,
                        request_response=delete_response,
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
                                     product=product.name,
                                     internal=product.default_code,
                                     synctime=time,
                                     response=update_api.content,
                                     api_name='De-Activate Product API')
                    _logger.info('DELETE PUT ---------------> %s', update_api)
                    _logger.info('DELETE PUT RESULT ---------------> %s',
                                 update_api.content)
                else:
                    if product.webshop_boolean_variant:
                        web_attribute = []
                        cross_prod = []
                        up_prod = []
                        tag_prod = []
                        tree_prod = []
                        catalog_prod = []
                        list_prices = []

                        # attributes & attribute values
                        seq = 0
                        for attribute in product.variant_webshop_attribute_line_ids:
                            seq += 1
                            for value in attribute.value_ids:
                                # Api for AttributeProperty
                                attrprop_key = 'web-' + str(attribute.attribute_id.id)
                                attrprop_parameters = {
                                    'key': attrprop_key,
                                    'name': attribute.attribute_id.name,
                                    'input_validation': "list"
                                }
                                attrprop_data = json.dumps(attrprop_parameters)
                                # API PUT Method for AttributeProperty
                                time = datetime.now()
                                attrprop_link_api = attrprop_link + attrprop_key + '/'
                                attrprop_api = requests.put(url=attrprop_link_api,
                                                            data=attrprop_data,
                                                            headers=headers,
                                                            verify=False)
                                # Technical API Log
                                attrprop_log = product.sudo().create_technical_log_api(
                                    request_method='PUT',
                                    request_type='Attribute Property',
                                    request_url=attrprop_link_api,
                                    request_headers=headers,
                                    request_response=attrprop_api.content,
                                    request_uid=self.env.uid,
                                    request_status=attrprop_api.status_code,
                                    request_time=time,
                                    request_arguments=attrprop_data,
                                    request_direction='outgoing')

                                # Send email notification
                                if attrprop_api.status_code not in (200, 201) \
                                        and attrprop_log:
                                    for user in self.env[
                                        'webshop.fail.notification'] \
                                            .sudo().search([]):
                                        if user.email:
                                            attrprop_log.sudo().action_send_fail_notification_mail \
                                                (lang=user.user_id.partner_id.lang,
                                                 email=user.email,
                                                 user=user.user_id.name,
                                                 product=product.name,
                                                 internal=product.default_code,
                                                 synctime=time,
                                                 response=attrprop_api.content,
                                                 api_name='Atrtibute Property API')
                                _logger.info('PUT ATTRPROR ---------------> %s', attrprop_api)
                                _logger.info('PUT ATTRPROR RESULT ---------------> %s',
                                             attrprop_api.content)

                                # Api for AttributeList
                                attrlist_key = 'web-' + str(value.id)
                                attrlist_parameters = {
                                    'key': attrlist_key,
                                    'property': attrprop_key,
                                    'list_value': value.name
                                }
                                attrlist_data = json.dumps(attrlist_parameters)
                                # API PUT Method for AttributeList
                                time = datetime.now()
                                attrlist_link_api = attrlist_link + attrlist_key + '/'
                                attrlist_api = requests.put(url=attrlist_link_api,
                                                            data=attrlist_data,
                                                            headers=headers,
                                                            verify=False)
                                # Technical API Log
                                attr_list_log = product.sudo().create_technical_log_api(
                                    request_method='PUT',
                                    request_type='Attribute List',
                                    request_url=attrlist_link_api,
                                    request_headers=headers,
                                    request_response=attrlist_api.content,
                                    request_uid=self.env.uid,
                                    request_status=attrlist_api.status_code,
                                    request_time=time,
                                    request_arguments=attrlist_data,
                                    request_direction='outgoing')

                                # Send email notification
                                if attrlist_api.status_code not in (200, 201) \
                                        and attr_list_log:
                                    for user in self.env[
                                        'webshop.fail.notification'] \
                                            .sudo().search([]):
                                        if user.email:
                                            attr_list_log.sudo().action_send_fail_notification_mail \
                                                (lang=user.user_id.partner_id.lang,
                                                 email=user.email,
                                                 user=user.user_id.name,
                                                 product=product.name,
                                                 internal=product.default_code,
                                                 synctime=time,
                                                 response=attrlist_api.content,
                                                 api_name='Atrtibute List API')
                                _logger.info('ATTRLIST PUT ---------------> %s', attrlist_api)
                                _logger.info('ATTRLIST PUT RESULT ---------------> %s',
                                             attrlist_api.content)

                                web_attribute.append({'key': attrprop_key,
                                                      'value': attrlist_key,
                                                      'sequence': seq})

                        # regular attributes & attribute values
                        seq = 0
                        for reg_attribute in product.variant_regular_attribute_line_ids:
                            seq += 1
                            for value in reg_attribute.value_ids:
                                # Api for AttributeProperty
                                reg_attrprop_key = 'man-' + str(reg_attribute.attribute_id.id)
                                reg_attrprop_parameters = {
                                    'key': reg_attrprop_key,
                                    'name': reg_attribute.attribute_id.name,
                                    'input_validation': "list"
                                }
                                reg_attrprop_data = json.dumps(
                                    reg_attrprop_parameters)

                                # API PUT Method for AttributeProperty
                                time = datetime.now()
                                attrprop_link_api = attrprop_link + reg_attrprop_key + '/'
                                reg_attrprop_api = requests.put(
                                    url=attrprop_link_api,
                                    data=reg_attrprop_data,
                                    headers=headers,
                                    verify=False)
                                # Technical API Log
                                reg_attrprop_log = product.sudo().create_technical_log_api(
                                    request_method='PUT',
                                    request_type='Attribute Property',
                                    request_url=attrprop_link_api,
                                    request_headers=headers,
                                    request_response=reg_attrprop_api.content,
                                    request_uid=self.env.uid,
                                    request_status=reg_attrprop_api.status_code,
                                    request_time=time,
                                    request_arguments=reg_attrprop_data,
                                    request_direction='outgoing')

                                # Send email notification
                                if reg_attrprop_api.status_code not in (
                                200, 201) \
                                        and reg_attrprop_log:
                                    for user in self.env[
                                        'webshop.fail.notification'] \
                                            .sudo().search([]):
                                        if user.email:
                                            reg_attrprop_log.sudo().action_send_fail_notification_mail \
                                                (
                                                    lang=user.user_id.partner_id.lang,
                                                    email=user.email,
                                                    user=user.user_id.name,
                                                    product=product.name,
                                                    internal=product.default_code,
                                                    synctime=time,
                                                    response=reg_attrprop_api.content,
                                                    api_name='Atrtibute Property API')
                                _logger.info(
                                    'PUT REGULAR ATTRPROR ---------------> %s',
                                    reg_attrprop_api)
                                _logger.info(
                                    'PUT REGULAR ATTRPROR RESULT ---------------> %s',
                                    reg_attrprop_api.content)

                                # Api for AttributeList
                                attrlist_key = 'man-' + str(value.id)
                                attrlist_parameters = {
                                    'key': attrlist_key,
                                    'property': reg_attrprop_key,
                                    'list_value': value.name
                                }
                                attrlist_data = json.dumps(
                                    attrlist_parameters)
                                # API PUT Method for AttributeList
                                time = datetime.now()
                                attrlist_link_api = attrlist_link + attrlist_key + '/'
                                attrlist_api = requests.put(
                                    url=attrlist_link_api,
                                    data=attrlist_data,
                                    headers=headers,
                                    verify=False)
                                # Technical API Log
                                attr_list_log = product.sudo().create_technical_log_api(
                                    request_method='PUT',
                                    request_type='Attribute List',
                                    request_url=attrlist_link_api,
                                    request_headers=headers,
                                    request_response=attrlist_api.content,
                                    request_uid=self.env.uid,
                                    request_status=attrlist_api.status_code,
                                    request_time=time,
                                    request_arguments=attrlist_data,
                                    request_direction='outgoing')

                                # Send email notification
                                if attrlist_api.status_code not in (
                                200, 201) \
                                        and attr_list_log:
                                    for user in self.env[
                                        'webshop.fail.notification'] \
                                            .sudo().search([]):
                                        if user.email:
                                            attr_list_log.sudo().action_send_fail_notification_mail \
                                                (
                                                    lang=user.user_id.partner_id.lang,
                                                    email=user.email,
                                                    user=user.user_id.name,
                                                    product=product.name,
                                                    internal=product.default_code,
                                                    synctime=time,
                                                    response=attrlist_api.content,
                                                    api_name='Atrtibute List API')
                                _logger.info(
                                    'ATTRLIST REGULAR PUT ---------------> %s',
                                    attrlist_api)
                                _logger.info(
                                    'ATTRLIST REGULAR PUT RESULT ---------------> %s',
                                    attrlist_api.content)

                                web_attribute.append(
                                    {'key': reg_attrprop_key,
                                     'value': attrlist_key,
                                     'sequence': seq})

                        # Api for Product Category
                        prodcateg_key = None
                        if product.categ_id:
                            prodcateg_key = str(product.categ_id.id)
                            prodcateg_parameters = {
                                'key': prodcateg_key,
                                'name': str(product.categ_id.name)
                            }
                            prodcateg_data = json.dumps(prodcateg_parameters)
                            # API PUT Method for Product Category
                            time = datetime.now()
                            prodcateg_link_api = prodcateg_link + prodcateg_key + '/'
                            prodcateg_api = requests.put(url=prodcateg_link_api,
                                                        data=prodcateg_data,
                                                        headers=headers,
                                                        verify=False)
                            # Technical API Log
                            prod_categ_log = product.sudo().create_technical_log_api(
                                request_method='PUT',
                                request_type='Product Category',
                                request_url=prodcateg_link_api,
                                request_headers=headers,
                                request_response=prodcateg_api.content,
                                request_uid=self.env.uid,
                                request_status=prodcateg_api.status_code,
                                request_time=time,
                                request_arguments=prodcateg_data,
                                request_direction='outgoing')

                            # Send email notification
                            if prodcateg_api.status_code not in (200, 201) \
                                    and prod_categ_log:
                                for user in self.env['webshop.fail.notification'] \
                                        .sudo().search([]):
                                    if user.email:
                                        prod_categ_log.sudo().action_send_fail_notification_mail \
                                            (lang=user.user_id.partner_id.lang,
                                             email=user.email,
                                             user=user.user_id.name,
                                             product=product.name,
                                             internal=product.default_code,
                                             synctime=time,
                                             response=prodcateg_api.content,
                                             api_name='Product Category API')
                            _logger.info('PRODCATEG PUT ---------------> %s', prodcateg_api)
                            _logger.info('PRODCATEG PUT RESULT ---------------> %s',
                                         prodcateg_api.content)

                        # Api for trees (category)
                        for tree in product.public_categ_variant_ids:
                            tree_prod.append(tree.id)
                            treecateg_key = str(tree.id)
                            treecateg_parameters = {
                                'key': treecateg_key,
                                'name': tree.name
                            }
                            treecateg_data = json.dumps(treecateg_parameters)
                            # API PUT Method for Trees Category
                            time = datetime.now()
                            treecateg_link_api = treecateg_link + treecateg_key + '/'
                            treecateg_api = requests.put(url=treecateg_link_api,
                                                         data=treecateg_data,
                                                         headers=headers,
                                                         verify=False)
                            # Technical API Log
                            tree_log = product.sudo().create_technical_log_api(
                                request_method='PUT',
                                request_type='Trees',
                                request_url=treecateg_link_api,
                                request_headers=headers,
                                request_response=treecateg_api.content,
                                request_uid=self.env.uid,
                                request_status=treecateg_api.status_code,
                                request_time=time,
                                request_arguments=treecateg_data,
                                request_direction='outgoing')

                            # Send email notification
                            if treecateg_api.status_code not in (200, 201) \
                                    and tree_log:
                                for user in self.env['webshop.fail.notification'] \
                                        .sudo().search([]):
                                    if user.email:
                                        tree_log.sudo().action_send_fail_notification_mail \
                                            (lang=user.user_id.partner_id.lang,
                                             email=user.email,
                                             user=user.user_id.name,
                                             product=product.name,
                                             internal=product.default_code,
                                             synctime=time,
                                             response=treecateg_api.content,
                                             api_name='Trees API')
                            _logger.info('PRODCATEG PUT ---------------> %s', treecateg_api)
                            _logger.info('PRODCATEG PUT RESULT ---------------> %s',
                                         treecateg_api.content)

                        # Api for tag
                        for tag in product.webshop_tags_ids_variant:
                            tag_prod.append(tag.id)
                            tag_key = str(tag.id)
                            tag_parameters = {
                                'key': tag_key,
                                'name': tag.name,
                                'type': "standard"
                            }
                            tag_data = json.dumps(tag_parameters)
                            # API PUT Method for Tag
                            time = datetime.now()
                            tag_link_api = tag_link + tag_key + '/'
                            tag_api = requests.put(url=tag_link_api,
                                                   data=tag_data,
                                                   headers=headers,
                                                   verify=False)
                            # Technical API Log
                            tag_log = product.sudo().create_technical_log_api(
                                request_method='PUT',
                                request_type='Tags',
                                request_url=tag_link_api,
                                request_headers=headers,
                                request_response=tag_api.content,
                                request_uid=self.env.uid,
                                request_status=tag_api.status_code,
                                request_time=time,
                                request_arguments=tag_data,
                                request_direction='outgoing')

                            # Send email notification
                            if tag_api.status_code not in (200, 201) \
                                    and tag_log:
                                for user in self.env['webshop.fail.notification'] \
                                        .sudo().search([]):
                                    if user.email:
                                        tag_log.sudo().action_send_fail_notification_mail \
                                            (lang=user.user_id.partner_id.lang,
                                             email=user.email,
                                             user=user.user_id.name,
                                             product=product.name,
                                             internal=product.default_code,
                                             synctime=time,
                                             response=tag_api.content,
                                             api_name='Tags API')
                            _logger.info('TAG PUT ---------------> %s', tag_api)
                            _logger.info('TAG PUT RESULT ---------------> %s',
                                         tag_api.content)

                        # Api for catalog
                        if product.catalog_variant:
                            catalog_prod.append(product.catalog_variant)
                            catalog_key = product.catalog_variant
                            catalog_params = {
                                'key': catalog_key,
                                'name': catalog_key,
                                'type': 'company'
                            }
                            catalog_data = json.dumps(catalog_params)
                            # API PUT Method for Catalog
                            time = datetime.now()
                            catalog_link_api = catalog_link + catalog_key + '/'
                            catalog_api = requests.put(url=catalog_link_api,
                                                       data=catalog_data,
                                                       headers=headers,
                                                       verify=False)
                            # Technical API Log
                            catalog_log = product.sudo().create_technical_log_api(
                                request_method='PUT',
                                request_type='Catalog',
                                request_url=catalog_link_api,
                                request_headers=headers,
                                request_response=catalog_api.content,
                                request_uid=self.env.uid,
                                request_status=catalog_api.status_code,
                                request_time=time,
                                request_arguments=catalog_data,
                                request_direction='outgoing')

                            # Send email notification
                            if catalog_api.status_code not in (200, 201) \
                                    and catalog_log:
                                for user in self.env['webshop.fail.notification'] \
                                        .sudo().search([]):
                                    if user.email:
                                        catalog_log.sudo().action_send_fail_notification_mail \
                                            (lang=user.user_id.partner_id.lang,
                                             email=user.email,
                                             user=user.user_id.name,
                                             product=product.name,
                                             internal=product.default_code,
                                             synctime=time,
                                             response=catalog_api.content,
                                             api_name='Catalog API')
                            _logger.info('CATALOG PUT ---------------> %s', catalog_api)
                            _logger.info('CATALOG RESULT ---------------> %s',
                                         catalog_api.content)

                        # GET VALUE NEEDED
                        # cross sell
                        for cross in product.variant_accessory_product_ids:
                            cross_prod.append(cross.id)

                        # up sell
                        for up in product.variant_alternative_product_ids:
                            up_prod.append(up.id)

                        list_prices.append(
                            {'company': api_config.api_company,
                             'value': product.lst_price}
                        )

                        # Api for product variant creation
                        parameters = {'key': str(product.id),
                                      'code': product.default_code or None,
                                      'name': product.ecommerce_name or None,
                                      'salable': product.sale_ok,
                                      'description': product.product_desc or None,
                                      'description2': product.intro_text or None,
                                      'description3': product.category_text or None,
                                      'uom': product.uom_id.id or None,
                                      'active': product.active,
                                      'category': prodcateg_key or None,
                                      'attributes': web_attribute or [],
                                      'list_prices': list_prices or None,
                                      'order_qty': product.order_quantity_variant or 0,
                                      'order_minimum_qty': product.min_order_quantitiy_variant or 0,
                                      'crosssell_products': cross_prod or [],
                                      'upsell_products': up_prod or [],
                                      'tags': tag_prod or [],
                                      'trees': tree_prod,
                                      'catalogs': catalog_prod}

                        if product.webshop_inventory_availability_variant:
                            parameters.update({'product_status': 'yes_discontinued'})
                        else:
                            parameters.update({'product_status': 'no'})

                        if product.delivery_service_variant_id:
                            parameters.update({'delivery_service': product.delivery_service_variant_id.id})

                        if product.search_keyword_variant:
                            parameters.update({'keywords_for_search': product.search_keyword_variant})

                        # Api for Brand
                        if product.brand_id_variant:
                            brand_key = str(product.brand_id_variant.id)
                            brand_parameters = {
                                'key': brand_key,
                                'name': str(product.brand_id_variant.name)
                            }
                            brand_data = json.dumps(brand_parameters)
                            prod_param = {'brand': brand_key or None}
                            parameters.update(prod_param)
                            # API PUT Method for Brand
                            time = datetime.now()
                            brand_link_api = brand_link + brand_key + '/'
                            brand_api = requests.put(url=brand_link_api,
                                                     data=brand_data,
                                                     headers=headers,
                                                     verify=False)
                            # Technical API Log
                            brand_log = product.sudo().create_technical_log_api(
                                request_method='PUT',
                                request_type='Brands',
                                request_url=brand_link_api,
                                request_headers=headers,
                                request_response=brand_api.content,
                                request_uid=self.env.uid,
                                request_status=brand_api.status_code,
                                request_time=time,
                                request_arguments=brand_data,
                                request_direction='outgoing')

                            # Send email notification
                            if brand_api.status_code not in (200, 201) \
                                    and brand_log:
                                for user in self.env['webshop.fail.notification'] \
                                        .sudo().search([]):
                                    if user.email:
                                        brand_log.sudo().action_send_fail_notification_mail \
                                            (lang=user.user_id.partner_id.lang,
                                             email=user.email,
                                             user=user.user_id.name,
                                             product=product.name,
                                             internal=product.default_code,
                                             synctime=time,
                                             response=brand_api.content,
                                             api_name='Brand API')
                            _logger.info('BRAND PUT ---------------> %s',
                                         brand_api)
                            _logger.info('BRAND PUT RESULT ---------------> %s',
                                         brand_api.content)
                        else:
                            brand_param = {'brand': None}
                            parameters.update(brand_param)

                        # Product API Call
                        product_data = json.dumps(parameters)
                        if method == 'create':
                            time = datetime.now()
                            r = requests.post(url=prod_link,
                                              data=product_data,
                                              headers=headers,
                                              verify=False)
                            if r.status_code in (200, 201):
                                # Product API Log
                                success_stat = {
                                    'internal_ref': product.default_code or '',
                                    'product_id': product.id,
                                    'type': 'POST',
                                    'sync_method': 'real_time',
                                    'sync_time': time,
                                    'sync_status': 'successful',
                                    'response_body': r.content,
                                }
                                self.env['webshop.api.log'].sudo().create(success_stat)
                                # Technical API Log
                                product.sudo().create_technical_log_api(
                                    request_method='POST',
                                    request_type='Product',
                                    request_url=prod_link,
                                    request_headers=headers,
                                    request_response=r.content,
                                    request_uid=self.env.uid,
                                    request_status=r.status_code,
                                    request_time=time,
                                    request_arguments=product_data,
                                    request_direction='outgoing')
                            else:
                                # Product API Log
                                failed_stat = {
                                    'internal_ref': product.default_code or '',
                                    'type': 'POST',
                                    'product_id': product.id,
                                    'sync_method': 'real_time',
                                    'sync_time': time,
                                    'sync_status': 'failed',
                                    'response_body': r.content,
                                }
                                self.env['webshop.api.log'].sudo().create(failed_stat)
                                # Technical API Log
                                tech_log = product.sudo().create_technical_log_api(
                                    request_method='POST',
                                    request_type='Product',
                                    request_url=prod_link,
                                    request_headers=headers,
                                    request_response=r.content,
                                    request_uid=self.env.uid,
                                    request_status=r.status_code,
                                    request_time=time,
                                    request_arguments=product_data,
                                    request_direction='outgoing')

                                # Send email notification
                                for user in self.env['webshop.fail.notification'] \
                                        .sudo().search([]):
                                    if user.email and tech_log:
                                        tech_log.sudo().action_send_fail_notification_mail \
                                            (lang=user.user_id.partner_id.lang,
                                             email=user.email,
                                             user=user.user_id.name,
                                             product=product.name,
                                             internal=product.default_code,
                                             synctime=time,
                                             response=r.content,
                                             api_name='Product API')
                        else:
                            time = datetime.now()
                            put_key = str(product.id)
                            prod_link1 = prod_link + put_key + '/'
                            r = requests.put(url=prod_link1,
                                             data=product_data,
                                             headers=headers,
                                             verify=False)
                            if r.status_code in (200, 201):
                                success_stat = {
                                    'internal_ref': product.default_code or '',
                                    'type': 'PUT',
                                    'product_id': product.id,
                                    'sync_method': 'real_time',
                                    'sync_time': time,
                                    'sync_status': 'successful',
                                    'response_body': r.content,
                                }
                                self.env['webshop.api.log'].sudo().create(success_stat)
                                # Technical API Log
                                product.sudo().create_technical_log_api(
                                    request_method='PUT',
                                    request_type='Product',
                                    request_url=prod_link1,
                                    request_headers=headers,
                                    request_response=r.content,
                                    request_uid=self.env.uid,
                                    request_status=r.status_code,
                                    request_time=time,
                                    request_arguments=product_data,
                                    request_direction='outgoing')
                            else:
                                failed_stat = {
                                    'internal_ref': product.default_code or '',
                                    'type': 'PUT',
                                    'product_id': product.id,
                                    'sync_method': 'real_time',
                                    'sync_time': time,
                                    'sync_status': 'failed',
                                    'response_body': r.content,
                                }
                                self.env['webshop.api.log'].sudo().create(failed_stat)
                                # Technical API Log
                                tech_log = product.sudo().create_technical_log_api(
                                    request_method='PUT',
                                    request_type='Product',
                                    request_url=prod_link1,
                                    request_headers=headers,
                                    request_response=r.content,
                                    request_uid=self.env.uid,
                                    request_status=r.status_code,
                                    request_time=time,
                                    request_arguments=product_data,
                                    request_direction='outgoing')

                                # Send email notification
                                for user in self.env['webshop.fail.notification']\
                                        .sudo().search([]):
                                    if user.email and tech_log:
                                        tech_log.sudo().action_send_fail_notification_mail\
                                            (lang=user.user_id.partner_id.lang,
                                             email=user.email, user=user.user_id.name,
                                             product=product.name,
                                             internal=product.default_code,
                                             synctime=time, response=r.content,
                                             api_name='Product API')

                        _logger.info('POSTT ---------------> %s', r)
                        _logger.info('POSTT RESULT ---------------> %s', r.content)

        return True

    @api.multi
    def create_technical_log_api(self, request_method=False, request_type=False,
                                 request_url=False, request_headers=False,
                                 request_response=False, request_uid=False,
                                 request_status=False, request_time=False,
                                 request_arguments=False, request_direction=False):
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

    @api.multi
    @job
    def webshop_api_stock(self, api_config=None):
        if api_config and api_config.token and api_config.api_url and \
                api_config.product_end_point and api_config.api_warehouse:
            headers = {'Authorization': 'Token ' + api_config.token,
                       'Content-Type': 'application/json'}
            time = datetime.now()
            stock_link = api_config.api_url + api_config.product_end_point
            stock_link_api = stock_link + str(self.id) + '/stock'
            data = json.dumps([{
                'company': api_config.api_company,
                'identification': self.id,
                'quantity': self.pcf_max_producible_qty,
                'warehouse': api_config.api_warehouse
            }])
            post_api = requests.post(url=stock_link_api, data=data,
                                     headers=headers, verify=False)

            # Product API Log
            success_stat = {
                'internal_ref': self.default_code or '',
                'product_id': self.id,
                'qty_synced': self.pcf_max_producible_qty,
                'req_type': 'POST',
                'sync_method': 'real_time',
                'sync_time': time,
                'sync_status': post_api.status_code,
                'response_body': post_api.content,
            }
            self.env['webshop.stock.api.log'].sudo().create(success_stat)

            post_log = self.sudo().create_technical_log_api(
                request_method='POST',
                request_type='Stock API',
                request_url=stock_link_api,
                request_headers=headers,
                request_response=post_api.content,
                request_uid=self.env.uid,
                request_status=post_api.status_code,
                request_time=time,
                request_arguments=data,
                request_direction='outgoing'
            )

            # Send email notification
            if post_api.status_code not in (200, 201) and post_log:
                for user in self.env[
                    'webshop.fail.notification'].sudo().search([]):
                    if user.email:
                        post_log.sudo().action_send_fail_notification_mail(
                            lang=user.user_id.partner_id.lang,
                            email=user.email,
                            user=user.user_id.name,
                            product=self.name,
                            synctime=time,
                            response=post_api.content,
                            api_name='Stock API')
        return True

    @api.multi
    def action_compute_pcf_max_qty(self):
        if not self.env.user.has_group(
                'markant_webshop.group_markant_pcf_recompute'):
            raise UserError(_('Sorry, You do not have access rights to '
                              'perform this action.'))
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)])

        log_items = []
        retries = 0
        if api_config:
            retries = api_config.api_attempts
        for product in self:
            if product.configurable_ok and \
                    product.webshop_boolean_variant and \
                    product.active:
                product_tmpl_id = product.product_tmpl_id and \
                                  product.product_tmpl_id.id
                bom = self.env['mrp.bom']._bom_find(
                    product_tmpl=self.env['product.template'].browse(
                        product_tmpl_id))
                if bom:
                    status = 'pass'
                    reason = ''
                    qty = 1
                    max_producible_qty = self.get_all_lines(
                        product_tmpl_id, product.id, qty)
                    if max_producible_qty == '<h2>Can not produce.</h2>':
                        result = 0
                    else:
                        max_producible_qty_lst = max_producible_qty.split(' ')
                        result = max_producible_qty_lst[2]

                    product.write({
                        'pcf_max_producible_qty': float(result)
                    })
                    product.with_delay(max_retries=retries).webshop_api_stock(
                        api_config)
                else:
                    status = 'fail'
                    reason = 'BoM not Found for ' + \
                             product.product_tmpl_id.name
            if not product.configurable_ok and \
                    product.webshop_boolean_variant and \
                    product.active:
                status = 'pass'
                reason = ''
                result = product.virtual_available
                if result <= 0:
                    result = 0
                product.write({
                    'pcf_max_producible_qty': result
                })
                product.with_delay(max_retries=retries).webshop_api_stock(
                    api_config)

            log_items.append((0, 0, {
                'product_id': product.id,
                'status': status,
                'reason': reason
            }))

        if log_items:
            self.env['pcf.max.qty.log'].create({
                'date': fields.Datetime.now(),
                'user_id': self.env.user.id,
                'log_item_ids': log_items
            })
