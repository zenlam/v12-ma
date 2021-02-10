from odoo import api, fields, models, _
from odoo.exceptions import Warning


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    carrier_name_id = fields.Many2one('carrier', string="Carrier")
    partner_invoice_id = fields.Many2one('res.partner',
                                         string='Invoice Address',
                                         readonly=True,
                                         related='sale_id.partner_invoice_id',
                                         help="Invoice address for current "
                                              "sales order.")
    delivery_option = fields.Selection(
        [('full', 'Full'), ('partial', 'Partial')],
        string='Delivery Option', copy=False)
    payment_term_id = fields.Many2one('account.payment.term',
                                      related='sale_id.payment_term_id',
                                      string='Payment Terms')
    last_print_date = fields.Datetime(string="Last Print Date")
    no_of_print = fields.Integer(string="No. of Print")
    block_do = fields.Boolean(string="Block Delivery")
    contact_person_id = fields.Many2one('res.users',
                                        string='Markant Contact Person',
                                        default=lambda self: self.env.user)
    packaging_ids = fields.One2many('picking.packaging',
                                    'picking_id',
                                    string='Packaging')
    packaging_count = fields.Integer(string="Packaging Count",
                                     compute='_compute_packaging_count')
    so_commitment_date = fields.Datetime('SO Commitment Date')
    is_partner_readonly = fields.Boolean(
        'Is Partner Readonly?', related='picking_type_id.is_partner_readonly',
        readonly=True)
    is_commitment_date_match = fields.Boolean(
        'Is Commitment Date Matched?',
        related='picking_type_id.is_commitment_date_match',
        readonly=True)
    partner_id = fields.Many2one(track_visibility=True)

    @api.multi
    def get_picking_report_data(self):
        line_ids = []
        for picking in self:
            for move in picking.move_ids_without_package:
                for move_line in move.move_line_ids:
                    if picking.is_commitment_date_match:
                        if move_line.date_expected and \
                                picking.so_commitment_date and \
                                (move_line.date_expected.date() ==
                                 picking.so_commitment_date.date()):
                            line_ids += move_line
                    else:
                        line_ids += move_line
        return sorted(line_ids, key=lambda k: (k.article_description_basic, k.location_id.name))

    def _get_bom_components(self, bom, bom_quantity, product):
        components = [{
            product.id: [],
        }]
        for line in bom.bom_line_ids:
            line_quantity = (bom_quantity / (bom.product_qty or 1.0)) * line.product_qty
            if line._skip_bom_line(product):
                continue
            components[0][product.id].append((
                line.product_id.id, line.product_id.display_name,
                line_quantity))
        return components

    @api.multi
    def _compute_packaging_count(self):
        for record in self:
            self.packaging_count = self.env[
                'picking.packaging'].search_count(
                [('picking_id', '=', record.id)])

    @api.multi
    def action_view_packaging_picking(self):
        self.ensure_one()
        packaging_id = self.env[
            'picking.packaging'].search(
            [('picking_id', '=', self.id)])
        action = self.env.ref(
            'markant_stock.action_view_picking_packaging').read()[0]
        action['domain'] = [('id', 'in', packaging_id.ids)]
        return action

    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        if not self.env.context.get('from_so') and not self.env.context.get('skip_obsolete'):
            for picking in self:
                if picking.sale_id:
                    picking.sale_id.with_context(from_do=True).calculate_obsolete_qty_after()
        return res

    @api.multi
    def button_validate(self):
        self.ensure_one()

        # Condition only checked when transfer type is `outgoing`
        if self.picking_type_code == 'outgoing':
            partial_warning = False
            do_not_repeat_warning = []
            check_for_components = {}
            partial_warning_str = ''

            # Check if Done qty is set by user for any move or not
            check_for_done_full = [move.quantity_done == 0
                                   for move in self.move_lines
                                   if not move.allow_partial]

            check_for_done_partial = [move.quantity_done == 0
                                      for move in self.move_lines
                                      if move.allow_partial]

            for move in self.move_lines:
                bom = self.env['mrp.bom']._bom_find(
                    product_tmpl=None,
                    product=move.sale_line_id.product_id,
                    picking_type=None, company_id=False)

                bom_component_list = False
                if bom:
                    bom_component_list = self._get_bom_components(
                        bom, bom.product_qty,
                        move.sale_line_id.product_id)

                if not move.allow_partial:
                    # Case(s) for Full Delivery
                    warning_msg = _('You can not process current order!\n'
                                    'As some operation(s) marked as '
                                    'Full delivery option.\n'
                                    'So, You can process those '
                                    'operation(s) as soon as '
                                    'all quantities are available in stock.')

                    # WTF - Full Closure Function
                    def recursive_check_full(arg=''):
                        if arg == 'WTF':
                            if not move.product_uom_qty:
                                # Initial Demand is 0
                                raise Warning(warning_msg)
                            if not move.quantity_done:
                                # Done Qty is 0
                                if move.reserved_availability < \
                                        move.product_uom_qty:
                                    raise Warning(warning_msg)
                            else:
                                # Done Qty is not 0
                                if move.quantity_done < move.product_uom_qty:
                                    raise Warning(warning_msg)
                        else:
                            if not move.quantity_done:
                                # Done Qty is 0
                                if move.reserved_availability < \
                                        move.product_uom_qty:
                                    raise Warning(warning_msg)
                            else:
                                if move.quantity_done < move.product_uom_qty:
                                    raise Warning(warning_msg)

                    if False in check_for_done_full:
                        # Only check if Done qty is changed by User
                        # Further check with 2 Scenario as below...
                        recursive_check_full()
                    else:
                        # Yayy!!, We got the matched BoM with +ve qty in SO
                        if move.sale_line_id.product_uom_qty \
                                and bom_component_list and \
                                bom_component_list[0].get(
                                move.sale_line_id.product_id.id):
                            bom_components = bom_component_list[0].get(
                                move.sale_line_id.product_id.id)
                            for component in bom_components:
                                if component[0] == move.product_id.id:
                                    recursive_check_full('WTF')
                        else:
                            recursive_check_full()
                else:
                    # WTF - Partial Closure Function
                    def recursive_check_partial():
                        if move.sale_line_id.id not in \
                                do_not_repeat_warning:
                            warning_str = \
                                "You are trying to " \
                                "deliver " + \
                                move.sale_line_id. \
                                    product_id.name \
                                + " as a partial " \
                                  "delivery." \
                                  "\nAs it's components " \
                                  "done " \
                                  "quantity are not set " \
                                  "properly." \
                                  "\nFor " + str(
                                    bom.product_qty) + \
                                " quantity of " + \
                                move.sale_line_id. \
                                    product_id.name \
                                + " we need " + \
                                component_str + \
                                "\nSo, set the Done " \
                                "quantity as " \
                                "per above values.\n\n"
                            do_not_repeat_warning.append(
                                move.sale_line_id.id)
                            return warning_str
                        else:
                            return ''

                    # Case(s) for Partial Delivery
                    # ----------------------------

                    # We got the matched BoM with +ve qty in SO
                    if move.sale_line_id.product_uom_qty \
                            and bom_component_list and \
                            bom_component_list[0].get(
                            move.sale_line_id.product_id.id):
                        bom_components = bom_component_list[0].get(
                            move.sale_line_id.product_id.id)
                        for component in bom_components:
                            if component[0] == move.product_id.id:
                                if check_for_components.get(
                                        move.sale_line_id.id):
                                    check_for_components[
                                        move.sale_line_id.id].append(
                                        move.quantity_done /
                                        component[2])
                                else:
                                    check_for_components.update({
                                        move.sale_line_id.id: [
                                            move.quantity_done /
                                            component[2]]
                                    })

                                final_check_for_components = [
                                    len(set(v)) for (k, v) in
                                    check_for_components.items()]
                                final_check_for_partial_components = [
                                    {k: all(qty == 0 for qty in v)} for (
                                        k, v) in
                                    check_for_components.items()]
                                is_partial = [
                                    i[move.sale_line_id.id]
                                    for i in
                                    final_check_for_partial_components
                                    if move.sale_line_id.id in i]

                                if not is_partial[0]:
                                    # If user set the done qty then...
                                    if not move.quantity_done or \
                                        move.quantity_done % \
                                            component[2] != 0 or \
                                            not all(
                                                each_c == 1 for each_c in
                                                final_check_for_components
                                            ):
                                        component_str = ''
                                        for component1 in bom_components:
                                            component1 = list(component1)
                                            del component1[0]
                                            component_str += ''.join(
                                                str(component1))
                                        partial_warning = True
                                        partial_warning_str += \
                                            recursive_check_partial()
                                else:
                                    # If user didn't set the done qty then,
                                    if False not in \
                                            check_for_done_partial and (
                                            not move.product_uom_qty or
                                            not move.reserved_availability
                                            or move.reserved_availability
                                            % component[2] != 0):
                                        component_str = ''
                                        for component1 in bom_components:
                                            component1 = list(component1)
                                            del component1[0]
                                            component_str += ''.join(
                                                str(component1))
                                        partial_warning = True
                                        partial_warning_str += \
                                            recursive_check_partial()
                                    else:
                                        if move.reserved_availability % \
                                                component[2] != 0:
                                            component_str = ''
                                            for component1 in bom_components:
                                                component1 = list(component1)
                                                del component1[0]
                                                component_str += ''.join(
                                                    str(component1))
                                            partial_warning = True
                                            partial_warning_str += \
                                                recursive_check_partial()
                    # No BoM, then nothing to check...
                    else:
                        pass

            if partial_warning:
                raise Warning(_(partial_warning_str))

            if self.block_do:
                raise Warning(_("This Delivery is blocked from the "
                                "Sales Order"))
        return super(StockPicking, self).button_validate()

    @api.multi
    def action_done(self):
        res = super(StockPicking, self).action_done()
        auto_assign = False
        prod_ids = []
        for record in self:
            if record.picking_type_id.trigger_auto_reserve:
                for prod in record.move_ids_without_package:
                    prod_ids.append(prod.product_id.id)
                auto_assign = True
        if auto_assign:
            sql = '''
                    SELECT sp.id
                    FROM
                        stock_move sm
                    LEFT JOIN stock_picking sp ON sm.picking_id = sp.id
                    WHERE sm.product_id IN %s
                    AND sp.state NOT IN ('draft', 'done', 'cancel')
                    '''
            self._cr.execute(sql, (tuple(prod_ids),))
            picking_ids = []
            for picking in self.env.cr.dictfetchall():
                picking_ids.append(picking.get('id'))
            all_picking = self.env['stock.picking'].search([
                ('id', 'in', picking_ids)],
                order='create_date')
            if all_picking:
                all_picking.action_assign()
        return res

    @api.multi
    def _create_backorder(self, backorder_moves=[]):
        """ Move all non-done lines into a new backorder picking.
        """
        backorders = self.env['stock.picking']
        for picking in self:
            moves_to_backorder = picking.move_lines.filtered(lambda x: x.state not in ('done', 'cancel'))
            # MARKANT: Need to update the article description inside the backorder
            sale_line_id_moves = {}
            sale_line_id_moves_ad = {}
            for move in moves_to_backorder:
                if move.sale_line_id not in sale_line_id_moves:
                    sale_line_id_moves.update({
                        move.sale_line_id: [move]
                    })
                    sale_line_id_moves_ad.update({
                        move.sale_line_id: [move.article_description]
                    })
                else:
                    sale_line_id_moves[move.sale_line_id].append(move)
                    sale_line_id_moves_ad[move.sale_line_id].append(move.article_description)
            for key, val in sale_line_id_moves_ad.items():
                if all(not ad for ad in val):
                    article_description_new = key.move_ids.filtered(lambda x: x.article_description)
                    if len(article_description_new) > 1:
                        article_description_new = article_description_new[0]
                    sale_line_id_moves[key][0].article_description = article_description_new.article_description
                    sale_line_id_moves[key][0].article_description_move = article_description_new.article_description

            # MARKANT: End of customization.
            if moves_to_backorder:
                backorder_picking = picking.copy({
                    'name': '/',
                    'move_lines': [],
                    'move_line_ids': [],
                    'backorder_id': picking.id,
                    'delivery_option': picking.delivery_option
                })
                picking.message_post(
                    body=_(
                        'The backorder <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> has been created.') % (
                             backorder_picking.id, backorder_picking.name))
                moves_to_backorder.write({'picking_id': backorder_picking.id})
                moves_to_backorder.mapped('package_level_id').write({'picking_id': backorder_picking.id})
                moves_to_backorder.mapped('move_line_ids').write({'picking_id': backorder_picking.id})
                backorder_picking.action_assign()
                # Automate changing of commitment date when backorder is created.
                # Always take the earliest date
                for backorder in backorder_picking:
                    if backorder.picking_type_id.is_commitment_date_match:
                        new_moves_to_backorder = backorder.move_lines.filtered(
                            lambda x: x.state not in ('done', 'cancel'))
                        exp_date = False
                        print('original exp date', exp_date)
                        for move in new_moves_to_backorder:
                            if not exp_date:
                                exp_date = move.date_expected
                            else:
                                if move.date_expected < exp_date:
                                    exp_date = move.date_expected
                        print('exp_date', exp_date)
                        sale_order = self.env['sale.order'].search(
                            [('id', '=', backorder.sale_id.id)])
                        if sale_order:
                            sale_order.write({
                                'commitment_date': exp_date
                            })
                backorders |= backorder_picking
        return backorders


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    is_delivery_order = fields.Boolean('Is This Delivery Order?')
    is_partner_readonly = fields.Boolean('Is Partner Readonly?')
    is_commitment_date_match = fields.Boolean('Is Commitment Date Matched?')
    trigger_auto_reserve = fields.Boolean('Trigger Auto Reserve',
                                          help='When picking is validated, '
                                               'auto reservation will happen '
                                               'for all picking in waiting stage!')
