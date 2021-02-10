from odoo import api, fields, models, _
from datetime import datetime
from lxml import etree
from openerp.osv.orm import setup_modifiers
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_neg_so = fields.Boolean('Is Negative SO?', default=False,
                               readonly=True)
    follow_up = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], default='open', string='Follow Up')
    origin_picking = fields.Many2one('stock.picking', 'Origin Picking',
                                     readonly=True)
    origin_so = fields.Many2one('sale.order', 'Origin SO', readonly=True)

    neg_so_count = fields.Integer(string="Negative SO Count",
                                  compute="_compute_neg_so")

    @api.multi
    def _compute_neg_so(self):
        for record in self:
            self.neg_so_count = self.env['sale.order'].search_count(
                [('origin_so', '=', self.id)])

    @api.multi
    def action_view_neg_so(self):
        self.ensure_one()
        action = self.env.ref(
            'markant_neg_po_so.negative_sale_form_action').read()[0]
        action['domain'] = [('origin_so', '=', self.id)]
        return action

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                        submenu=False):
        """
        No Create for Negative SO
        """
        result = super(SaleOrder, self).fields_view_get(view_id=view_id,
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

    @api.model
    def create(self, vals):
        if vals.get('is_neg_so', False):
            vals['name'] = self.env['ir.sequence'].next_by_code('neg.so')
        res = super(SaleOrder, self).create(vals)
        return res

    @api.depends('state', 'order_line.invoice_status',
                 'order_line.invoice_lines')
    def _get_invoiced(self):
        """
        Inherit compute function to manually set invoice_status field
        """
        super(SaleOrder, self)._get_invoiced()
        for order in self:
            if order.is_neg_so == True:
                order.update({
                    'invoice_status': 'no'
                })

    @api.multi
    def action_cancel(self):
        """
        Inherit cancel button, to cancel the origin picking when this negative
        SO is cancelled. But not allow to cancel this negative SO if the
        origin picking is validated.
        """
        for order in self:
            if order.is_neg_so:
                if order.origin_picking.state == 'done':
                    raise UserError(_(
                        "You are not allow to cancel this Negative SO "
                        "because the origin picking is validated."))
                elif order.origin_picking.state != 'cancel':
                    order.origin_picking.action_cancel()
        return super(SaleOrder, self).action_cancel()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def write(self, vals):
        for record in self:
            if record.order_id.is_neg_so:
                if vals.get('product_uom_qty', 0) > 0:
                    raise UserError(_(
                        "The order lines quantity must be Negative for Negative SO."))

        return super(SaleOrderLine, self).write(vals)
