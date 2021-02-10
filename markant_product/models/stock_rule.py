from collections import OrderedDict
from itertools import chain

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockRule(models.Model):
    _inherit = 'stock.rule'

    # Override main method, to process Parent-Child BoM.
    # While processing BoM(s) need to create product variant(s) on the fly &
    # add it to Components tab of related BoM(s).
    #
    # All above process done while confirming the Sale Order (SO).
    @api.multi
    def _run_manufacture(self, product_id, product_qty, product_uom,
                         location_id, name, origin, values):
        Production = self.env['mrp.production']
        ProductionSudo = Production.sudo().with_context(
            force_company=values['company_id'].id)
        bom = self._get_matching_bom(product_id, values)
        if not bom:
            msg = _(
                'There is no Bill of Material found for the product %s. '
                'Please define a Bill of Material for this product.') % (
                  product_id.display_name,)
            raise UserError(msg)

        # ### Multi BoM Scenario *** Start *** ####################
        final_attribute_list = product_id.attribute_value_ids.ids

        self.check_for_multi_bom_scenario(product_id, bom,
                                          final_attribute_list)
        # ### Multi BoM Scenario *** End *** ######################

        # create the MO as SUPERUSER because the current user may not have the
        # rights to do it (mto product launched by a sale for example)
        production = ProductionSudo.create(
            self._prepare_mo_vals(product_id, product_qty, product_uom,
                                  location_id, name, origin, values, bom))
        origin_production = values.get('move_dest_ids') and \
                            values['move_dest_ids'][
                                0].raw_material_production_id or False
        orderpoint = values.get('orderpoint_id')
        if orderpoint:
            production.message_post_with_view(
                'mail.message_origin_link',
                values={'self': production, 'origin': orderpoint},
                subtype_id=self.env.ref('mail.mt_note').id)
        if origin_production:
            production.message_post_with_view(
                'mail.message_origin_link',
                values={'self': production, 'origin': origin_production},
                subtype_id=self.env.ref('mail.mt_note').id)
        return True

    @api.multi
    def check_for_multi_bom_scenario(self, product_id, bom,
                                     final_attribute_list, context=None):
        self.ensure_one()

        # Init base record/object for prefetch
        prefetch = self.env['base']._prefetch

        # Check the `bom` is Parent BoM or not,
        # If there is no product variant then its consider as Parent BoM
        # So, Need to execute below code & create separate BoM for its variant
        if not bom.product_id:

            # Prefetch record(s) for good performance
            configurator_lines = []
            for conf_line in bom.sudo().configurator_line_ids:
                record = conf_line.sudo().with_prefetch(prefetch)
                configurator_lines.append(record)

            # Create Components(product.product)
            # for Configurable Products(product.template)
            for conf_line in configurator_lines:
                new_prod_attr_vals_lst = []
                config_attr_is_combo = False
                for line in conf_line.attribute_value_mapping_ids:
                    manuf_line_attr_vals = [
                        val.id for val in line.manuf_prod_attr_val_ids]

                    config_attr_is_combo = \
                        conf_line.attribute_mapping_ids.sudo().search([
                            ('config_prod_attr_id', '=',
                             line.config_prod_attr_val_id.attribute_id.id),
                            ('attr_mapping_id', '=', conf_line.id)])\
                        .manuf_prod_attr_ids

                    if len(config_attr_is_combo) > 1:
                        matched_attrs = list(set(manuf_line_attr_vals)
                                             & set(final_attribute_list))
                        if len(matched_attrs) == len(config_attr_is_combo) \
                                and all(elem in final_attribute_list
                                        for elem in matched_attrs):
                            new_prod_attr_vals_lst.append(
                                line.config_prod_attr_val_id.id)
                    else:
                        if any(elem in final_attribute_list
                               for elem in manuf_line_attr_vals):
                            new_prod_attr_vals_lst.append(
                                line.config_prod_attr_val_id.id)

                if len(new_prod_attr_vals_lst) == len(
                        conf_line.product_tmpl_id.
                        valid_product_template_attribute_line_ids):
                    # number of attribute values passed is same as
                    # the configuration of attributes on the template

                    product_variant = self.create_products_for_bom(
                        new_prod_attr_vals_lst, conf_line)

                    if product_variant.configurable_ok and \
                            product_variant.standard_price == 0 and \
                            product_variant.bom_count > 0 and \
                            product_variant.valuation != 'real_time':
                        product_variant.button_bom_cost()

                    if conf_line.product_tmpl_id == \
                            product_variant.product_tmpl_id:

                        existing_components = []
                        for line in bom.bom_line_ids:

                            # Get the record-set of attribute value(s)
                            # sorted by Id
                            apply_on_variants = [
                                attr for attr in
                                line.attribute_value_ids.sorted(
                                    lambda o: o.id)]
                            existing_components.append([line.product_id.id,
                                                        line.product_qty,
                                                        line.product_uom_id.id,
                                                        apply_on_variants])

                        # Here we can get direct record-set but we need to
                        # sort it by Id in order to compare with another list
                        manuf_attr = [
                            attr_line.manuf_prod_attr_val_ids.ids
                            for attr_line in
                            conf_line.attribute_value_mapping_ids
                            if attr_line.config_prod_attr_val_id.id in
                            product_variant.attribute_value_ids.ids]

                        if len(config_attr_is_combo) > 1:
                            for each_lst in manuf_attr:
                                matched_attrs = list(
                                    set(each_lst) & set(final_attribute_list))
                                if len(matched_attrs) == \
                                        len(config_attr_is_combo) and \
                                        all(elem in final_attribute_list
                                            for elem in matched_attrs):
                                    manuf_attr = [each_lst]

                        # Get the flat list of attribute value(s) id
                        flat_manuf_lst = list(chain.from_iterable(manuf_attr))

                        # Get the record-set of attribute value(s)
                        # sorted by Id
                        flat_manuf_attr = list(chain.from_iterable(
                            self.env['product.attribute.value'].sudo().browse(
                                flat_manuf_lst).sorted(lambda o: o.id)))

                        cond_check = []
                        for existing_component in existing_components:
                            e_apply_on_variants = existing_component.pop(3)

                            if [product_variant.id, conf_line.product_qty,
                                    conf_line.product_uom_id.id] == \
                                    existing_component and \
                                    flat_manuf_attr == e_apply_on_variants:
                                cond_check.append(True)
                            else:
                                cond_check.append(False)

                        if True not in cond_check:
                            bom.sudo().bom_line_ids = [
                                (0, 0, {'product_id': product_variant.id,
                                        'product_qty': conf_line.product_qty,
                                        'attribute_value_ids': [
                                            (4, attr.id) for attr in
                                            flat_manuf_attr],
                                        'product_uom_id':
                                            conf_line.product_uom_id.id,
                                        'auto_create': True})]
        return True

    @api.multi
    def create_products_for_bom(self, new_prod_attr_vals_lst, conf_line):
        self.ensure_one()

        product_tmpl_id = conf_line.product_tmpl_id
        sequence_no = conf_line.sequence_no
        parent_bom = conf_line.bom_id

        # Init base record/object for prefetch
        prefetch = self.env['base']._prefetch

        # Prefetch record(s) for good performance
        product_tmpl_id = self.env['product.template'].sudo().browse(
            product_tmpl_id.id).with_prefetch(prefetch)

        attribute_values = self.env['product.attribute.value'].sudo().browse(
            new_prod_attr_vals_lst)._without_no_variant_attributes()

        combination = self.env['product.template.attribute.value'].sudo().search([
            ('product_tmpl_id', '=', product_tmpl_id.id),
            ('product_attribute_value_id', 'in', attribute_values.ids),
        ])

        product_variant = product_tmpl_id._get_variant_for_combination(
            combination)
        if not product_variant or not product_variant.active:
            if not product_tmpl_id.with_context(
                    markant_archive_check=True)._is_combination_possible(
                    combination, parent_combination=None):
                # Variant creation is not possible
                # with given combination
                raise UserError(_('The user tried to create an invalid '
                                  'variant for the product: %s '
                                  '(Sequence No: %s)\n'
                                  'BoM reference: %s') %
                                (product_tmpl_id.name, sequence_no,
                                 parent_bom.product_tmpl_id.name))

            default_code = product_tmpl_id.d_number_generator(attribute_values)

            # ##############################################################
            # Image for this specific variants will be pulled once a day
            # with help of Scheduled Action --
            # `Markant Product: Get Image from Media Bank`
            # ##############################################################

            product_variant = self.env['product.product'].sudo(). \
                create({
                    'product_tmpl_id': product_tmpl_id.id,
                    'attribute_value_ids': [
                        (6, 0, attribute_values.ids)],
                    'default_code': default_code,
                })
        return product_variant
