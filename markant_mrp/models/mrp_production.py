from odoo import api, fields, models, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    last_print_date = fields.Datetime(string="Last Print Date")
    no_of_print = fields.Integer(string="No. of Print")

    @api.multi
    def get_lines_stock_to_pre_movement(self, records):
        material_which_needs_movement = {}

        precision = self.env[
            'decimal.precision'].precision_get(
            'Product Unit of Measure')
        format_qty = '%.{precision}f'.format(
            precision=precision)

        for mo in records:
            mo.action_assign()
            consumed_raw_materials = {}
            for raw_id in mo.move_raw_ids:
                qty = raw_id.product_uom_qty - raw_id.reserved_availability
                if qty != 0:
                    consumed_raw_materials.update({
                        raw_id.product_id: qty,
                    })

            source_loc_id = self.env['stock.inventory']._default_location_id()
            if source_loc_id:
                source_loc = self.env['stock.location'].browse(source_loc_id)
                if not mo.picking_ids:
                    for ck, cv in consumed_raw_materials.items():
                        article = self.env[
                            'sale.order.line'
                        ].get_sale_order_line_multiline_description_sale(ck)

                        if ck in material_which_needs_movement:
                            material_which_needs_movement[ck][0] += \
                                ', ' + mo.name
                            material_which_needs_movement[ck][1] += \
                                ', ' + mo.origin
                            material_which_needs_movement[ck][4] += \
                                float(format_qty % cv)
                        else:
                            origin = mo.origin or ''
                            material_which_needs_movement.update({
                                ck: [mo.name, origin, article, '',
                                     float(format_qty % cv), []]
                            })
                else:
                    for picking_id in mo.picking_ids:
                        if picking_id.location_id == source_loc:
                            needed_raw_materials = {}

                            for move in picking_id.move_ids_without_package:
                                needed_raw_materials.update({
                                    move.product_id: move.product_uom_qty,
                                })

                            for ck, cv in consumed_raw_materials.items():
                                article = self.env[
                                    'sale.order.line'
                                ].get_sale_order_line_multiline_description_sale(ck)
                                if ck not in needed_raw_materials:

                                    if ck in material_which_needs_movement:
                                        material_which_needs_movement[ck][0] += \
                                            ', ' + mo.name
                                        material_which_needs_movement[ck][1] += \
                                            ', ' + mo.origin
                                        material_which_needs_movement[ck][4] += \
                                            float(format_qty % cv)
                                    else:
                                        origin = mo.origin or ''
                                        material_which_needs_movement.update({
                                            ck: [mo.name, origin, article, '',
                                                 float(format_qty % cv), []]
                                        })
                                else:
                                    for nk, nv in needed_raw_materials.items():
                                        if ck == nk and cv > nv:
                                            if ck in material_which_needs_movement:
                                                material_which_needs_movement[
                                                    ck][0] += \
                                                    ', ' + mo.name
                                                material_which_needs_movement[
                                                    ck][1] += \
                                                    ', ' + mo.origin
                                                material_which_needs_movement[
                                                    ck][4] += \
                                                    float(format_qty %
                                                          (cv - nv))
                                            else:
                                                origin = mo.origin or ''
                                                material_which_needs_movement.update(
                                                    {
                                                        ck: [mo.name,
                                                             origin,
                                                             article, '',
                                                             float(
                                                                 format_qty %
                                                                 (cv - nv)
                                                             ), []]
                                                    })

        for key, val in material_which_needs_movement.items():
            product = key
            needed_qty = val[4]
            equal_quant = []
            big_quant = []
            quant_qty = []
            exact_quant = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('quantity', '=', needed_qty),
                ('location_id.usage', '=', 'internal')], order='quantity DESC')

            for same_quant in exact_quant:
                qty = same_quant.quantity - same_quant.reserved_quantity
                quant_qty.append(qty)
                if qty > 0 and qty == needed_qty:
                    equal_quant.append(same_quant)

            large_quant = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('quantity', '>', needed_qty),
                ('location_id.usage', '=', 'internal')], order='quantity DESC')

            for huge_quant in large_quant:
                qty = huge_quant.quantity - huge_quant.reserved_quantity
                quant_qty.append(qty)
                if qty > 0 and qty > needed_qty:
                    big_quant.append(huge_quant)

            combine_quant = []
            if not exact_quant and not large_quant:
                all_quant = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('quantity', '<', needed_qty),
                    ('location_id.usage', '=', 'internal')],
                    order='quantity DESC')
                sum_of_quant = 0.0
                for quant in all_quant:
                    qty = quant.quantity - quant.reserved_quantity
                    quant_qty.append(qty)
                    if 0 < qty < needed_qty:
                        combine_quant.append(quant)
                        sum_of_quant += qty
                        if sum_of_quant >= needed_qty:
                            break

            if equal_quant:
                final_locations = equal_quant[0].location_id.name
                final_locations_id = equal_quant[0].location_id
            elif big_quant:
                final_locations = big_quant[0].location_id.name
                final_locations_id = big_quant[0].location_id
            else:
                final_locations = ''
                final_locations_id = []
                for quant in combine_quant:
                    final_locations += quant.location_id.name + ', '
                    final_locations_id += quant.location_id

            material_which_needs_movement[product][3] += final_locations
            material_which_needs_movement[product][5] += quant_qty
        return material_which_needs_movement
