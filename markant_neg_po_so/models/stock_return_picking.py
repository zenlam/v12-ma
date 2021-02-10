from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round, float_compare
from datetime import datetime


class ReturnPickingLine(models.TransientModel):
    _inherit = 'stock.return.picking.line'

    to_create_neg = fields.Boolean('To Create Negative SO/PO',
                                   readonly=False)
    to_refund = fields.Boolean('To Refund(update SO/PO)',
                               help='Trigger a decrease of the delivered/'
                                    'received quantity in the associated '
                                    'Sale Order/Purchase Order',
                               related='to_create_neg', readonly=False)

    @api.onchange('to_refund')
    def onchange_to_create_neg(self):
        self.to_create_neg = self.to_refund


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    to_hide_column = fields.Boolean('Hide Create Negative PO')

    @api.model
    def default_get(self, fields):
        """
        Override default_get to auto filled To Create Negative PO/SO check box
        if the wizard is opening from a incoming picking
        """
        if len(self.env.context.get('active_ids', list())) > 1:
            raise UserError(_("You may only return one picking at a time."))
        res = super(ReturnPicking, self).default_get(fields)

        move_dest_exists = False
        product_return_moves = []
        is_po_so = True
        to_hide_column = False
        picking = self.env['stock.picking'].browse(
            self.env.context.get('active_id'))
        if picking:
            res.update({'picking_id': picking.id})
            if picking.state != 'done':
                raise UserError(_("You may only return Done pickings."))
            if picking.picking_type_code not in ('incoming', 'outgoing'):
                is_po_so = False
                to_hide_column = True
                res.update({'to_hide_column': to_hide_column})
            for move in picking.move_lines:
                if move.state == 'cancel':
                    continue
                if move.scrapped:
                    continue
                if move.move_dest_ids:
                    move_dest_exists = True
                quantity = move.product_qty - sum(move.move_dest_ids.filtered(
                    lambda m: m.state in ['partially_available', 'assigned',
                                          'done']). \
                                                  mapped(
                    'move_line_ids').mapped('product_qty'))
                quantity = float_round(quantity,
                                       precision_rounding=move.product_uom.rounding)
                product_return_moves.append((0, 0,
                                             {'product_id': move.product_id.id,
                                              'quantity': quantity,
                                              'move_id': move.id,
                                              'uom_id': move.product_id.uom_id.id,
                                              'to_refund': is_po_so,
                                              'to_create_neg': is_po_so}))

            if not product_return_moves:
                raise UserError(_(
                    "No products to return (only lines in Done state and not fully returned yet can be returned)."))
            if 'product_return_moves' in fields:
                res.update({'product_return_moves': product_return_moves})
            if 'move_dest_exists' in fields:
                res.update({'move_dest_exists': move_dest_exists})
            if 'parent_location_id' in fields and picking.location_id.usage == 'internal':
                res.update({
                    'parent_location_id': picking.picking_type_id.warehouse_id and picking.picking_type_id.warehouse_id.view_location_id.id or picking.location_id.location_id.id})
            if 'original_location_id' in fields:
                res.update({'original_location_id': picking.location_id.id})
            if 'location_id' in fields:
                location_id = picking.location_id.id
                if picking.picking_type_id.return_picking_type_id.default_location_dest_id.return_location:
                    location_id = picking.picking_type_id.return_picking_type_id.default_location_dest_id.id
                res['location_id'] = location_id
        return res

    def create_returns(self):
        """
        Inherit this function to create negative PO/SO when return button is
        clicked on the return wizard
        """
        have_neg_po = self.env['purchase.order'].search_count(
            [('origin_picking', '=', self.picking_id.id)])
        have_neg_so = self.env['sale.order'].search_count(
            [('origin_picking', '=', self.picking_id.id)])
        if have_neg_po or have_neg_so:
            raise UserError(_(
                "You are trying to create a return on a return that created a "
                "negative SO/PO. \n\n Instead, please create a Normal SO/PO"))
        for wizard in self:
            new_picking_id, pick_type_id = wizard._create_returns()
            new_picking = self.env['stock.picking'].browse(new_picking_id)
            if not self.to_hide_column:
                if any(
                        return_line.to_create_neg == True
                        and return_line.quantity > 0
                        for return_line in self.product_return_moves):
                    """
                    Only incoming and outgoing picking
                    Dropship picking will have both sale_id and purchase id 
                    but the picking is in po, so we crete a neg po
                    """
                    if new_picking.purchase_id:
                        self.create_neg_po(new_picking)
                    elif new_picking.sale_id:
                        self.create_neg_so(new_picking)

        # Override the context to disable all the potential filters that could have been set previously
        ctx = dict(self.env.context)
        ctx.update({
            'search_default_picking_type_id': pick_type_id,
            'search_default_draft': False,
            'search_default_assigned': False,
            'search_default_confirmed': False,
            'search_default_ready': False,
            'search_default_late': False,
            'search_default_available': False,
        })
        return {
            'name': _('Returned Picking'),
            'view_type': 'form',
            'view_mode': 'form,tree,calendar',
            'res_model': 'stock.picking',
            'res_id': new_picking_id,
            'type': 'ir.actions.act_window',
            'context': ctx,
        }

    @api.multi
    def _prepare_po_order_line_vals(self, po):
        for return_line in self.product_return_moves:
            if return_line.quantity and return_line.to_create_neg:
                line_vals = {
                    'product_id': return_line.product_id.id,
                    'product_qty': -return_line.quantity,
                    'product_uom': return_line.uom_id.id,
                    'order_id': po.id,
                    'qty_received': -return_line.quantity,
                    'confirmation_date': datetime.now()
                }
                return_line.move_id.purchase_line_id.copy(line_vals)

    @api.multi
    def _prepare_so_order_line_vals(self, so):
        for return_line in self.product_return_moves:
            if return_line.quantity and return_line.to_create_neg:
                line_vals = {
                    'product_id': return_line.product_id.id,
                    'product_uom_qty': -return_line.quantity,
                    'product_uom': return_line.uom_id.id,
                    'order_id': so.id,
                }
                return_line.move_id.sale_line_id.copy(line_vals)

    @api.multi
    def create_neg_po(self, new_picking):
        neg_po = new_picking.purchase_id.copy({
            'order_line': [],
            'is_neg_po': True,
            'date_order': datetime.now(),
            'origin_picking': new_picking.id,
            'origin_po': new_picking.purchase_id.id,
            'origin': new_picking.name,
            'state': 'purchase',
            'picking_type_id': new_picking.picking_type_id.id,
            'invoice_status': 'no',
            'date_planned': datetime.now(),
            'date_approve': datetime.now(),
        })
        self._prepare_po_order_line_vals(neg_po)

    @api.multi
    def create_neg_so(self, new_picking):
        neg_so = new_picking.sale_id.copy({
            'order_line': [],
            'is_neg_so': True,
            'date_order': datetime.now(),
            'origin_picking': new_picking.id,
            'origin_so': new_picking.sale_id.id,
            'origin': new_picking.name,
            'state': 'sale',
            'confirmation_date': datetime.now(),
            'is_min_admin_cost_rule': False,
            'is_montage_install_rule': False,
            'is_project_discount': False,
            'inst_installation_type_id': False,
            'inst_require_initial_so': False,
        })
        self._prepare_so_order_line_vals(neg_so)
