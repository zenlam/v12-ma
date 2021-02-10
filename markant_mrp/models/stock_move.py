from itertools import groupby
from operator import itemgetter

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_round, float_is_zero


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def compute_qty_per_product(self):
        for move in self:
            production_id = move.raw_material_production_id
            if production_id and production_id.product_qty and move.product_uom_qty:
                move.qty_per_product = move.product_uom_qty / production_id.product_qty
            else:
                move.qty_per_product = 0.0

    qty_per_product = fields.Float('Qty Per Product', compute='compute_qty_per_product')

    # def _action_confirm(self, merge=True, merge_into=False):
    #     """ Confirms stock move or put it in waiting if it's linked to
    #     another move.
    #     :param: merge: According to this boolean, a newly confirmed move
    #     will be merged in another move of the same picking sharing
    #     its characteristics.
    #     """
    #
    #     # This code block is coming from mrp/models/stock_move.py
    #     # ----- start -----
    #     moves = self.env['stock.move']
    #     for move in self:
    #         moves |= move.action_explode()
    #     # we go further with the list of ids potentially changed by action_explode
    #     # ------ end ------
    #     #
    #     # From Above code moves pass as self & call the super method,
    #     # Since, we override whole method then we need to
    #     # pass above moves to self
    #     self = moves
    #
    #     # Below code block is coming from stock/models/stock_move.py
    #     # which is modified due to MARKANT requirement...
    #     move_create_proc = self.env['stock.move']
    #     move_to_confirm = self.env['stock.move']
    #     move_waiting = self.env['stock.move']
    #
    #     to_assign = {}
    #     for move in self:
    #         # if the move is preceeded, then it's waiting (if preceeding
    #         # move is done, then action_assign has been called already
    #         # and its state is already available)
    #         if move.move_orig_ids:
    #             move_waiting |= move
    #         else:
    #             if move.procure_method == 'make_to_order':
    #                 move_create_proc |= move
    #             else:
    #                 move_to_confirm |= move
    #         if move._should_be_assigned():
    #             key = (move.group_id.id, move.location_id.id,
    #                    move.location_dest_id.id)
    #             if key not in to_assign:
    #                 to_assign[key] = self.env['stock.move']
    #             to_assign[key] |= move
    #
    #     # create procurements for make to order moves
    #     for move in move_create_proc:
    #         values = move._prepare_procurement_values()
    #         origin = (move.group_id and move.group_id.name or (
    #                 move.origin or move.picking_id.name or "/"))
    #
    #         # Get the current rule related to move to find the action
    #         rule = self.env['procurement.group']._get_rule(
    #             move.product_id, move.location_id, values)
    #         if not rule:
    #             raise UserError(_('No procurement rule found in '
    #                               'location "%s" for product "%s".\n '
    #                               'Check routes configuration.') % (
    #                 move.location_id.display_name,
    #                 move.product_id.display_name))
    #         action = 'pull' if rule.action == 'pull_push' else rule.action
    #
    #         warehouse_id = values.get('warehouse_id')
    #         procurement_grp = values.get('group_id')
    #
    #         # 3 Types of Manufacture Steps
    #         # ----------------------------
    #         # 'mrp_one_step' --> 'Manufacture (1 step)'
    #         # 'pbm'          --> 'Pick components and then manufacture
    #         #                     (2 steps)'
    #         # 'pbm_sam'      --> 'Pick components, manufacture and
    #         #                     then store products (3 steps)'
    #         #
    #         # When it set to `pbm_sam` then we need to amend the qty for
    #         # _run_pull & then related all _run_* will changed automatically...
    #         #
    #         # But if it not set to `pbm_sam` then need to need to amend qty
    #         #
    #         # So, We're going to change the procurement qty instead of
    #         # checking mechanism inside each _run_* method(s)
    #         #
    #         # @todo Need to check all the possbile scenario(s)
    #         #   take place when confirm the SO
    #         #
    #         # available_quantity = self.env['stock.quant']._get_available_quantity(move.product_id, move.location_id)
    #         #
    #         # As Odoo base still checks the `stock.quant` for
    #         # `available_quantity`
    #         # But for MARKANT we need to check the `FORECAST`,
    #         # As they do not want to purchase/produce more
    #         #
    #         # So, for MARKANT...
    #         # `available_quantity` is equal to `forecast_quantity`
    #         available_quantity = move.product_id.virtual_available
    #         product_qty = move.product_uom_qty
    #
    #         if action == 'pull' and \
    #                 warehouse_id.manufacture_steps == 'pbm_sam':
    #             # Test Case(s):
    #             #  #01:  0  <  0  <  1
    #             #       Go to -> else .. if
    #             #       product_qty = 1
    #             #  #02:  0  <  5  <  2
    #             #       Go to -> else .. else
    #             #       product_qty = 0.0
    #             #  #03:  0  <  2  <  3
    #             #       Go to -> if
    #             #       product_qty = 3 - 2 = 1
    #             #  #04:  0  < -2  <  2
    #             #       Go to -> else .. if
    #             #       product_qty = 2
    #
    #             if 0.0 < available_quantity < product_qty:
    #                 product_qty -= available_quantity
    #             else:
    #                 if available_quantity <= 0.0:
    #                     # when FORECAST qty is (0|-)
    #                     pass
    #                 else:
    #                     product_qty = 0.0
    #         else:
    #             if action not in ['pull', 'buy'] and \
    #                     warehouse_id.manufacture_steps != 'pbm_sam':
    #                 if 0.0 < available_quantity < product_qty:
    #                     product_qty -= available_quantity
    #                 else:
    #                     if available_quantity <= 0.0:
    #                         # when FORECAST qty is (0|-)
    #                         pass
    #                     else:
    #                         product_qty = 0.0
    #             if action == 'buy' and \
    #                     warehouse_id.manufacture_steps == 'pbm_sam':
    #                 if 0.0 < available_quantity < product_qty:
    #                     product_qty -= available_quantity
    #                 else:
    #                     if available_quantity <= 0.0:
    #                         # when FORECAST qty is (0|-)
    #                         pass
    #                     else:
    #                         product_qty = 0.0
    #
    #         if product_qty > 0.0:
    #             self.env['procurement.group'].run(
    #                 move.product_id, product_qty, move.product_uom,
    #                 move.location_id,
    #                 move.rule_id and move.rule_id.name or "/",
    #                 origin, values)
    #
    #     move_to_confirm.write({'state': 'confirmed'})
    #     (move_waiting | move_create_proc).write({'state': 'waiting'})
    #
    #     # assign picking in batch for all confirmed move that
    #     # share the same details
    #     for moves in to_assign.values():
    #         moves._assign_picking()
    #     self._push_apply()
    #     if merge:
    #         return self._merge_moves(merge_into=merge_into)
    #     return self

    # def _action_assign(self):
    #     # Below code block is coming from stock/models/stock_move.py
    #     # which is modified due to MARKANT requirement...
    #     """ Reserve stock moves by creating their stock move lines. A stock move is
    #     considered reserved once the sum of `product_qty` for all its move lines is
    #     equal to its `product_qty`. If it is less, the stock move is considered
    #     partially available.
    #     """
    #     assigned_moves = self.env['stock.move']
    #     partially_available_moves = self.env['stock.move']
    #     # Read the `reserved_availability` field of the moves out of the loop to prevent unwanted
    #     # cache invalidation when actually reserving the move.
    #     reserved_availability = {move: move.reserved_availability for move in self}
    #     roundings = {move: move.product_id.uom_id.rounding for move in self}
    #     move_line_vals_list = []
    #     for move in self.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available']):
    #         rounding = roundings[move]
    #         missing_reserved_uom_quantity = move.product_uom_qty - reserved_availability[move]
    #         missing_reserved_quantity = move.product_uom._compute_quantity(missing_reserved_uom_quantity, move.product_id.uom_id, rounding_method='HALF-UP')
    #
    #         if move.location_id.should_bypass_reservation() \
    #                 or move.product_id.type == 'consu':
    #             # create the move line(s) but do not impact quants
    #             if move.product_id.tracking == 'serial' and (move.picking_type_id.use_create_lots or move.picking_type_id.use_existing_lots):
    #                 for i in range(0, int(missing_reserved_quantity)):
    #                     move_line_vals_list.append(move._prepare_move_line_vals(quantity=1))
    #             else:
    #                 to_update = move.move_line_ids.filtered(lambda ml: ml.product_uom_id == move.product_uom and
    #                                                                    ml.location_id == move.location_id and
    #                                                                    ml.location_dest_id == move.location_dest_id and
    #                                                                    ml.picking_id == move.picking_id and
    #                                                                    not ml.lot_id and
    #                                                                    not ml.package_id and
    #                                                                    not ml.owner_id)
    #                 if to_update:
    #                     to_update[0].product_uom_qty += missing_reserved_uom_quantity
    #                 else:
    #                     move_line_vals_list.append(move._prepare_move_line_vals(quantity=missing_reserved_quantity))
    #             assigned_moves |= move
    #         else:
    #             if not move.move_orig_ids:
    #                 # Markant: From now we reserve qty for `make_to_order` too!
    #                 # if move.procure_method == 'make_to_order':
    #                 #     continue
    #                 # If we don't need any quantity, consider the move assigned.
    #                 need = missing_reserved_quantity
    #                 if float_is_zero(need, precision_rounding=rounding):
    #                     assigned_moves |= move
    #                     continue
    #                 # Reserve new quants and create move lines accordingly.
    #                 forced_package_id = move.package_level_id.package_id or None
    #
    #                 # @todo Siddharth Bhalgami
    #                 #   Odoo is taking this qty as available_quantity
    #                 available_quantity = self.env['stock.quant']._get_available_quantity(move.product_id, move.location_id, package_id=forced_package_id)
    #                 if available_quantity <= 0:
    #                     continue
    #                 taken_quantity = move._update_reserved_quantity(need, available_quantity, move.location_id, package_id=forced_package_id, strict=False)
    #                 if float_is_zero(taken_quantity, precision_rounding=rounding):
    #                     continue
    #                 if float_compare(need, taken_quantity, precision_rounding=rounding) == 0:
    #                     assigned_moves |= move
    #                 else:
    #                     partially_available_moves |= move
    #             else:
    #                 # --------------------------------------------------------
    #                 # Need to check this below dead code needed or not
    #                 # --------------------------------------------------------
    #                 # Special case happens when 3 steps manufacture enabled
    #                 # In this we got 2 Move with same procurement group
    #                 # @todo Siddharth Bhalgami
    #                 #   Need to check whether keeps here or
    #                 #   need an extra effort & put it somewhere else
    #                 # print("move.move_orig_ids>>>>>>>>>>>>>>>>>>", move.move_orig_ids)
    #                 # for move_orig_id in move.move_orig_ids:
    #                 #     if move_orig_id.procure_method == 'make_to_order' \
    #                 #             and move.group_id and move_orig_id.group_id \
    #                 #             and move_orig_id.group_id == move.group_id:
    #                 #         # Below code is the copy from above if block
    #                 #         need = missing_reserved_quantity
    #                 #         if float_is_zero(need, precision_rounding=rounding):
    #                 #             assigned_moves |= move_orig_id
    #                 #             continue
    #                 #         # Reserve new quants and create move lines accordingly.
    #                 #         forced_package_id = move_orig_id.package_level_id.package_id or None
    #                 #
    #                 #         available_quantity = self.env[
    #                 #             'stock.quant']._get_available_quantity(
    #                 #             move_orig_id.product_id, move_orig_id.location_id,
    #                 #             package_id=forced_package_id)
    #                 #         if available_quantity <= 0:
    #                 #             continue
    #                 #         taken_quantity = move_orig_id._update_reserved_quantity(
    #                 #             need, available_quantity, move_orig_id.location_id,
    #                 #             package_id=forced_package_id, strict=False)
    #                 #         if float_is_zero(taken_quantity,
    #                 #                          precision_rounding=rounding):
    #                 #             continue
    #                 #         if float_compare(need, taken_quantity,
    #                 #                          precision_rounding=rounding) == 0:
    #                 #             assigned_moves |= move_orig_id
    #                 #         else:
    #                 #             partially_available_moves |= move_orig_id
    #                 #         continue
    #                 # Check what our parents brought and what our siblings took in order to
    #                 # determine what we can distribute.
    #                 # `qty_done` is in `ml.product_uom_id` and, as we will later increase
    #                 # the reserved quantity on the quants, convert it here in
    #                 # `product_id.uom_id` (the UOM of the quants is the UOM of the product).
    #                 move_lines_in = move.move_orig_ids.filtered(lambda m: m.state == 'done').mapped('move_line_ids')
    #                 keys_in_groupby = ['location_dest_id', 'lot_id', 'result_package_id', 'owner_id']
    #
    #                 def _keys_in_sorted(ml):
    #                     return (ml.location_dest_id.id, ml.lot_id.id, ml.result_package_id.id, ml.owner_id.id)
    #
    #                 grouped_move_lines_in = {}
    #                 for k, g in groupby(sorted(move_lines_in, key=_keys_in_sorted), key=itemgetter(*keys_in_groupby)):
    #                     qty_done = 0
    #                     for ml in g:
    #                         qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
    #
    #                     grouped_move_lines_in[k] = qty_done
    #                 move_lines_out_done = (move.move_orig_ids.mapped('move_dest_ids') - move) \
    #                     .filtered(lambda m: m.state in ['done']) \
    #                     .mapped('move_line_ids')
    #
    #                 # As we defer the write on the stock.move's state at the end of the loop, there
    #                 # could be moves to consider in what our siblings already took.
    #                 moves_out_siblings = move.move_orig_ids.mapped('move_dest_ids') - move
    #                 moves_out_siblings_to_consider = moves_out_siblings & (assigned_moves + partially_available_moves)
    #                 reserved_moves_out_siblings = moves_out_siblings.filtered(lambda m: m.state in ['partially_available', 'assigned'])
    #                 move_lines_out_reserved = (reserved_moves_out_siblings | moves_out_siblings_to_consider).mapped('move_line_ids')
    #                 keys_out_groupby = ['location_id', 'lot_id', 'package_id', 'owner_id']
    #
    #                 def _keys_out_sorted(ml):
    #                     return (ml.location_id.id, ml.lot_id.id, ml.package_id.id, ml.owner_id.id)
    #
    #                 grouped_move_lines_out = {}
    #                 for k, g in groupby(sorted(move_lines_out_done, key=_keys_out_sorted), key=itemgetter(*keys_out_groupby)):
    #                     qty_done = 0
    #                     for ml in g:
    #                         qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
    #                     grouped_move_lines_out[k] = qty_done
    #                 for k, g in groupby(sorted(move_lines_out_reserved, key=_keys_out_sorted), key=itemgetter(*keys_out_groupby)):
    #                     grouped_move_lines_out[k] = sum(self.env['stock.move.line'].concat(*list(g)).mapped('product_qty'))
    #
    #                 available_move_lines = {key: grouped_move_lines_in[key] - grouped_move_lines_out.get(key, 0) for key in grouped_move_lines_in.keys()}
    #                 # pop key if the quantity available amount to 0
    #                 available_move_lines = dict((k, v) for k, v in available_move_lines.items() if v)
    #
    #                 if not available_move_lines:
    #                     continue
    #                 for move_line in move.move_line_ids.filtered(lambda m: m.product_qty):
    #                     if available_move_lines.get((move_line.location_id, move_line.lot_id, move_line.result_package_id, move_line.owner_id)):
    #                         available_move_lines[(move_line.location_id, move_line.lot_id, move_line.result_package_id, move_line.owner_id)] -= move_line.product_qty
    #                 for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
    #                     need = move.product_qty - sum(move.move_line_ids.mapped('product_qty'))
    #                     # Check the need quantity again, if is there any
    #                     # quants which are already assigned from stock
    #                     # if move.availability > 0.0:
    #                     #     need -= move.availability
    #
    #                     # `quantity` is what is brought by chained done move lines. We double check
    #                     # here this quantity is available on the quants themselves. If not, this
    #                     # could be the result of an inventory adjustment that removed totally of
    #                     # partially `quantity`. When this happens, we chose to reserve the maximum
    #                     # still available. This situation could not happen on MTS move, because in
    #                     # this case `quantity` is directly the quantity on the quants themselves.
    #                     available_quantity = self.env['stock.quant']._get_available_quantity(
    #                         move.product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True)
    #                     if float_is_zero(available_quantity, precision_rounding=rounding):
    #                         continue
    #                     # FIXME... Siddharth Bhalgami
    #                     #   If linked moves found then reserved_availability
    #                     #   is same as that linked move qty
    #                     taken_quantity = move._update_reserved_quantity(need, max(quantity, available_quantity), location_id, lot_id, package_id, owner_id)
    #                     if float_is_zero(taken_quantity, precision_rounding=rounding):
    #                         continue
    #                     if float_is_zero(need - taken_quantity, precision_rounding=rounding):
    #                         assigned_moves |= move
    #                         break
    #                     partially_available_moves |= move
    #     self.env['stock.move.line'].create(move_line_vals_list)
    #     partially_available_moves.write({'state': 'partially_available'})
    #     assigned_moves.write({'state': 'assigned'})
    #     self.mapped('picking_id')._check_entire_pack()
    #
    #     # This code block is coming from mrp/models/stock_move.py
    #     # ----- start -----
    #     for move in self.filtered(lambda x: x.production_id or x.raw_material_production_id):
    #         if move.move_line_ids:
    #             move.move_line_ids.write({'production_id': move.raw_material_production_id.id,
    #                                       'workorder_id': move.workorder_id.id,})
    #     # ------ end ------
    #
    #     # This code block is coming from markant_stock/models/stock_move.py
    #     # Since this method already override then,
    #     # need to take care of custom changes
    #     # ----- start -----
    #     smoves = self.filtered(lambda x: x.state not in ('done', 'cancel'))
    #     smoves = smoves.filtered(lambda x: x.picking_id or x.backorder_id)
    #     if smoves:
    #         resp = smoves.with_context(checkonlywithoutdone=True)._recompute_state()
        # ------ end ------

    # Override(2) original method of `stock_account` which is already override in `mrp_labour_cost`
    def _account_entry_move(self):
        """ Accounting Valuation Entries """
        self.ensure_one()
        if self.product_id.type not in ['product', 'consu']:
            # Custom Development: allow stock valuation for
            # consumable products also (but with specific condition)
            return False
        if self.product_id.type == 'consu' and (self.picking_type_id and self.picking_type_id.code == 'outgoing'):
            if not self.product_id.kit_component:
                # Custom Development: no stock valuation for consumable products,
                # if not a kit component
                return False
            else:
                if self.product_id.kit_component:
                    if self.product_id.purchase_ok:
                        # If Product is Kit Component & Purchasable then no need DO entry
                        return False
                    else:
                        # Check if this move is belong to KIT or not, if not KIT then follow Odoo base
                        bom = self.env['mrp.bom']._bom_find(product=self.sale_line_id.product_id,
                                                            picking_type=self.picking_type_id)
                        if not bom or (bom and bom.type != 'phantom'):
                            return False
        if self.product_id.type == 'consu' and (self.picking_type_id and self.picking_type_id.code == 'mrp_operation'):
            if not self.product_id.mrp_cost_ok or not self.product_id.labour_type:
                # Custom Development: no stock valuation for consumable products,
                # if labour type is not available
                return False

        if self.product_id.type == 'consu' and (self.picking_type_id and
                                                self.picking_type_id.code not in ['outgoing', 'mrp_operation']):
            # no stock valuation if picking type not set as `outgoing` or `mrp_operation`
            return False

        if self.restrict_partner_id:
            # if the move isn't owned by the company,
            # we don't make any valuation
            return False

        location_from = self.location_id
        location_to = self.location_dest_id
        company_from = self._is_out() and self.mapped(
            'move_line_ids.location_id.company_id') or False
        company_to = self._is_in() and self.mapped(
            'move_line_ids.location_dest_id.company_id') or False

        # Create Journal Entry for products arriving in the company;
        # in case of routes making the link between several
        # warehouse of the same company, the transit location belongs
        # to this company, so we don't need to create accounting entries
        if self._is_in():
            journal_id, acc_src, acc_dest, acc_valuation = \
                self._get_accounting_data_for_valuation()
            if location_from and location_from.usage == 'customer':
                # goods returned from customer
                self.with_context(
                    force_company=company_to.id)._create_account_move_line(
                    acc_dest, acc_valuation, journal_id)
            else:
                self.with_context(
                    force_company=company_to.id)._create_account_move_line(
                    acc_src, acc_valuation, journal_id)

        # Create Journal Entry for products leaving the company
        if self._is_out():
            journal_id, acc_src, acc_dest, acc_valuation = \
                self._get_accounting_data_for_valuation()
            if location_to and location_to.usage == 'supplier':
                # goods returned to supplier
                self.with_context(
                    force_company=company_from.id)._create_account_move_line(
                    acc_valuation, acc_src, journal_id)
            else:
                self.with_context(
                    force_company=company_from.id)._create_account_move_line(
                    acc_valuation, acc_dest, journal_id)

        if self.company_id.anglo_saxon_accounting:
            # Creates an account entry from stock_input to
            # stock_output on a dropship move.
            # https://github.com/odoo/odoo/issues/12687
            journal_id, acc_src, acc_dest, acc_valuation = \
                self._get_accounting_data_for_valuation()
            if self._is_dropshipped():
                self.with_context(force_company=self.company_id.id). \
                    _create_account_move_line(acc_src, acc_dest, journal_id)
            elif self._is_dropshipped_returned():
                self.with_context(force_company=self.company_id.id). \
                    _create_account_move_line(acc_dest, acc_src, journal_id)

        if self.company_id.anglo_saxon_accounting:
            # eventually reconcile together the invoice and valuation
            # accounting entries on the stock interim accounts
            self._get_related_invoices()._anglo_saxon_reconcile_valuation(
                product=self.product_id)
