# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning
from odoo.tools import formatLang
from dateutil.relativedelta import relativedelta


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    rfq_number = fields.Integer(compute='_compute_rfq_amount_total',
                                string="Number of rfq")
    purchase_order_number = fields.Integer(compute='_compute_po_amount_total',
                                           string="Number of purchase order")
    purchase_order_ids = fields.Many2many('purchase.order',
                                          'purchase_order_crm_lead_rel',
                                          'lead_id', 'order_id',
                                          string='PO Id')

    def _compute_rfq_amount_total(self):
        self.ensure_one()
        rfq_lead = self.purchase_order_ids.filtered\
            (lambda x: x.state in ('draft', 'sent', 'to approve'))
        self.rfq_number = len(rfq_lead)

    def _compute_po_amount_total(self):
        self.ensure_one()
        po_lead = self.purchase_order_ids.filtered\
            (lambda x: x.state in ('purchase', 'done'))
        self.purchase_order_number = len(po_lead)

    @api.multi
    def show_rfq_list(self):
        self.ensure_one()
        views = [(self.env.ref('purchase.purchase_order_tree').id, 'tree'),
                 (self.env.ref('purchase.purchase_order_form').id, 'form')]

        return {
            'name': _('RFQ'),
            'domain': [('id', 'in', self.purchase_order_ids.ids),
                       ('state', 'in', ['draft', 'sent', 'to approve'])],
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'views': views,
            'view_id': False,
            'context': {'default_opportunity_ids': self.ids},
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def show_purchase_order_list(self):
        self.ensure_one()
        views = [(self.env.ref('purchase.purchase_order_tree').id, 'tree'),
                 (self.env.ref('purchase.purchase_order_form').id, 'form')]

        return {
            'name': _('Purchase Order'),
            'domain': [('id', 'in', self.purchase_order_ids.ids),
                       ('state', 'in', ['purchase', 'done'])],
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'views': views,
            'view_id': False,
            'context': {'default_opportunity_ids': self.ids},
            'type': 'ir.actions.act_window',
        }


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    user_id = fields.Many2one(domain=lambda self: [
        ('groups_id', 'in',
         [self.env.ref('purchase.group_purchase_user').id,
          self.env.ref('purchase.group_purchase_manager').id])
    ])

    # Incoterm : when partner changed we need to change this.
    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        res = super(PurchaseOrder, self).onchange_partner_id()
        self.user_id = self.partner_id.purchase_user_id.id or self.env.uid
        if self.partner_id and self.partner_id.incoterm_id:
            self.incoterm_id = self.partner_id.incoterm_id.id
        elif self.partner_id and self.partner_id.parent_id:
            if self.partner_id.parent_id.incoterm_id:
                self.incoterm_id = self.partner_id.parent_id.incoterm_id.id
            else:
                self.incoterm_id = False
        else:
            self.incoterm_id = False
        return res       

    @api.depends('origin')
    def get_source_link(self):
        if self.origin:
            link = []
            origins = self.origin.split(',')
            for ori in origins:
                ori = ori.strip()
                sale_order_id = self.env['sale.order'].search([('name', '=', ori)])
                if sale_order_id:
                    link.append('<a href=web#id=%s&action=%s&model=%s&view_type=form>%s</a>' %
                                (sale_order_id.id, self.env.ref('sale.action_orders').id, sale_order_id._name, ori))
                mrp_production_id = self.env['mrp.production'].search([('name', '=', ori)])
                if mrp_production_id:
                    link.append('<a href=web#id=%s&action=%s&model=%s&view_type=form>%s</a>' %
                                (mrp_production_id.id, self.env.ref('mrp.mrp_production_action').id,
                                 mrp_production_id._name, ori))
                picking_id = self.env['stock.picking'].search([('name', '=', ori)])
                if picking_id:
                    link.append('<a href=web#id=%s&action=%s&model=%s&view_type=form>%s</a>' %
                                (picking_id.id, self.env.ref('stock.stock_picking_action_picking_type').id,
                                 picking_id._name, ori))
                warehouse_orderpoint_id = self.env['stock.warehouse.orderpoint'].search([('name', '=', ori)])
                if warehouse_orderpoint_id:
                    link.append('<a href=web#id=%s&action=%s&model=%s&view_type=form>%s</a>' %
                                (warehouse_orderpoint_id.id, self.env.ref('stock.action_orderpoint_form').id,
                                 warehouse_orderpoint_id._name, ori))
            self.origin_link = ', '.join(link)

    @api.model
    def get_default_note(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'markant_purchase.use_purchase_note') and self.env.user.company_id.purchase_note or ''

	# Order Cycle
    purchase_order_cycle_id = fields.Many2one('order.cycle', string="Order Cycle", default=lambda self: self.env["order.cycle"].sudo().search([('is_default', '=', True)], order='id') and self.env["order.cycle"].sudo().search([('is_default', '=', True)], order='id').id or False)
    apply_order_cycle = fields.Boolean(default=lambda self: self.env["ir.sequence"].sudo().search([('code', '=', 'purchase.order')], order='id') and self.env["ir.sequence"].sudo().search([('code', '=', 'purchase.order')], order='id')[0].apply_order_cycle or False)
    purchase_order_cycle_prefix = fields.Char()
    origin_link = fields.Html(string='Source Document', readonly=True, compute=get_source_link)
    opportunity_count = fields.Integer("Opportunity",
                                       compute='_compute_opportunity_count')
    opportunity_ids = fields.Many2many('crm.lead', 'purchase_order_crm_lead_rel',
                                       'order_id', 'lead_id',
                                       string='Opportunity')
    terms_note = fields.Html('Terms and conditions', default=get_default_note)

    @api.multi
    def _compute_opportunity_count(self):
        self.ensure_one()
        self.opportunity_count = len(self.opportunity_ids)

    @api.onchange('purchase_order_cycle_id')
    def onchange_purchase_order_cycle(self):
        if self.name != _('New'):
            record_name = self.name
            if self.purchase_order_cycle_id:
                cycle_name = self.purchase_order_cycle_id.name + "/"
                to_process = True
                if self.purchase_order_cycle_prefix:
                    if cycle_name != self.purchase_order_cycle_prefix:
                        record_name = record_name.replace(self.purchase_order_cycle_prefix, cycle_name, 1)
                        self.name = record_name
                        self.purchase_order_cycle_prefix = cycle_name
                        to_process = False
                if to_process:
                    record_name = record_name
                    if cycle_name not in record_name:
                        record_name = cycle_name + record_name
                        self.name = record_name
                        self.purchase_order_cycle_prefix = cycle_name
            elif self.purchase_order_cycle_prefix:
                if self.purchase_order_cycle_prefix in record_name:
                    record_name = record_name.replace(self.purchase_order_cycle_prefix, "", 1)
                    self.name = record_name
                    self.purchase_order_cycle_prefix = ""

    @api.model
    def create(self, vals):
        res = super(PurchaseOrder, self).create(vals)
        if res.apply_order_cycle and res.purchase_order_cycle_id:
            cycle_name = res.purchase_order_cycle_id.name + "/"
            if cycle_name not in res.name:
                resp = res.with_context(only_name_write_again=True).write({'name': cycle_name + res.name, 'purchase_order_cycle_prefix': cycle_name})
        return res

    @api.multi
    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        if self.env.context.get("only_name_write_again") is not None:
            return res
        for record in self:
            record_name = record.name
            if self.purchase_order_cycle_id:
                cycle_name = self.purchase_order_cycle_id.name + "/"
                to_process = True
                if self.purchase_order_cycle_prefix:
                    if cycle_name != self.purchase_order_cycle_prefix:
                        record_name = record_name.replace(self.purchase_order_cycle_prefix, cycle_name, 1)
                        resp = record.with_context(only_name_write_again=True).write({'name': record_name , 'purchase_order_cycle_prefix': cycle_name})
                        to_process = False
                if to_process:
                    if cycle_name not in record_name:
                        record_name = cycle_name + record_name
                        resp = record.with_context(only_name_write_again=True).write({'name': record_name, 'purchase_order_cycle_prefix':cycle_name})
            elif self.purchase_order_cycle_prefix:
                if self.purchase_order_cycle_prefix in record_name:
                    record_name = record_name.replace(self.purchase_order_cycle_prefix, "", 1)
                    resp = record.with_context(only_name_write_again=True).write({'name': record_name, 'purchase_order_cycle_prefix': ""})
        return res

    @api.multi
    def show_purchase_lead_opportunities(self):
        self.ensure_one()
        views = [(self.env.ref('crm.crm_case_tree_view_oppor').id, 'tree'),
                 (self.env.ref('crm.crm_case_form_view_oppor').id, 'form')]
        return {
            'name': _('Opportunities'),
            'domain': [('id', 'in', self.opportunity_ids.ids)],
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'crm.lead',
            'views': views,
            'view_id': False,
            'type': 'ir.actions.act_window',
        }

    # Pre-Payment related code
    need_prepayment = fields.Boolean(string="Need Pre-Payment")
    hide_confirm_button = fields.Boolean(compute='_compute_hide_confirm_button')

    @api.depends('need_prepayment')
    def _compute_hide_confirm_button(self):
        manager_group = self.user_has_groups('markant_purchase.group_markant_purchase_pre_payment_manager')
        for order in self:
            if not manager_group and order.need_prepayment:
                order.hide_confirm_button = True
            else:
                order.hide_confirm_button = False

    def _run_prepayment_po(self):
        user_ids = []
        for user in self.env['res.users'].search([('groups_id' ,'=' ,self.env.ref('markant_purchase.group_markant_purchase_pre_payment_manager').id)]):
            user_ids.append(user.partner_id.id)
        rece_str = ','.join(str(e) for e in user_ids)

        po_list = []
        for po in self.search([('state' ,'in' ,['draft', 'sent']), ('need_prepayment', '=', True)]):
            po_list.append(po)

        if po_list:
            template = self.env.ref('markant_purchase.email_template_po_need_prepayment_markant_purchase', False)
            template.write({'partner_to': rece_str})
            template.with_context(orders=po_list).send_mail(po.id, force_send=True)

    @api.multi
    def action_view_invoice(self):
        res = super(PurchaseOrder, self).action_view_invoice()
        # Remove the reference value when create Bill
        res['context']['default_reference'] = False
        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    confirmation_date = fields.Datetime(string="Confirmation Date")
    ex_works_date = fields.Datetime(string="Ex-works Date")

    # change the string of the field
    date_planned = fields.Datetime(string="Schedule Delivery Date")
    product_vendor_code = fields.Char(string="Vendor Code",
                                      compute="_compute_vendor_code")
    goods_available_date = fields.Datetime(string="Goods Available Date")

    @api.depends('product_id', 'product_qty', 'product_uom')
    def _compute_vendor_code(self):
        for line in self:
            if line.product_id:
                params = {'order_id': line.order_id}
                seller = line.product_id._select_seller(
                    partner_id=line.partner_id,
                    quantity=line.product_qty,
                    date=line.order_id.date_order and line.order_id.date_order.date(),
                    uom_id=line.product_uom,
                    params=params)

                if seller and seller.product_code:
                    line.product_vendor_code = seller.product_code
                else:
                    line.product_vendor_code = False

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        res = super(PurchaseOrderLine, self)._onchange_quantity()
        # if self.date_planned and not self.confirmation_date:
        self.with_context(no_need_confirmation_onchange=True).confirmation_date = self.date_planned

    @api.onchange('confirmation_date')
    def _onchange_confirmation_date(self):
        if self.env.context.get('no_need_confirmation_onchange') is None:
            self.date_planned = self.confirmation_date

    @api.onchange('date_planned')
    def _onchange_planned_date(self):
        if self.date_planned:
            self.goods_available_date = self.date_planned + \
                                        relativedelta(days=+3)

    @api.multi
    def write(self, vals):
        res = super(PurchaseOrderLine, self).write(vals)
        if vals.get('date_planned') is not None:
            for record in self:
                if record.order_id.state not in ['done', 'cancel']:
                    for move in record.move_ids:
                        if move.state not in ['done', 'cancel']:
                            write_done = move.write({'date_expected': record.date_planned})
        return res

    is_qty_remain_receive = fields.Boolean(compute='_compute_is_qty_remain_receive', store=True)

    @api.depends('qty_received','product_qty')
    def _compute_is_qty_remain_receive(self):
        for line in self:
            if line.qty_received < line.product_qty:
                line.is_qty_remain_receive = True


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    purchase_id_stored = fields.Many2one('purchase.order', compute='_compute_purchase_id_stored', store=True)
    
    @api.depends('move_lines')
    def _compute_purchase_id_stored(self):
        for picking in self:
            if picking.purchase_id:
                picking.purchase_id_stored = picking.purchase_id.id
            else:
                picking.purchase_id_stored = False


class PurchaseBillUnion(models.Model):
    _inherit = 'purchase.bill.union'


    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100,
                     name_get_uid=None):
        args.append(['purchase_order_id', '!=', False])
        records = self.search(args)
        valid_purchase_ids = []
        if records:
            for pbu in records:
                for line in pbu.purchase_order_id.order_line:
                    if line.product_id.type in ('consu', 'product'):
                        if line.qty_invoiced < line.qty_received:
                            valid_purchase_ids.append(pbu.id)
                            continue
                    elif line.product_id.type == 'service':
                        if line.qty_invoiced < line.product_qty:
                            valid_purchase_ids.append(pbu.id)
                            continue
            valid_purchase_ids = list(set(valid_purchase_ids))
            args.append(['id', 'in', valid_purchase_ids])
        res = super(PurchaseBillUnion, self)._name_search(
            name=name, args=args, operator=operator,
            limit=limit, name_get_uid=name_get_uid)
        return res


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    # Load all unsold PO lines
    @api.onchange('purchase_id')
    def purchase_order_change(self):
        if not self.purchase_id:
            return {}
        if not self.partner_id:
            self.partner_id = self.purchase_id.partner_id.id

        vendor_ref = self.purchase_id.partner_ref
        if vendor_ref and (not self.reference or (
                vendor_ref + ", " not in self.reference and not self.reference.endswith(vendor_ref))):
            self.reference = ", ".join([self.reference, vendor_ref]) if self.reference else vendor_ref

        if not self.invoice_line_ids:
            #as there's no invoice line yet, we keep the currency of the PO
            self.currency_id = self.purchase_id.currency_id

        new_lines = self.env['account.invoice.line']
        for line in self.purchase_id.order_line - self.invoice_line_ids.mapped('purchase_line_id'):
            if line.product_id.type in ('consu', 'product'):
                if line.qty_invoiced == line.qty_received:
                    continue
            elif line.product_id.type == 'service':
                if line.qty_invoiced == line.product_qty:
                    continue
            data = self._prepare_invoice_line_from_po_line(line)
            new_line = new_lines.new(data)
            new_line._set_additional_fields(self)
            new_lines += new_line

        self.invoice_line_ids += new_lines
        self.payment_term_id = self.purchase_id.payment_term_id
        self.env.context = dict(self.env.context, from_purchase_order_change=True)
        self.purchase_id = False
        self.reference = False
        return {}
