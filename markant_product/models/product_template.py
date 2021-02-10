import base64
import json
import requests
from io import BytesIO
import logging
from collections import OrderedDict
import itertools

from odoo import api, fields, models, tools, _
from odoo.exceptions import AccessError, Warning, UserError, ValidationError
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.depends('product_variant_ids', 'product_variant_ids.default_code')
    def _compute_default_code(self):
        unique_variants = self.filtered(
            lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            if template.configurable_ok:
                template.default_code = ''
            else:
                template.default_code = \
                    template.product_variant_ids.default_code
        for template in (self - unique_variants):
            template.default_code = ''

    configurable_ok = fields.Boolean(string='Configurable')
    first_digit_article_code = fields.Char(string='First Digit Article Code',
                                           copy=False)
    product_config_steps_ids = fields.One2many('product.config.steps.attr',
                                               'product_tmpl_id',
                                               string='Configuration Steps')
    old_item_number = fields.Char(string='Old Item Number')
    used_in_bom_config_count = fields.Integer('# of BoM Where is Used',
                                              compute='_used_in_bom_conf_count')
    obsolete_product = fields.Boolean(string='End of life', default=False)
    free_stock_qty = fields.Float('Free Stock', compute='_compute_free_stock_qty',
                                  digits=dp.get_precision('Product Unit of Measure'), store=True)

    def _compute_free_stock_qty(self):
        for template in self:
            variant_reserved_sum = 0
            for p in template.product_variant_ids:
                variant_reserved = p.get_reserved_qty(p.id)
                variant_reserved_sum += variant_reserved
            template.free_stock_qty = template.qty_available - variant_reserved_sum

    @api.multi
    def _compute_used_in_bom_count(self):
        for template in self:
            template.used_in_bom_count = self.env['mrp.bom'].search_count(
                [('bom_line_ids.product_id', 'in',
                  template.product_variant_ids.ids),
                 ('active', '=', True)])

    @api.multi
    def action_used_in_bom(self):
        self.ensure_one()
        action = self.env.ref('mrp.mrp_bom_form_action').read()[0]
        action['domain'] = [
            ('bom_line_ids.product_id', 'in', self.product_variant_ids.ids),
            ('active', '=', True)]
        return action

    @api.multi
    def _used_in_bom_conf_count(self):
        for template in self:
            template.used_in_bom_config_count = self.env['mrp.bom'] \
                .search_count([('configurator_line_ids.product_tmpl_id', '=',
                                template.id),
                               ('active', '=', True)])

    @api.multi
    def action_used_in_bom_configurator(self):
        self.ensure_one()
        action = self.env.ref('mrp.mrp_bom_form_action').read()[0]
        action['domain'] = [
            ('configurator_line_ids.product_tmpl_id', '=', self.id),
            ('active', '=', True)]
        return action

    @api.multi
    def action_set_incremental(self):
        for record in self:
            num = 0
            for line in record.attribute_line_ids:
                num += 5
                line.desc_sequence = num

    def d_number_generator(self, attribute_values):
        default_code = ''
        check_for_d_number = OrderedDict()
        for line in self.attribute_line_ids.sorted('sequence'):
            check_for_d_number.update({line.attribute_id.id:
                                       line.include_inside_d})

        for key, val in check_for_d_number.items():
            for attribute_value in attribute_values:
                if key == attribute_value.attribute_id.id and \
                        val and attribute_value.article_code:
                    default_code += attribute_value.article_code

        if self.first_digit_article_code:
            default_code = self.first_digit_article_code + default_code
        return default_code

    @api.constrains('attribute_line_ids')
    def check_unique_desc_seq(self):
        if self.attribute_line_ids:
            seq_list = [line.desc_sequence for line in self.attribute_line_ids]
            if len(seq_list) != len(set(seq_list)):
                raise ValidationError(_('Description Sequence of variants '
                                        'must be unique.'))

    @api.multi
    def write(self, vals):
        if vals.get('obsolete_product'):
            for template in self:
                for prod in template.product_variant_ids:
                    prod.obsolete_product = True
                    
        if 'uom_id' in vals:
            new_uom = self.env['uom.uom'].browse(vals['uom_id'])
            updated = self.filtered(lambda template: template.uom_id != new_uom)
            done_moves = self.env['stock.move'].search(
                [('product_id', 'in', updated.with_context(active_test=False)
                  .mapped('product_variant_ids').ids)], limit=1)
            if done_moves:
                raise UserError(_("You cannot change the unit of measure from "
                                  "( %s ) to ( %s ) as there are already stock "
                                  "moves for this product ( %s ). If you want "
                                  "to change the unit of measure, you should "
                                  "rather archive this product and create "
                                  "a new one.") %
                                (self.uom_id.name, new_uom.name, self.name))
        res = super(ProductTemplate, self).write(vals)
        for prod in self:
            for attribute_line in prod.attribute_line_ids:
                if prod.configurable_ok and \
                        attribute_line.attribute_id.create_variant != \
                        'dynamic':
                    raise Warning(_("Product and Attribute combination "
                                    "is wrong."
                                    "\n\nYour configuration should follow "
                                    "below steps\n"
                                    "\n--> If Product is set to "
                                    "`Configurable`"
                                    " then for Attributes "
                                    "(Create Variant option) only possible "
                                    "values is "
                                    "`Only when the product is added "
                                    "to a sales order`"))
                attribute_line.attribute_id.write({
                    'product_tmpl_ids': [(4, prod.id)]
                })
                for att_values in attribute_line.value_ids:
                    att_values.write({
                        'product_tmpl_ids': [(4, prod.id)]
                    })
            product_ids = self.search(
                [('default_code', '=', prod.default_code),
                 ('active', '=', True),
                 ('id', '!=', prod.id)])
            if 'active' in vals:
                if prod.active and prod.default_code and product_ids:
                    raise Warning(_('You are trying to restore product '
                                    '\n(%s : %s).'
                                    '\n\nThere is already an existing '
                                    'active product(s) that exists with '
                                    'the same internal reference! \n(%s)') %
                                  (prod.name, prod.default_code,
                                   ('\n'.join([p.name + " : " + p.default_code
                                               for p in product_ids]))))
                elif prod.used_in_bom_count > 0:
                    raise Warning(_('You cannot Archive this product before '
                                    'removing component from the active '
                                    'BOM list'))
                elif prod.used_in_bom_config_count > 0:
                    raise Warning(
                        _('You cannot Archive this product before '
                          'removing component from the active BOM list'))

            if 'attribute_line_ids' in vals:
                for variant in prod.product_variant_ids:
                    variant.get_name_without_code()
        return res

    # Override method
    @api.multi
    def _create_product_variant(self, combination, log_warning=False):
        """ Create if necessary and possible and return the product variant
        matching the given combination for this template.

        It is possible to create only if the template has dynamic attributes
        and the combination itself is possible.

        :param combination: the combination for which to get or create variant.
            The combination must contain all necessary attributes, including
            those of type no_variant. Indeed even though those attributes won't
            be included in the variant if newly created, they are needed when
            checking if the combination is possible.
        :type combination: recordset of `product.template.attribute.value`

        :param log_warning: whether a warning should be logged on fail
        :type log_warning: bool

        :return: the product variant matching the combination
            if product is active or none
        :rtype: recordset of `product.product`
        """
        self.ensure_one()

        Product = self.env['product.product']

        product_variant = self._get_variant_for_combination(combination)

        # Return product_variant if it's active otherwise create new
        if product_variant and product_variant.active:
            return product_variant

        if not self.has_dynamic_attributes():
            if log_warning:
                _logger.warning('The user #%s tried to create a variant for the non-dynamic product %s.' % (self.env.user.id, self.id))
            return Product

        if not self.with_context(markant_archive_check=True)._is_combination_possible(combination):
            if log_warning:
                _logger.warning('The user #%s tried to create an invalid variant for the product %s.' % (self.env.user.id, self.id))
            return Product

        attribute_values = combination.mapped('product_attribute_value_id')._without_no_variant_attributes()

        default_code = self.d_number_generator(attribute_values)

        media_bank_start_url = \
            self.env.user.company_id.media_bank_start_url
        media_bank_end_url = \
            self.env.user.company_id.media_bank_end_url

        if default_code and len(default_code) > 4:
            image_url = '%s/%s/%s/%s/%s/%s.%s' % (
                media_bank_start_url, default_code[0],
                default_code[1], default_code[2],
                default_code[3], default_code, media_bank_end_url)
            if requests.get(image_url).status_code == 200:
                buffered = BytesIO(requests.get(image_url).content)
                img_base64 = base64.b64encode(buffered.getvalue())
            else:
                img_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC"\
                             "1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAA"\
                             "AASUVORK5CYII=".encode()
        else:
            img_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC"\
                         "1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAA"\
                         "AASUVORK5CYII=".encode()

        vals = {
            'product_tmpl_id': self.id,
            'attribute_value_ids': [(6, 0, attribute_values.ids)],
            'default_code': default_code,
            'image_variant': img_base64
        }
        if self.env.context.get('pcf_lookup', False):
            vals.update({
                'pcf_lookup': True,
            })
        return Product.sudo().create(vals)

    def has_dynamic_attributes(self):
        """Return whether this `product.template` has at least one dynamic
        attribute.

        :return: True if at least one dynamic attribute, False otherwise
        :rtype: bool

        * Markant Requirement *
        If product not marked as Configurable then also create variants,
        As `dynamic` will act as `always` option.
        """
        self.ensure_one()
        if not self.configurable_ok:
            return False
        return any(a.create_variant == 'dynamic' for a in
                   self._get_valid_product_attributes())

    # Copy of ``create_product_variant`` but this
    # one is for the PCF Lookup to pass the context
    @api.multi
    def create_product_variant_pcf_lookup(self, product_template_attribute_value_ids):
        """ Create if necessary and possible and return the id of the product
        variant matching the given combination for this template.

        Note AWA: Known "exploit" issues with this method:

        - This method could be used by an unauthenticated user to generate a
            lot of useless variants. Unfortunately, after discussing the
            matter with ODO, there's no easy and user-friendly way to block
            that behavior.

            We would have to use captcha/server actions to clean/... that
            are all not user-friendly/overkill mechanisms.

        - This method could be used to try to guess what product variant ids
            are created in the system and what product template ids are
            configured as "dynamic", but that does not seem like a big deal.

        The error messages are identical on purpose to avoid giving too much
        information to a potential attacker:
            - returning 0 when failing
            - returning the variant id whether it already existed or not

        :param product_template_attribute_value_ids: the combination for which
            to get or create variant
        :type product_template_attribute_value_ids: json encoded list of id
            of `product.template.attribute.value`

        :return: id of the product variant matching the combination or 0
        :rtype: int
        """
        combination = self.env['product.template.attribute.value'] \
            .browse(json.loads(product_template_attribute_value_ids))

        return self.with_context(pcf_lookup=True).\
                   _create_product_variant(combination,
                                           log_warning=True).id or 0

    @api.multi
    def _get_combination_info(self, combination=False, product_id=False,
                              add_qty=1, pricelist=False,
                              parent_combination=False, only_template=False):
        """ Return info about a given combination.

        Note: this method does not take into account whether the combination is
        actually possible.

        :param combination: recordset of `product.template.attribute.value`

        :param product_id: id of a `product.product`. If no `combination`
            is set, the method will try to load the variant `product_id` if
            it exists instead of finding a variant based on the combination.

            If there is no combination, that means we definitely want a
            variant and not something that will have no_variant set.

        :param add_qty: float with the quantity for which to get the info,
            indeed some pricelist rules might depend on it.

        :param pricelist: `product.pricelist` the pricelist to use
            (can be none, eg. from SO if no partner and no pricelist selected)

        :param parent_combination: if no combination and no product_id are
            given, it will try to find the first possible combination, taking
            into account parent_combination (if set) for the exclusion rules.

        :param only_template: boolean, if set to True, get the info for the
            template only: ignore combination and don't try to find variant

        :return: dict with product/combination info:

            - product_id: the variant id matching the combination (if it exists)

            - product_template_id: the current template id

            - display_name: the name of the combination

            - price: the computed price of the combination, take the catalog
                price if no pricelist is given

            - list_price: the catalog price of the combination, but this is
                not the "real" list_price, it has price_extra included (so
                it's actually more closely related to `lst_price`), and it
                is converted to the pricelist currency (if given)

            - has_discounted_price: True if the pricelist discount policy says
                the price does not include the discount and there is actually a
                discount applied (price < list_price), else False
        """
        self.ensure_one()
        # get the name before the change of context to benefit from prefetch
        display_name = self.name

        quantity = self.env.context.get('quantity', add_qty)
        context = dict(self.env.context, quantity=quantity,
                       pricelist=pricelist.id if pricelist else False)
        product_template = self.with_context(context)

        combination = combination or product_template.env[
            'product.template.attribute.value']

        if not product_id and not combination and not only_template and not product_template.configurable_ok:
            combination = product_template._get_first_possible_combination(
                parent_combination)

        if only_template:
            product = product_template.env['product.product']
        elif product_id and not combination:
            product = product_template.env['product.product'].browse(
                product_id)
        else:
            product = product_template._get_variant_for_combination(combination)

        if product:
            # We need to add the price_extra for the attributes that are not
            # in the variant, typically those of type no_variant, but it is
            # possible that a no_variant attribute is still in a variant if
            # the type of the attribute has been changed after creation.
            no_variant_attributes_price_extra = [
                ptav.price_extra for ptav in combination.filtered(
                    lambda ptav:
                    ptav.price_extra and
                    ptav not in product.product_template_attribute_value_ids
                )
            ]
            if no_variant_attributes_price_extra:
                product = product.with_context(
                    no_variant_attributes_price_extra=no_variant_attributes_price_extra
                )
            list_price = product.price_compute('list_price')[product.id]
            price = product.price if pricelist else list_price
        else:
            product_template = product_template.with_context(
                current_attributes_price_extra=[v.price_extra or 0.0 for v in
                                                combination])
            list_price = product_template.price_compute('list_price')[
                product_template.id]
            price = product_template.price if pricelist else list_price

        filtered_combination = combination._without_no_variant_attributes()
        if filtered_combination:
            display_name = '%s (%s)' % (
            display_name, ', '.join(filtered_combination.mapped('name')))

        if pricelist and pricelist.currency_id != product_template.currency_id:
            list_price = product_template.currency_id._convert(
                list_price, pricelist.currency_id,
                product_template._get_current_company(pricelist=pricelist),
                fields.Date.today()
            )

        price_without_discount = list_price if pricelist and pricelist.discount_policy == 'without_discount' else price
        has_discounted_price = (
                                           pricelist or product_template).currency_id.compare_amounts(
            price_without_discount, price) == 1

        return {
            'product_id': product.id,
            'product_template_id': product_template.id,
            'display_name': display_name,
            'price': price,
            'list_price': list_price,
            'has_discounted_price': has_discounted_price,
        }

    @api.multi
    def action_duplicate_with_bom(self):
        new_prod_lst = []
        for rec in self:
            new_lines = []
            new_rec = rec.copy({
                'name': rec.name + ' (copy)',
            })
            for line in rec.attribute_line_ids:
                new_line = line.copy({'product_tmpl_id': new_rec.id})
                new_lines.append(new_line.id)
            new_prod_lst.append(new_rec.id)
            bom = self.env['mrp.bom']._bom_find(product_tmpl=rec)
            if bom:
                new_conf_lines = []
                for conf_line in bom.configurator_line_ids:
                    att_map_lst = []
                    att_val_map_lst = []

                    for att_line in conf_line.attribute_mapping_ids:
                        att_map_lst.append(att_line.copy().id)
                    for att_val_line in conf_line.attribute_value_mapping_ids:
                        att_val_map_lst.append(att_val_line.copy().id)

                    new_line = conf_line.with_context(
                        {'import_file': True}).copy({
                            'attribute_mapping_ids': [(6, 0, att_map_lst)],
                            'attribute_value_mapping_ids': [
                                (6, 0, att_val_map_lst)]
                    })
                    new_conf_lines.append(new_line.id)

                bom.copy({
                    'product_tmpl_id': new_rec.id,
                    'configurator_line_ids': [(6, 0, new_conf_lines)]
                })
        return {
            'name': 'Products',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'product.template',
            'domain': [('id', 'in', new_prod_lst)],
        }

    # Override method
    @api.multi
    def _is_combination_possible(self, combination, parent_combination=None):
        """
        The combination is possible if it is not excluded by any rule
        coming from the current template, not excluded by any rule from the
        parent_combination (if given)

        Moreover the attributes of the combination must excatly match the
        attributes allowed on the template.

        :param combination: the combination to check for possibility
        :type combination: recordset `product.template.attribute.value`

        :param parent_combination: combination from which `self` is an
            optional or accessory product.
        :type parent_combination: recordset `product.template.attribute.value`

        :return: whether the combination is possible
        :rtype: bool
        """
        self.ensure_one()

        if len(combination) != len(self.valid_product_template_attribute_line_ids):
            # number of attribute values passed is different than the
            # configuration of attributes on the template
            return False

        if self.valid_product_attribute_ids != combination.mapped('attribute_id'):
            # combination has different attributes than the ones configured on the template
            return False

        if self.valid_product_attribute_value_ids < combination.mapped('product_attribute_value_id'):
            # combination has different values than the ones configured on the template
            return False

        variant = self._get_variant_for_combination(combination)

        if self.has_dynamic_attributes():
            if variant and not variant.active:
                # dynamic and the variant has been archived
                # then allow to create new
                if self.env.context.get('markant_archive_check'):
                    return True
                # dynamic and the variant has been archived
                else:
                    return False
        else:
            if self.env.context.get('markant_archive_check') and variant \
                    and not variant.active:
                # not dynamic and the variant has been archived
                # then allow to create new
                return True
            elif not variant or not variant.active:
                # not dynamic, the variant has been archived or deleted
                return False
            else:
                return False

        exclusions = self._get_own_attribute_exclusions()
        if exclusions:
            # exclude if the current value is in an exclusion,
            # and the value excluding it is also in the combination
            for ptav in combination:
                # for exclusion in exclusions.get(ptav.id):
                for exclusion in exclusions.get(ptav.id, []):
                    if exclusion in combination.ids:
                        return False

        parent_exclusions = self._get_parent_attribute_exclusions(
            parent_combination)
        if parent_exclusions:
            for exclusion in parent_exclusions:
                if exclusion in combination.ids:
                    return False

        return True

    # Override method
    @api.multi
    def create_variant_ids(self):
        Product = self.env["product.product"]

        for tmpl_id in self.with_context(active_test=False):
            # Handle the variants for each template separately. This will be
            # less efficient when called on a lot of products with few variants
            # but it is better when there's a lot of variants on one template.
            variants_to_create = []
            variants_to_activate = self.env['product.product']
            variants_to_unlink = self.env['product.product']
            # adding an attribute with only one value should not recreate product
            # write this attribute on every product to make sure we don't lose them
            variant_alone = tmpl_id._get_valid_product_template_attribute_lines().filtered(
                lambda
                    line: line.attribute_id.create_variant == 'always' and len(
                    line.value_ids) == 1).mapped('value_ids')
            for value_id in variant_alone:
                updated_products = tmpl_id.product_variant_ids.filtered(lambda
                                                                            product: value_id.attribute_id not in product.mapped(
                    'attribute_value_ids.attribute_id'))
                updated_products.write(
                    {'attribute_value_ids': [(4, value_id.id)]})

            # Determine which product variants need to be created based on the attribute
            # configuration. If any attribute is set to generate variants dynamically, skip the
            # process.
            # Technical note: if there is no attribute, a variant is still created because
            # 'not any([])' and 'set([]) not in set([])' are True.
            if not tmpl_id.has_dynamic_attributes():
                # Iterator containing all possible `product.attribute.value` combination
                # The iterator is used to avoid MemoryError in case of a huge number of combination.
                all_variants = itertools.product(*(
                    line.value_ids.ids for line in
                tmpl_id.valid_product_template_attribute_line_wnva_ids
                ))
                # Set containing existing `product.attribute.value` combination
                existing_variants = {
                    frozenset(variant.attribute_value_ids.ids)
                    for variant in tmpl_id.product_variant_ids
                }
                # For each possible variant, create if it doesn't exist yet.
                for value_ids in all_variants:
                    value_ids = frozenset(value_ids)
                    if value_ids not in existing_variants:
                        variants_to_create.append({
                            'product_tmpl_id': tmpl_id.id,
                            'attribute_value_ids': [(6, 0, list(value_ids))],
                            'active': tmpl_id.active,
                        })
                        if len(variants_to_create) > 1000:
                            raise UserError(_(
                                'The number of variants to generate is too high. '
                                'You should either not generate variants for each combination or generate them on demand from the sales order. '
                                'To do so, open the form view of attributes and change the mode of *Create Variants*.'))

            # Check existing variants if any needs to be activated or unlinked.
            # - if the product is not active and has valid attributes and attribute values, it
            #   should be activated
            # - if the product does not have valid attributes or attribute values, it should be
            #   deleted
            valid_value_ids = tmpl_id.valid_product_attribute_value_wnva_ids
            valid_attribute_ids = tmpl_id.valid_product_attribute_wnva_ids
            seen_attributes = set(
                p.attribute_value_ids for p in tmpl_id.product_variant_ids if
                p.active)
            for product_id in tmpl_id.product_variant_ids:
                if product_id._has_valid_attributes(valid_attribute_ids,
                                                    valid_value_ids):
                    if not product_id.active and product_id.attribute_value_ids not in seen_attributes:
                        variants_to_activate += product_id
                        seen_attributes.add(product_id.attribute_value_ids)
                else:
                    variants_to_unlink += product_id

            # if variants_to_activate:
            #     variants_to_activate.write({'active': True})

            # create new products
            if variants_to_create:
                Product.create(variants_to_create)

            # Avoid access errors in case the products is shared amongst companies but the underlying
            # objects are not. If unlink fails because of an AccessError (e.g. while recomputing
            # fields), the 'write' call will fail as well for the same reason since the field has
            # been set to recompute.
            if variants_to_unlink:
                variants_to_unlink.check_access_rights('unlink')
                variants_to_unlink.check_access_rule('unlink')
                variants_to_unlink.check_access_rights('write')
                variants_to_unlink.check_access_rule('write')
                variants_to_unlink = variants_to_unlink.sudo()
            # unlink or inactive product
            # try in batch first because it is much faster
            try:
                with self._cr.savepoint(), tools.mute_logger('odoo.sql_db'):
                    variants_to_unlink.unlink()
            except Exception:
                # fall back to one by one if batch is not possible
                for variant in variants_to_unlink:
                    try:
                        with self._cr.savepoint(), tools.mute_logger(
                                'odoo.sql_db'):
                            variant.unlink()
                    # We catch all kind of exception to be sure that the operation doesn't fail.
                    except Exception:
                        # Note: this can still fail if something is preventing from archiving.
                        # This is the case from existing stock reordering rules.
                        variant.write({'active': False})

        # prefetched o2m have to be reloaded (because of active_test)
        # (eg. product.template: product_variant_ids)
        # We can't rely on existing invalidate_cache because of the savepoint.
        self.invalidate_cache()
        return True

    @api.multi
    def check_purchase_method(self):
        for record in self:
            if record.type == 'service' and record.purchase_ok and record.purchase_method == 'receive':
                return False
        return True

    _constraints = [(check_purchase_method, 'Control policy cant be "On received quantities" for product type service and Can be Purchased is true.',
                     ['type', 'purchase_ok', 'purchase_method'])]

    # Copy of `def translate_fields(self, model, id, field=None):`
    # from ir_translation.py
    @api.multi
    def action_translate_product_tmpl_name(self):
        """ Open a view for translating the field(s) of the record (model, id). """
        main_lang = 'en_US'

        # Pass the field = 'name'
        # As for this view we only target the `name` field of Product Template
        field = 'name'

        if not self.env['res.lang'].search_count(
                [('code', '!=', main_lang)]):
            raise UserError(_(
                "Translation features are unavailable until you install an extra translation."))

        # determine domain for selecting translations
        records = self.with_context(lang=main_lang).browse(self.ids)
        domain = ['&', ('res_id', 'in', self.ids),
                  ('name', '=like', self._name + ',%')]

        def make_domain(fld, rec):
            name = "%s,%s" % (fld.model_name, fld.name)
            return ['&', ('res_id', '=', rec.id), ('name', '=', name)]

        # insert missing translations, and extend domain for related fields
        for record in records:
            for name, fld in record._fields.items():
                if not fld.translate:
                    continue

                rec = record
                if fld.related:
                    try:
                        # traverse related fields up to their data source
                        while fld.related:
                            rec, fld = fld.traverse_related(rec)
                        if rec:
                            domain = ['|'] + domain + make_domain(fld, rec)
                    except AccessError:
                        continue

                assert fld.translate and rec._name == fld.model_name
                self.env['ir.translation'].insert_missing(fld, rec)

        action = {
            'name': 'Translate',
            'res_model': 'ir.translation',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'view_id': self.env.ref(
                'base.view_translation_dialog_tree').id,
            'target': 'current',
            'flags': {'search_view': True, 'action_buttons': True},
            'domain': domain,
        }
        if field:
            for record in records:
                fld = record._fields[field]
                if not fld.related:
                    action['context'] = {
                        'search_default_name': "%s,%s" % (
                            fld.model_name, fld.name),
                    }
                else:
                    rec = record
                    try:
                        while fld.related:
                            rec, fld = fld.traverse_related(rec)
                        if rec:
                            action['context'] = {
                                'search_default_name': "%s,%s" % (
                                    fld.model_name, fld.name), }
                    except AccessError:
                        pass
        return action


class ProductProduct(models.Model):
    _inherit = 'product.product'

    default_code = fields.Char(copy=False)
    used_in_bom_config_count = fields.Integer('# of BoM Where is Used',
                                              compute='_used_in_bom_conf_count')
    name_without_code = fields.Text(string='Name without Code', compute='get_name_without_code', translate=True)
    obsolete_product = fields.Boolean(string='End of life', default=False)
    pcf_lookup = fields.Boolean(string='PCF Lookup', default=False, copy=False)
    free_stock_qty = fields.Float('Free Stock', compute='_compute_free_stock_qty',
                                  digits=dp.get_precision('Product Unit of Measure'), store=True)

    _sql_constraints = [
        ('barcode_uniq', 'check(1=1)', "A barcode can only be assigned to one product !"),
    ]

    def get_name_without_code(self):
        for product in self:
            show_attributes = sorted(
                [attribute for attribute in product.product_tmpl_id.attribute_line_ids
                 if not attribute.excl_desc], key=lambda x: x.desc_sequence)

            # if product.default_code:
            #     name = '[' + product.default_code + '] ' + product.name + '\n'
            # else:
            name = product.name + '\n'

            attrs = []
            for template_attr in show_attributes:
                for product_attr in product.attribute_value_ids:
                    if template_attr.attribute_id.id == product_attr.attribute_id.id:
                        attrs.append(product_attr.attribute_id.name + ' : ' + product_attr.name)
            if attrs:
                name += ',\n'.join(attrs)
            product.name_without_code = name

    @api.depends('qty_available')
    def _compute_free_stock_qty(self):
        for product in self:
            qty_on_hand = product.qty_available
            reserved_qty = product.get_reserved_qty(product.id)
            product.free_stock_qty = qty_on_hand - reserved_qty

    def get_reserved_qty(self, product_id):
        all_quant = self.env['stock.quant'].search([
            ('product_id', '=', product_id),
            ('location_id.usage', '=', 'internal')],
            order='quantity DESC')
        sum_of_reserved_quant = 0
        for quant in all_quant:
            sum_of_reserved_quant += quant.reserved_quantity
        return sum_of_reserved_quant

    @api.constrains('default_code', 'barcode')
    def _check_duplicate_default_code(self):
        for prod in self:
            product_ids = self.search([
                ('default_code', '=', prod.default_code),
                ('active', '=', True),
                ('id', '!=', prod.id)])
            product_barcode = self.search([
                ('barcode', '=', prod.barcode),
                ('active', '=', True),
                ('id', '!=', prod.id)])
            if prod.active and prod.default_code and product_ids:
                raise Warning(_('You are trying to create/modify product '
                                '\n(%s : %s).'
                                '\n\nThere is already an existing '
                                'active product(s) that exists with '
                                'the same internal reference! \n(%s)') %
                              (prod.name, prod.default_code,
                               ('\n'.join([p.name + " : " + p.default_code
                                           for p in product_ids]))))
            if prod.active and prod.barcode and product_barcode:
                raise Warning(_('You are trying to create/modify product '
                                '\n(%s : %s).'
                                '\n\nThere is already an existing '
                                'active product(s) that exists with '
                                'the same barcode! \n(%s)') %
                              (prod.name, prod.barcode,
                               ('\n'.join([p.name + " : " + p.barcode
                                           for p in product_barcode]))))

    @api.multi
    def _compute_used_in_bom_count(self):
        for product in self:
            product.used_in_bom_count = self.env['mrp.bom'].search_count(
                [('bom_line_ids.product_id', '=', product.id),
                 ('active', '=', True)])

    @api.multi
    def _used_in_bom_conf_count(self):
        for product in self:
            product.used_in_bom_config_count = self.env['mrp.bom'] \
                .search_count([('configurator_line_ids.product_tmpl_id', 'in',
                                product.product_tmpl_id.ids),
                               ('active', '=', True)])

    @api.multi
    def action_used_in_bom(self):
        self.ensure_one()
        action = self.env.ref('mrp.mrp_bom_form_action').read()[0]
        action['domain'] = [('bom_line_ids.product_id', '=', self.id),
                            ('active', '=', True)]
        return action

    @api.multi
    def action_used_in_bom_configurator(self):
        self.ensure_one()
        action = self.env.ref('mrp.mrp_bom_form_action').read()[0]
        action['domain'] = [('configurator_line_ids.product_tmpl_id', 'in',
                             self.product_tmpl_id.ids),
                            ('active', '=', True)]
        return action

    @api.multi
    def write(self, vals):
        res = super(ProductProduct, self).write(vals)
        for prod in self:
            product_ids = self.search(
                [('default_code', '=', prod.default_code),
                 ('active', '=', True),
                 ('id', '!=', prod.id)])
            product_barcode = self.search(
                [('barcode', '=', prod.barcode),
                 ('active', '=', True),
                 ('id', '!=', prod.id)])
            if 'active' in vals:
                if prod.active and prod.default_code and product_ids:
                    raise Warning(_('You are trying to restore product '
                                    '\n(%s : %s).'
                                    '\n\nThere is already an existing '
                                    'active product(s) that exists with '
                                    'the same internal reference! \n(%s)') %
                                  (prod.name, prod.default_code,
                                   ('\n'.join([p.name + " : " + p.default_code
                                               for p in product_ids]))))
                if prod.active and prod.barcode and product_barcode:
                    raise Warning(_('You are trying to restore product '
                                    '\n(%s : %s).'
                                    '\n\nThere is already an existing '
                                    'active product(s) that exists with '
                                    'the same barcode! \n(%s)') %
                                  (prod.name, prod.barcode,
                                   ('\n'.join([p.name + " : " + p.barcode
                                               for p in product_barcode]))))
                # Check whether is it used in BOM components
                elif prod.used_in_bom_count > 0:
                    raise Warning(_('You cannot Archive this product before '
                                    'removing component from the active BOM list'))
        return res

    # This method should be called once a day by the scheduler
    @api.model
    def _get_product_image(self):
        media_bank_start_url = \
            self.env.user.sudo().company_id.media_bank_start_url
        media_bank_end_url = \
            self.env.user.sudo().company_id.media_bank_end_url

        for product in self.env['product.product'].sudo().search(
                [('configurable_ok', '=', True),
                 ('image_variant', '=', False)]):
            if product.default_code and len(product.default_code) > 4:
                image_url = '%s/%s/%s/%s/%s/%s.%s' % (
                    media_bank_start_url, product.default_code[0],
                    product.default_code[1], product.default_code[2],
                    product.default_code[3], product.default_code,
                    media_bank_end_url)
                if requests.get(image_url).status_code == 200:
                    buffered = BytesIO(requests.get(image_url).content)
                    img_base64 = base64.b64encode(buffered.getvalue())
                else:
                    img_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC" \
                                 "1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAA" \
                                 "AASUVORK5CYII=".encode()
            else:
                img_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC" \
                             "1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAA" \
                             "AASUVORK5CYII=".encode()

            product.image_variant = img_base64

    # This method should be called once a day by the scheduler
    @api.model
    def _remove_pcf_lookup_products(self):
        pcf_prod_obj = self.search([('pcf_lookup', '=', True)])
        already_used = []
        for product in pcf_prod_obj:
            try:
                product.unlink()
            except Exception:
                # Get all the exception product, instead commit the cursor
                already_used.append(product.id)
                pass
        self.env.cr.rollback()
        for product in pcf_prod_obj:
            if product.id not in already_used:
                product.unlink()

    def get_product_multiline_description_sale(self):
        """ Compute a multiline description of this product, in the context of sales
                (do not use for purchases or other display reasons that don't intend to use "description_sale").
            It will often be used as the default description of a sale order line referencing this product.
        """
        show_attributes = sorted(
            [attribute for attribute in self.product_tmpl_id.attribute_line_ids
             if not attribute.excl_desc], key=lambda x: x.desc_sequence)

        if self.default_code:
            name = '[' + self.default_code + '] ' + self.name + '\n'
        else:
            name = self.name + '\n'

        attrs = []
        for template_attr in show_attributes:
            for product_attr in self.attribute_value_ids:
                if template_attr.attribute_id.id == product_attr.attribute_id.id:
                    attrs.append(product_attr.attribute_id.name + ' : ' + product_attr.name)
        if attrs:
            name += ', \n'.join(attrs)
        return name

    @api.multi
    def name_get(self):
        # TDE: this could be cleaned a bit I think

        def _name_get(d):
            name = d.get('name', '')
            code = self._context.get('display_default_code', True) and d.get(
                'default_code', False) or False
            if code:
                name = '[%s] %s' % (code, name)
            return (d['id'], name)

        partner_id = self._context.get('partner_id')
        if partner_id:
            partner_ids = [partner_id, self.env['res.partner'].browse(
                partner_id).commercial_partner_id.id]
        else:
            partner_ids = []

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access_rights("read")
        self.check_access_rule("read")

        result = []

        # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
        # Use `load=False` to not call `name_get` for the `product_tmpl_id`
        self.sudo().read(
            ['name', 'default_code', 'product_tmpl_id', 'attribute_value_ids',
             'attribute_line_ids'], load=False)

        product_template_ids = self.sudo().mapped('product_tmpl_id').ids

        if partner_ids:
            supplier_info = self.env['product.supplierinfo'].sudo().search([
                ('product_tmpl_id', 'in', product_template_ids),
                ('name', 'in', partner_ids),
            ])
            # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
            # Use `load=False` to not call `name_get` for the `product_tmpl_id` and `product_id`
            supplier_info.sudo().read(
                ['product_tmpl_id', 'product_id', 'product_name',
                 'product_code'], load=False)
            supplier_info_by_template = {}
            for r in supplier_info:
                supplier_info_by_template.setdefault(r.product_tmpl_id,
                                                     []).append(r)
        for product in self.sudo():
            # display only the attributes with multiple possible values on the template
            variable_attributes = product.attribute_line_ids.filtered(
                lambda l: len(l.value_ids) > 1).mapped('attribute_id')
            variant = product.attribute_value_ids._variant_name(
                variable_attributes)

            name = variant and "%s (%s)" % (
            product.name, variant) or product.name
            if partner_ids:
                product_supplier_info = supplier_info_by_template.get(
                    product.product_tmpl_id, [])
                sellers = [x for x in product_supplier_info if
                           x.product_id and x.product_id == product]
                if not sellers:
                    sellers = [x for x in product_supplier_info if
                               not x.product_id]
            mydict = {
                'id': product.id,
                'name': name,
                'default_code': product.default_code,
            }
            result.append(_name_get(mydict))
        return result


class ProductManualCreation(models.Model):
    _name = 'product.manual.creation'
    _description = 'Product Manual Creation'
    _rec_name = 'product_tmpl_id'

    product_tmpl_id = fields.Many2one('product.template',
                                      string='Product Template', required=True)
    product_id = fields.Many2one('product.product', string='Product Variant',
                                 readonly=True)
    value_ids = fields.Many2many('product.template.attribute.value',
                                 'product_tmpl_attr_vals_rel',
                                 'rec1', 'rec2',
                                 string='Components', required=True)
    state = fields.Selection([('draft', 'Draft'), ('wait', 'Waiting'),
                              ('success', 'Success'), ('fail', 'Fail')],
                             string='Stage', readonly=True, default='draft')
    remarks = fields.Char(string='Remarks', readonly=True)

    def create_product_variant_manual_common(self):
        remarks = ''

        # Check for given combination is possible or not
        # for creation of particular variant
        if not self.product_tmpl_id.with_context(
                markant_archive_check=True)._is_combination_possible(
            self.value_ids, parent_combination=None):
            remarks += 'Given component combination is not possible.'

        product_variant = self.product_tmpl_id._get_variant_for_combination(
            self.value_ids)

        if product_variant and product_variant.active:
            self.write({
                'product_id': product_variant.id,
                'remarks': 'Variant already exists!',
                'state': 'success'
            })
        elif remarks:
            self.write({
                'remarks': remarks,
                'state': 'fail'
            })
        else:
            product_id = self.product_tmpl_id._create_product_variant(
                self.value_ids, log_warning=False)
            self.write({
                'product_id': product_id.id if product_id else False,
                'state': 'success'
            })

    @api.multi
    def action_change_stage(self):
        for rec in self:
            if rec.state != 'draft':
                raise Warning(_('Please, Select records which are '
                                'in "Draft" stage.'))
            rec.state = 'wait'

    @api.multi
    def action_create_product_variant_manual(self):
        if not self.env.user.has_group(
                'markant_product.group_markant_manual_product_variant_sa'):
            raise UserError(_('Sorry, You do not have access rights to '
                              'perform this action.'))
        for rec in self:
            if rec.state != 'wait':
                raise Warning(_('Please, Select records which are '
                                'in "Waiting" stage.'))
            rec.sudo().create_product_variant_manual_common()

    # This method should be called once a day by the scheduler
    # ==============================================
    # Markant Product: Create Manual Product Variant
    # ==============================================
    @api.model
    def _create_product_variant_manual(self):
        for rec in self.env['product.manual.creation'].sudo().search(
                [('state', '=', 'wait')]):
            rec.sudo().create_product_variant_manual_common()
        return True
