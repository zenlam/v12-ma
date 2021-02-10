from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends('so_po_ref')
    def get_source_link(self):
        for move in self:
            if move.so_po_ref:
                link = []
                origins = move.so_po_ref.split(',')
                for ori in origins:
                    ori = ori.strip()
                    sale_order_id = self.env['sale.order'].search([('name', '=', ori)])
                    if sale_order_id:
                        link.append('<a href=web#id=%s&action=%s&model=%s&view_type=form>%s</a>' %
                                    (sale_order_id.id, self.env.ref('sale.action_orders').id, sale_order_id._name, ori))
                    purchase_order_id = self.env['purchase.order'].search([('name', '=', ori)])
                    if purchase_order_id:
                        link.append('<a href=web#id=%s&action=%s&model=%s&view_type=form>%s</a>' %
                                    (purchase_order_id.id, self.env.ref('purchase.purchase_form_action').id,
                                     purchase_order_id._name, ori))
                move.so_po_ref_link = ', '.join(link)

    so_po_ref = fields.Char('SO/PO')
    so_po_ref_link = fields.Html(string='SO/PO Link', readonly=True, compute=get_source_link)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends('so_po_ref')
    def get_source_link(self):
        for move in self:
            if move.so_po_ref:
                link = []
                origins = move.so_po_ref.split(',')
                for ori in origins:
                    ori = ori.strip()
                    sale_order_id = self.env['sale.order'].search([('name', '=', ori)])
                    if sale_order_id:
                        link.append('<a href=web#id=%s&action=%s&model=%s&view_type=form>%s</a>' %
                                    (sale_order_id.id, self.env.ref('sale.action_orders').id, sale_order_id._name, ori))
                    purchase_order_id = self.env['purchase.order'].search([('name', '=', ori)])
                    if purchase_order_id:
                        link.append('<a href=web#id=%s&action=%s&model=%s&view_type=form>%s</a>' %
                                    (purchase_order_id.id, self.env.ref('purchase.purchase_form_action').id,
                                     purchase_order_id._name, ori))
                move.so_po_ref_link = ', '.join(link)

    @api.depends('move_id.line_ids', 'move_id.line_ids.tax_line_id', 'move_id.line_ids.debit',
                 'move_id.line_ids.credit')
    def _compute_tax_base_amount(self):
        res = super(AccountMoveLine, self)._compute_tax_base_amount()
        for move_line in self:
            if move_line.move_id:
                if move_line.invoice_id.type == 'in_refund':
                    move_line.neg_tax_base_amount = move_line.tax_base_amount * -1
                else:
                    move_line.neg_tax_base_amount = move_line.tax_base_amount
        return res

    so_po_ref = fields.Char('SO/PO')
    so_po_ref_link = fields.Html(string='SO/PO Link', readonly=True, compute=get_source_link)
    neg_tax_base_amount = fields.Monetary(string="Base Amount", compute='_compute_tax_base_amount',
                                          currency_field='company_currency_id', store=True)
