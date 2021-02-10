from odoo import api, fields, models, registry, SUPERUSER_ID, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    article_description = fields.Text('Order Point')
    article_description_move = fields.Text('Invisible Order Point')
    allow_partial = fields.Boolean(string='Allow Partial?', readonly=True)
    article_description_basic = fields.Text('Basic Order Point', compute="_get_basic_orderpoint", store=True)

    @api.depends('article_description_move')
    def _get_basic_orderpoint(self):
        for move in self:
            new_order = move.article_description_move
            if new_order is False:
                new_order = ''
            if "\n" in new_order:
                move.article_description_basic = new_order[:new_order.find("\n")]
            else:
                move.article_description_basic = new_order

    def action_explode(self):
        """ Explodes pickings """
        # in order to explode a move, we must have a picking_type_id on that
        # move because otherwise the move
        # won't be assigned to a picking and it would be weird to explode
        # a move into several if they aren't
        # all grouped in the same picking.
        if not self.picking_type_id:
            return self
        bom = self.env['mrp.bom'].sudo()._bom_find(
            product=self.product_id, company_id=self.company_id.id)
        if not bom or bom.type != 'phantom':
            return self
        phantom_moves = self.env['stock.move']
        processed_moves = self.env['stock.move']
        factor = self.product_uom._compute_quantity(
            self.product_uom_qty, bom.product_uom_id) / bom.product_qty
        boms, lines = bom.sudo().explode(self.product_id, factor,
                                         picking_type=bom.picking_type_id)
        for bom_line, line_data in lines:
            phantom_moves += self._generate_move_phantom(bom_line,
                                                         line_data['qty'])

        for new_move in phantom_moves:
            # For the PHANTOM, we do change the logic of Odoo base,
            # according to Odoo base if PHANTOM BoM is MTO then
            # for all BoM lines MTO will be passed forcefully.
            # Check method `_generate_move_phantom` in
            # `/mrp/models/stock_move.py`
            #
            # So, We write procure_method field again based on Product.
            # (We do not consider Parent any-more)
            #
            # For Ex. If Parent is `make_to_order`, but Child is only set as
            # `Buy` or `Manufacturer` then for procure method will become
            # `make_to_stock`
            #
            # ******* Adjust Procure Method -- START *******
            # try:
            #     mto_route = self.env['stock.warehouse']._find_global_route(
            #         'stock.route_warehouse0_mto', _('Make To Order'))
            # except:
            #     mto_route = False
            #
            # routes = new_move.product_id.route_ids + \
            #          new_move.product_id.route_from_categ_ids + \
            #          new_move.product_id.warehouse_id.route_ids
            # pull = self.env['stock.rule'].search(
            #     [('route_id', 'in', [x.id for x in routes]),
            #      ('location_src_id', '=', new_move.location_id.id),
            #      ('location_id', '=', new_move.location_dest_id.id),
            #      ('action', '!=', 'push')], limit=1)
            # if pull and (pull.procure_method == 'make_to_order'):
            #     new_move.procure_method = pull.procure_method
            # elif not pull: # If there is no make_to_stock rule either
            #     if mto_route and mto_route.id in [x.id for x in routes]:
            #         new_move.procure_method = 'make_to_order'
            #     else:
            #         new_move.procure_method = 'make_to_stock'
            # ******* Adjust Procure Method -- END *******

            processed_moves |= new_move.action_explode()
        #         if not self.split_from and self.procurement_id:
        #             # Check if procurements have been made to wait for
        #             moves = self.procurement_id.move_ids
        #             if len(moves) == 1:
        #                 self.procurement_id.write({'state': 'done'})
        if processed_moves and self.state == 'assigned':
            # Set the state of resulting moves according to 'assigned' as
            # the original move is assigned
            processed_moves.write({'state': 'assigned'})

        # Save the data if main/parent move is marked as allow partial
        allow_partial = self.allow_partial

        # delete the move with original product which is not relevant anymore
        self.sudo().unlink()

        # Add article description in last line,
        # As in GUI last line consider as first line
        if processed_moves:
            if not processed_moves[0].article_description:
                processed_moves[0].article_description = 'No Order Point'
                processed_moves[0].article_description_move = 'No Order Point'
            processed_moves[0].article_description += \
                '\n' + processed_moves[0].name + '\nQty: ' + str(factor)
            processed_moves[0].article_description_move += \
                '\n' + processed_moves[0].name + '\nQty: ' + str(factor)
        for mov in processed_moves[1:]:
            mov.article_description = False
            mov.article_description_move = processed_moves[0].article_description_move

        # Check for allow partial from parent move reference
        for mov in processed_moves:
            mov.allow_partial = allow_partial

        return processed_moves

    def _get_new_picking_values(self):
        vals = super(StockMove, self)._get_new_picking_values()
        vals['carrier_name_id'] = self.sale_line_id.order_id.carrier_name_id.id
        return vals

    def _action_assign(self):
        res = super(StockMove, self)._action_assign()
        moves = self.filtered(lambda x: x.state not in
                                        ('draft','done', 'cancel'))
        moves = moves.filtered(
            lambda x: x.picking_id.picking_type_id.is_delivery_order or
            x.backorder_id.picking_type_id.is_delivery_order)
        if moves:
            move_ids = moves.ids
            def call_recompute_state():
                dbname = self.env.cr.dbname
                _context = self._context
                db_registry = registry(dbname)
                with api.Environment.manage(), db_registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, _context)
                    env['stock.move'].browse(move_ids).with_context(
                        markant_recompute_state=True)._recompute_state()
            self._cr.after('commit', call_recompute_state)
        return res

    # def _recompute_state(self):
    #     for move in self:
    #         if move.state in ('cancel', 'done', 'draft'):
    #             continue
    #         elif move.reserved_availability == move.product_uom_qty:
    #             move.state = 'assigned'
    #         elif move.reserved_availability and move.reserved_availability <= move.product_uom_qty:
    #             move.state = 'partially_available'
    #         else:
    #             if move.procure_method == 'make_to_order' and not move.move_orig_ids:
    #                 move.state = 'waiting'
    #             elif move.move_orig_ids and not all(orig.state in ('done', 'cancel') for orig in move.move_orig_ids):
    #                 move.state = 'waiting'
    #             else:
    #                 move.state = 'confirmed'

    def _recompute_state(self):
        markant_recompute_state = self.env.context.get('markant_recompute_state', False)
        
        for move in self:
            if move.state in ('cancel', 'done', 'draft'):
                continue
            elif move.reserved_availability == move.product_uom_qty:
                if markant_recompute_state:
                    if move.state != 'assigned':
                        move.state = 'assigned'
                else:
                    move.state = 'assigned'
            elif move.reserved_availability and move.reserved_availability <= move.product_uom_qty:
                if markant_recompute_state:
                    if move.picking_id or move.backorder_id:
                        if move.allow_partial:
                            if move.state != 'partially_available':
                                move.state = 'partially_available'
                        else:
                            if move.state != 'confirmed':
                                move.state = 'confirmed'
                    else:
                        if move.state != 'partially_available':
                            move.state = 'partially_available'
                else:
                    move.state = 'partially_available'
            else:
                if markant_recompute_state:
                    continue
                else:
                    if move.procure_method == 'make_to_order' and not move.move_orig_ids:
                        move.state = 'waiting'
                    elif move.move_orig_ids and not all(orig.state in ('done', 'cancel') for orig in move.move_orig_ids):
                        move.state = 'waiting'
                    else:
                        move.state = 'confirmed'


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    article_description = fields.Text('Order Point', related='move_id.article_description', store=True)
    date_expected = fields.Datetime('Expected Date', related='move_id.date_expected', store=True)
    article_description_move = fields.Text('Invisible Order Point', related='move_id.article_description_move',
                                           store=True)
    article_description_basic = fields.Text('Basic Order Point', related='move_id.article_description_basic',
                                            store=True)
