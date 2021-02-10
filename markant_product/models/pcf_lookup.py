import math
from itertools import chain

from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning
from odoo.tools import float_round


class PCFLookup(models.AbstractModel):
    _name = 'pcf.lookup'
    _description = 'PCF Lookup'

    @api.model
    def get_bom(self, bom_id=False, product_id=False, line_qty=False,
                line_id=False, level=False):

        # To process the multi level BoM
        bom = self.env['mrp.bom'].browse(bom_id)
        product_rec = self.env['product.product'].browse(product_id)
        final_attribute_list = product_rec.attribute_value_ids.ids
        self.check_for_multi_bom_scenario(product_rec, bom,
                                          final_attribute_list)

        lines = self._get_bom(bom_id=bom_id, product_id=product_id,
                              line_qty=line_qty, line_id=line_id, level=level)
        return self.env.ref('markant_product.report_mrp_bom_line_pcf_lookup').render({'data': lines})

    def _get_operation_line(self, routing, qty, level):
        operations = []
        total = 0.0
        for operation in routing.operation_ids:
            operation_cycle = float_round(qty / operation.workcenter_id.capacity, precision_rounding=1, rounding_method='UP')
            duration_expected = operation_cycle * operation.time_cycle + operation.workcenter_id.time_stop + operation.workcenter_id.time_start
            total = ((duration_expected / 60.0) * operation.workcenter_id.costs_hour)
            operations.append({
                'level': level or 0,
                'operation': operation,
                'name': operation.name + ' - ' + operation.workcenter_id.name,
                'duration_expected': duration_expected,
                'total': self.env.user.company_id.currency_id.round(total),
            })
        return operations

    def _get_bom_reference(self, bom):
        return bom.display_name

    def _get_bom(self, bom_id=False, product_id=False, line_qty=False, line_id=False, level=False):
        bom = self.env['mrp.bom'].browse(bom_id)
        bom_quantity = line_qty
        if line_id:
            current_line = self.env['mrp.bom.line'].browse(int(line_id))
            bom_quantity = current_line.product_uom_id._compute_quantity(line_qty, bom.product_uom_id)
        # Display bom components for current selected product variant
        if product_id:
            product = self.env['product.product'].browse(int(product_id))
        else:
            product = bom.product_id or bom.product_tmpl_id.product_variant_id
        if product:
            attachments = self.env['mrp.document'].search(['|', '&', ('res_model', '=', 'product.product'),
            ('res_id', '=', product.id), '&', ('res_model', '=', 'product.template'), ('res_id', '=', product.product_tmpl_id.id)])
        else:
            product = bom.product_tmpl_id
            attachments = self.env['mrp.document'].search([('res_model', '=', 'product.template'), ('res_id', '=', product.id)])
        # operations = self._get_operation_line(bom.routing_id, float_round(bom_quantity / bom.product_qty, precision_rounding=1, rounding_method='UP'), 0)
        lines = {
            'bom': bom,
            'bom_qty': bom_quantity,
            'bom_prod_name': product.display_name,
            'currency': self.env.user.company_id.currency_id,
            'product': product,
            'prod_type': product.type,
            'prod_available_qty': product.qty_available,
            'prod_free_qty': product.free_stock_qty,
            'code': bom and self._get_bom_reference(bom) or '',
            'price': product.uom_id._compute_price(product.standard_price, bom.product_uom_id) * bom_quantity,
            # 'total': sum([op['total'] for op in operations]),
            'total': 0,
            'level': level or 0,
            # 'operations': operations,
            # 'operations_cost': sum([op['total'] for op in operations]),
            'attachments': attachments,
            # 'operations_time': sum([op['duration_expected'] for op in operations])
        }
        components, total = self._get_bom_lines(bom, bom_quantity, product, line_id, level)
        lines['components'] = components
        lines['total'] += total
        return lines

    def _get_bom_lines(self, bom, bom_quantity, product, line_id, level):
        components = []
        total = 0
        for line in bom.bom_line_ids:
            line_quantity = (bom_quantity / (bom.product_qty or 1.0)) * line.product_qty
            if line._skip_bom_line(product):
                continue
            price = line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id) * line_quantity
            if line.child_bom_id:
                factor = line.product_uom_id._compute_quantity(line_quantity, line.child_bom_id.product_uom_id) / line.child_bom_id.product_qty
                sub_total = self._get_price(line.child_bom_id, factor, line.product_id)
            else:
                sub_total = price
            sub_total = self.env.user.company_id.currency_id.round(sub_total)
            components.append({
                'prod_id': line.product_id.id,
                'prod_name': line.product_id.display_name,
                'prod_type': line.product_id.type,
                'code': line.child_bom_id and self._get_bom_reference(line.child_bom_id) or '',
                'prod_qty': line_quantity,
                'prod_uom': line.product_uom_id.name,
                'prod_available_qty': line.product_id.qty_available,
                'prod_free_qty': line.product_id.free_stock_qty,
                'prod_cost': self.env.user.company_id.currency_id.round(price),
                'parent_id': bom.id,
                'bom_type': bom.type,
                'line_id': line.id,
                'level': level or 0,
                'total': sub_total,
                'child_bom': line.child_bom_id.id,
                'phantom_bom': line.child_bom_id and line.child_bom_id.type == 'phantom' or False,
                'attachments': self.env['mrp.document'].search(['|', '&',
                    ('res_model', '=', 'product.product'), ('res_id', '=', line.product_id.id), '&', ('res_model', '=', 'product.template'), ('res_id', '=', line.product_id.product_tmpl_id.id)]),

            })
            total += sub_total
        return components, total

    def _get_price(self, bom, factor, product):
        price = 0
        if bom.routing_id:
            # routing are defined on a BoM and don't have a concept of quantity.
            # It means that the operation time are defined for the quantity on
            # the BoM (the user produces a batch of products). E.g the user
            # product a batch of 10 units with a 5 minutes operation, the time
            # will be the 5 for a quantity between 1-10, then doubled for
            # 11-20,...
            operation_cycle = float_round(factor, precision_rounding=1, rounding_method='UP')
            operations = self._get_operation_line(bom.routing_id, operation_cycle, 0)
            price += sum([op['total'] for op in operations])

        for line in bom.bom_line_ids:
            if line._skip_bom_line(product):
                continue
            if line.child_bom_id:
                qty = line.product_uom_id._compute_quantity(line.product_qty * factor, line.child_bom_id.product_uom_id) / line.child_bom_id.product_qty
                sub_price = self._get_price(line.child_bom_id, qty, line.product_id)
                price += sub_price
            else:
                prod_qty = line.product_qty * factor
                not_rounded_price = line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id) * prod_qty
                price += self.env.user.company_id.currency_id.round(not_rounded_price)
        return price

    @api.model
    def _get_display_data(self, bom_id, searchProduct, searchQty=0):
        lines = {}
        bom = self.env['mrp.bom'].browse(bom_id)
        bom_quantity = searchQty or bom.product_qty
        bom_product_variants = {}
        bom_uom_name = ''

        if bom:
            bom_uom_name = bom.product_uom_id.name

            # Get variants used for search
            if not bom.product_id:
                for variant in bom.product_tmpl_id.product_variant_ids:
                    bom_product_variants[variant.id] = variant.display_name

        lines = self._get_bom(bom_id, product_id=searchProduct,
                              line_qty=bom_quantity, level=1)
        return {
            'lines': lines,
            'variants': bom_product_variants,
            'bom_uom_name': bom_uom_name,
            'bom_qty': bom_quantity,
            'is_variant_applied': self.env.user.user_has_groups(
                'product.group_product_variant') and len(
                bom_product_variants) > 1,
            'is_uom_applied': self.env.user.user_has_groups('uom.group_uom')
        }

    @api.model
    def get_html(self, searchProductTmpl=False, searchProduct=False,
                 searchQty=1):

        bom = self.env['mrp.bom']._bom_find(
            product_tmpl=
            self.env['product.template'].browse(searchProductTmpl))
        if not bom:
            raise Warning(_('Sorry, No BoM defined for this Product.'))

        # Create Sub BoMs on the fly
        product_id = self.env['product.product'].browse(searchProduct)
        final_attribute_list = product_id.attribute_value_ids.ids
        self.check_for_multi_bom_scenario(product_id, bom,
                                          final_attribute_list)

        res = self._get_display_data(
            bom_id=bom.id,
            searchProduct=searchProduct,
            searchQty=searchQty)
        res['lines']['report_type'] = 'html'
        res['lines']['report_structure'] = 'all'
        res['lines']['has_attachments'] = False
        res['lines'] = self.env.ref(
            'markant_product.report_mrp_bom_pcf_lookup').render(
            {'data': res['lines']})
        return res

    @api.model
    def get_all_lines(self, product_tmpl_id=False, product_id=False, qty=1):
        bom = self.env['mrp.bom']._bom_find(
            product_tmpl=self.env['product.template'].browse(product_tmpl_id))
        bom_id = bom.id
        child_bom_ids = []
        unfolded = True
        product_id = self.env['product.product'].browse(product_id)

        data = self._get_bom(bom_id=bom_id, product_id=product_id.id,
                             line_qty=qty)

        def get_sub_lines(bom, product_id, line_qty, line_id, level):
            data = self._get_bom(bom_id=bom.id, product_id=product_id,
                                 line_qty=line_qty, line_id=line_id,
                                 level=level)
            bom_lines = data['components']
            lines = []
            for bom_line in bom_lines:
                lines.append({
                    'name': bom_line['prod_name'],
                    'type': 'bom',
                    'quantity': bom_line['prod_qty'],
                    'uom': bom_line['prod_uom'],
                    'prod_cost': bom_line['prod_cost'],
                    'bom_cost': bom_line['total'],
                    'level': bom_line['level'],
                    'code': bom_line['code'],
                    'prod_type': bom_line['prod_type'],
                    'prod_free_qty': bom_line['prod_free_qty'],
                    'parent_id': bom_line['parent_id'],
                    'prod_id': bom_line['prod_id'],
                    'bom_type': bom_line['bom_type'],
                })
                if bom_line['child_bom'] and (unfolded or bom_line['child_bom'] in child_bom_ids):
                    line = self.env['mrp.bom.line'].browse(bom_line['line_id'])
                    lines += (get_sub_lines(line.child_bom_id, line.product_id, bom_line['prod_qty'], line, level + 1))
            # if data['operations']:
            #     lines.append({
            #         'name': _('Operations'),
            #         'type': 'operation',
            #         'quantity': data['operations_time'],
            #         'uom': _('minutes'),
            #         'bom_cost': data['operations_cost'],
            #         'level': level,
            #     })
            #     for operation in data['operations']:
            #         if unfolded or 'operation-' + str(bom.id) in child_bom_ids:
            #             lines.append({
            #                 'name': operation['name'],
            #                 'type': 'operation',
            #                 'quantity': operation['duration_expected'],
            #                 'uom': _('minutes'),
            #                 'bom_cost': operation['total'],
            #                 'level': level + 1,
            #             })
            return lines

        product = product_id or bom.product_id or \
                  bom.product_tmpl_id.product_variant_id
        pdf_lines = get_sub_lines(bom, product, qty, False, 1)

        can_not_produce = False
        wtf_calculation = []
        all_levels = range(10)
        running_level = 0
        for line in pdf_lines:
            if line.get('prod_type') and line['prod_type'] != 'consu':
                if line['level'] in all_levels:
                    if line['prod_free_qty']/line['quantity'] > 0:
                        current_level = line['level']
                        if running_level == current_level:
                            wtf_calculation[-1].append(math.floor(
                                line['prod_free_qty']/line['quantity']))
                        else:
                            wtf_calculation.append(
                                [math.floor(
                                    line['prod_free_qty'] / line['quantity']
                                )]
                            )
                            running_level = current_level
                    else:
                        product_bom = self.env['mrp.bom']._bom_find(
                            product_tmpl=self.env['product.product'].browse(
                                line['prod_id']).product_tmpl_id)
                        if not product_bom or product_bom.type == 'normal':
                            can_not_produce = True
                            break
                        else:
                            pass

        if can_not_produce or not wtf_calculation:
            return '<h2>Can not produce.</h2>'
        else:
            producible_qty = min([item for sublist in wtf_calculation
                                  for item in sublist])
            return '<h2>Can produce %s quantity.<h2>' % \
                   producible_qty

    @api.model
    def check_for_multi_bom_scenario(self, product_id, bom,
                                     final_attribute_list, context=None):
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
                            ('attr_mapping_id', '=', conf_line.id)]
                        ).manuf_prod_attr_ids

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

    @api.model
    def create_products_for_bom(self, new_prod_attr_vals_lst, conf_line):
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

        combination = self.env[
            'product.template.attribute.value'].sudo().search([
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

            product_variant = self.env['product.product'].sudo().create({
                'product_tmpl_id': product_tmpl_id.id,
                'attribute_value_ids': [
                    (6, 0, attribute_values.ids)],
                'default_code': default_code,
            })
        return product_variant
