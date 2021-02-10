from odoo import api, fields, models, _
from odoo.exceptions import UserError
from lxml import etree
from openerp.osv.orm import setup_modifiers


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_neg_po = fields.Boolean('Is Negative PO?', default=False,
                               readonly=True)
    follow_up = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], default='open', string='Follow Up')
    origin_picking = fields.Many2one('stock.picking', 'Origin Picking',
                                     readonly=True)
    origin_po = fields.Many2one('purchase.order', 'Origin PO', readonly=True)

    neg_po_count = fields.Integer(string="Negative PO Count",
                                  compute="_compute_neg_po")

    @api.model
    def create(self, vals):
        if vals.get('is_neg_po', False):
            vals['name'] = self.env['ir.sequence'].next_by_code('neg.po')
        res = super(PurchaseOrder, self).create(vals)
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                        submenu=False):
        """
        No Create for Negative PO
        """
        result = super(PurchaseOrder, self).fields_view_get(view_id=view_id,
                                                            view_type=view_type,
                                                            toolbar=toolbar,
                                                            submenu=submenu)

        if self.env.context.get('no_create', False):
            doc = etree.XML(result['arch'])
            for node in doc.xpath("//tree"):
                node.set('create', 'false')
                setup_modifiers(node)
            for node in doc.xpath("//form"):
                node.set('create', 'false')
                setup_modifiers(node)
            result['arch'] = etree.tostring(doc)
        return result

    @api.multi
    def _compute_neg_po(self):
        for record in self:
            self.neg_po_count = self.env['purchase.order'].search_count(
                [('origin_po', '=', self.id)])

    @api.multi
    def action_view_neg_po(self):
        self.ensure_one()
        action = self.env.ref(
            'markant_neg_po_so.negative_purchase_form_action').read()[0]
        action['domain'] = [('origin_po', '=', self.id)]
        return action

    @api.depends('state', 'order_line.qty_invoiced', 'order_line.qty_received',
                 'order_line.product_qty')
    def _get_invoiced(self):
        """
        Inherit compute function to manually set invoice_status field
        """
        super(PurchaseOrder, self)._get_invoiced()
        for order in self:
            if order.is_neg_po == True:
                order.update({
                    'invoice_status': 'no'
                })

    @api.multi
    def button_cancel(self):
        """
        Inherit cancel button, to cancel the origin picking when this negative
        PO is cancelled. But not allow to cancel this negative PO if the
        origin picking is validated.
        """
        for order in self:
            if order.is_neg_po:
                if order.origin_picking.state == 'done':
                    raise UserError(_(
                        "You are not allow to cancel this Negative PO "
                        "because the origin picking is validated."))
                elif order.origin_picking.state != 'cancel':
                    order.origin_picking.action_cancel()
        return super(PurchaseOrder, self).button_cancel()


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.multi
    def _create_or_update_picking(self):
        """
        Inherit this function to not create picking for Negative PO
        """
        for line in self:
            if line.order_id.is_neg_po:
                return
            else:
                super(PurchaseOrderLine, self)._create_or_update_picking()

    @api.multi
    def write(self, vals):
        """
        Validate the order line of Negative PO must be negative quantity
        """
        for record in self:
            if record.order_id.is_neg_po:
                if vals.get('product_qty', 0) > 0:
                    raise UserError(_(
                        "The order lines quantity must be Negative for Negative PO."))

        return super(PurchaseOrderLine, self).write(vals)
