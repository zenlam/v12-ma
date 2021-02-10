from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    cn_count = fields.Integer(compute="_compute_credit_note_count")
    is_import = fields.Boolean(string="Is import")
    backdated_post = fields.Boolean()
    backdated_date = fields.Date()
    interim_account_id = fields.Many2one('account.account', string="Interim Account")
    backdate_move_id = fields.Many2one('account.move', string="Backdated Move", copy=False)
    je_count = fields.Integer(compute="_compute_journal_entries_count")
    contact_person_id = fields.Many2one('res.users',
                                        string='Markant Contact Person',
                                        default=lambda self: self.env.user)
    partner_invoice_id = fields.Many2one('res.partner',
                                         string='Invoice Address',
                                         readonly=True,
                                         help="Invoice address for populated from "
                                              "sales order.")
    neg_amount_untaxed = fields.Monetary(string='Tax Excluded',
                                     store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    neg_amount_tax = fields.Monetary(string='Tax', store=True, readonly=True, compute='_compute_amount')

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding',
                 'currency_id', 'company_id', 'date_invoice', 'type')
    def _compute_amount(self):
        res = super(AccountInvoice, self)._compute_amount()
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.neg_amount_untaxed = self.amount_untaxed * sign
        self.neg_amount_tax = self.amount_tax * sign
        return res


    def _get_invoice_term(self):
        """
        Get record for cron job to run
        """
        return self.env['customer.invoice.term'].search([('active', '=', True)], limit=1)

    def _get_vendor_bill_term(self):
        """
        Get record for cron job to run
        """
        return self.env['vendor.bill.term'].search([('active', '=', True)], limit=1)

    @api.multi
    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        print('user_id ------------------->', self.user_id, self.user_id.email)
        self.ensure_one()
        template = self.env.ref('account.email_template_edi_invoice', False)
        compose_form = self.env.ref('account.account_invoice_send_wizard_form', False)
        # have model_description in template language
        lang = self.env.context.get('lang')
        if template and template.lang:
            lang = template._render_template(template.lang, 'account.invoice', self.id)
        self = self.with_context(lang=lang)
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Vendor Bill'),
            'out_refund': _('Credit Note'),
            'in_refund': _('Vendor Credit note'),
        }
        ctx = dict(
            default_model='account.invoice',
            default_res_id=self.ids[0],
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            model_description=TYPES[self.type],
            custom_layout="markant_account.markant_invoice_mail_notification_paynow",
            force_email=True
        )
        return {
            'name': _('Send Invoice'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice.send',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def _compute_journal_entries_count(self):
        for rec in self:
            count = 0
            if rec.move_id:
                count += 1
            if rec.backdate_move_id:
                count += 1
            rec.je_count = count

    @api.multi
    def invoice_show_journal_entries(self):
        self.ensure_one()
        je_ids = []
        if self.move_id:
            je_ids.append(self.move_id.id)
        if self.backdate_move_id:
            je_ids.append(self.backdate_move_id.id)

        if je_ids:
            return {
                'name': _('Journal Entries'),
                'domain': [('id', 'in', je_ids)],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'views': [(self.env.ref('account.view_move_tree').id, 'tree'),
                          (self.env.ref('account.view_move_form').id, 'form')],
            }

    @api.model
    def invoice_line_move_line_get(self):
        res = super(AccountInvoice, self).invoice_line_move_line_get()
        interim_account_id = self.interim_account_id.id
        if self.backdated_post:
            i = 0
            for line in res:
                for invline in self.invoice_line_ids:
                    if line.get('invl_id', 0) == invline.id:
                        if interim_account_id:
                            res[i]['account_id'] = interim_account_id
                i = i+1
        return res

    @api.multi
    def action_invoice_open(self):
        account_move = self.env['account.move']
        res = super(AccountInvoice, self).action_invoice_open()
        journal_id = self.env["ir.config_parameter"].sudo().get_param("markant_account.interim_account_journal_id")
        if journal_id:
            journal_id = self.env['account.journal'].browse([int(journal_id)])
        for inv in self:
            if inv.backdated_post:
                if not journal_id:
                    raise Warning(_('Please define the journal for Interim Account for backdated post.'))
                if not journal_id.sequence_id:
                    raise Warning(_('Please define sequence on the journal related to this invoice.'))
               
                company_currency = inv.company_id.currency_id

                iml = []
                for line in inv.invoice_line_ids:
                    new_move_line_dict = {
                        'invl_id': line.id,
                        'type': 'src',
                        'name': line.name,
                        'price_unit': line.price_unit,
                        'quantity': line.quantity,
                        'price': line.price_subtotal,
                        'account_id': line.account_id.id,
                        'product_id': line.product_id.id,
                        'uom_id': line.uom_id.id,
                        'account_analytic_id': line.account_analytic_id.id,
                        'invoice_id': self.id,
                    }
                    iml.append(new_move_line_dict)
                    diff_currency = inv.currency_id != company_currency
                    total, total_currency, iml = inv.compute_invoice_totals(company_currency, iml)
                    name = inv.name or ''
                    if True:
                        iml.append({
                            'type': 'dest',
                            'name': name,
                            'price': total,
                            'account_id': inv.interim_account_id.id,
                            'date_maturity': inv.date_due,
                            'amount_currency': diff_currency and total_currency,
                            'currency_id': diff_currency and inv.currency_id.id,
                            'invoice_id': inv.id
                        })
                part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
                line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
                line = inv.group_lines(iml, line)

                line = inv.finalize_invoice_move_lines(line)

                date = inv.backdated_date
                
                move_vals = {
                    'ref': "Backdated " + str(inv.number),
                    'line_ids': line,
                    'journal_id': journal_id.id,
                    'date': date,
                    'narration': inv.comment,
                }

                move = account_move.create(move_vals)
                if journal_id.sequence_id:
                    # If invoice is actually refund and journal has a refund_sequence then use that one or use the regular one
                    sequence = journal_id.sequence_id
                    new_name = sequence.with_context(ir_sequence_date=move.date).next_by_id()
                    resp = move.write({'name': new_name})
                # Pass invoice in method post: used if you want to get the same
                # account move reference when creating the same invoice after a cancelled one:
                move.post(invoice = inv)
                # make the invoice point to that move
                vals = {
                    'backdate_move_id': move.id,
                }
                inv.write(vals)
        return res

    @api.multi
    def action_cancel(self):
        res = super(AccountInvoice, self).action_cancel()
        moves = self.env['account.move']
        for inv in self:
            if inv.backdate_move_id:
                moves += inv.backdate_move_id
            #unreconcile all journal items of the invoice, since the cancellation will unlink them anyway
            if inv.backdate_move_id:
                inv.backdate_move_id.line_ids.filtered(lambda x: x.account_id.reconcile).remove_move_reconcile()

        # First, set the invoices as cancelled and detach the move ids
        self.write({'backdate_move_id': False})
        if moves:
            # second, invalidate the move(s)
            moves.button_cancel()
            # delete the move this invoice was pointing to
            # Note that the corresponding move_lines and move_reconciles
            # will be automatically deleted too
            moves.unlink()
        return res

    def _compute_credit_note_count(self):
        for rec in self:
            rec.cn_count = self.search_count([
                ('refund_invoice_id', '=', rec.id)])

    @api.multi
    def cn_show_invoice(self):
        self.ensure_one()
        tmp_id = self.search([('number', '=', self.origin)]).id
        if self.type == 'out_refund':
            return {
                'name': _('Invoices'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.invoice',
                'res_id': tmp_id,
                'type': 'ir.actions.act_window',
                'views': [(self.env.ref('account.invoice_form').id, 'form')]
            }
        elif self.type == 'in_refund':
            return {
                'name': _('Vendor Bills'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.invoice',
                'res_id': tmp_id,
                'type': 'ir.actions.act_window',
                'views': [(self.env.ref(
                    'account.invoice_supplier_form').id, 'form')]
            }

    @api.multi
    def invoice_show_credit_note(self):
        self.ensure_one()
        domain = [('refund_invoice_id', '=', self.id)]
        if self.type == 'out_invoice':
            return {
                'name': _('Credit Notes'),
                'domain': domain,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.invoice',
                'type': 'ir.actions.act_window',
                'views': [(self.env.ref('account.invoice_tree').id, 'tree'),
                          (self.env.ref('account.invoice_form').id, 'form')],
            }
        elif self.type == 'in_invoice':
            return {
                'name': _('Refunds'),
                'domain': domain,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.invoice',
                'type': 'ir.actions.act_window',
                'views': [
                    (self.env.ref('account.invoice_supplier_tree').id, 'tree'),
                    (self.env.ref('account.invoice_supplier_form').id, 'form')
                ],
            }


    # Cees Invoices
    @api.multi
    @api.onchange('type')
    def compute_report_to_send_readonly_required(self):
        for record in self:
            if record.type == 'out_invoice':
                sale_orders = record.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')
                if sale_orders:
                    record.report_to_send_readonly = True
                    record.report_to_send_required = False
                else:
                    record.report_to_send_readonly = False
                    record.report_to_send_required = True
            else:
                record.report_to_send_readonly = True
                record.report_to_send_required = False

    report_to_send_readonly = fields.Boolean(compute="compute_report_to_send_readonly_required")
    report_to_send_required = fields.Boolean(compute="compute_report_to_send_readonly_required")
    report_to_send = fields.Selection([
        ('so_gross_total', 'Markant Invoice - Gross Total'),
        ('so_discount', 'Markant Invoice - Discount'),
        ('so_sub_total', 'Markant Invoice - Subtotal'),
    ], string="Report to send/print", default="so_discount")


    @api.depends('invoice_line_ids.price_gross_total')
    def _amount_all_invoice_markant(self):
        for invoice in self:
            inv_gross_total = inv_discount_total = inv_subtotal_total = inv_project_disc_total = inv_installation_total = inv_admin_total = 0.0
            pd_order_line = invoice.invoice_line_ids.filtered(lambda ol: ol.is_project_discount_line)
            admin_order_line = invoice.invoice_line_ids.filtered(lambda ol: ol.is_min_admin_cost_rule_line)
            mont_install_order_line = invoice.invoice_line_ids.filtered(lambda ol: ol.is_montage_install_rule_line)
            for line in invoice.invoice_line_ids:
                if line.is_project_discount_line:
                    continue
                if line.is_min_admin_cost_rule_line:
                    continue
                if line.is_montage_install_rule_line:
                    continue
                inv_gross_total += line.price_gross_total
                inv_discount_total += line.price_gross_total - line.price_subtotal
            
            for line in pd_order_line:
                inv_project_disc_total += line.price_unit

            for line in admin_order_line:
                inv_admin_total += line.price_unit

            for line in mont_install_order_line:
                inv_installation_total += line.price_unit

            invoice.update({
                'inv_gross_total': inv_gross_total,
                'inv_discount_total': inv_discount_total,
                'inv_subtotal_total': inv_gross_total - inv_discount_total,
                'inv_project_disc_total': inv_project_disc_total,
                'inv_installation_total': inv_installation_total,
                'inv_admin_total': inv_admin_total,
            })

    inv_gross_total = fields.Monetary(string='Gross Total', store=True, readonly=True, compute='_amount_all_invoice_markant')
    inv_discount_total = fields.Monetary(string='Total Disc Lines', store=True, readonly=True, compute='_amount_all_invoice_markant')
    inv_subtotal_total = fields.Monetary(string='Sum of Subtotal', store=True, readonly=True, compute='_amount_all_invoice_markant')
    inv_project_disc_total = fields.Monetary(string='Project Discount', store=True, readonly=True, compute='_amount_all_invoice_markant')
    inv_installation_total = fields.Monetary(string='Installation', store=True, readonly=True, compute='_amount_all_invoice_markant')
    inv_admin_total = fields.Monetary(string='Administration', store=True, readonly=True, compute='_amount_all_invoice_markant')

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"


    @api.depends('quantity', 'price_unit')
    def _compute_price_gross_total(self):
        for line in self:
            line.price_gross_total = line.price_unit * line.quantity
            
    price_gross_total = fields.Float(compute='_compute_price_gross_total', string='Gross Total', readonly=True, store=True, digits=dp.get_precision('Product Price'))
    is_project_discount_line = fields.Boolean()
    is_min_admin_cost_rule_line = fields.Boolean()
    is_montage_install_rule_line = fields.Boolean()

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        res.update({
            'report_to_send' : self.report_to_send,
            'partner_invoice_id': self.partner_invoice_id.id
        })
        return res

    @api.multi
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if vals.get('report_to_send') is not None:
            for record in self:
                for inv in record.invoice_ids:
                    invresp = inv.write({'report_to_send': record.report_to_send,
                                         'partner_invoice_id': record.partner_invoice_id.id})
        return res

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        res.update({
            'is_project_discount_line' :self.is_project_discount_line,
            'is_min_admin_cost_rule_line' :self.is_min_admin_cost_rule_line,
            'is_montage_install_rule_line' : self.is_montage_install_rule_line
        })
        return res

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    @api.multi
    def _create_invoice(self, order, so_line, amount):
        invoice = super(SaleAdvancePaymentInv, self)._create_invoice(order, so_line, amount)
        write_done = invoice.write({'report_to_send': order.report_to_send,
                                    'partner_invoice_id': order.partner_invoice_id.id})
        return invoice

