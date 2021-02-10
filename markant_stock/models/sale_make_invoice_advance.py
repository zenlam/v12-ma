import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    @api.model
    def _get_auto_advance_payment_method(self):
        if len(self._context.get('markant_orders')) == 1:
            order = self._context.get('markant_orders')[0]
            if order.order_line.filtered(lambda dp: dp.is_downpayment) and \
                    order.invoice_ids.filtered(
                        lambda invoice: invoice.state != 'cancel') or \
                    order.order_line.filtered(lambda l: l.qty_to_invoice < 0):
                return 'all'
            else:
                return 'delivered'
        return 'all'

    @api.multi
    def create_invoices_per_order(self, sale_orders):
        if self._context.get('markant_auto_invoice'):
            advance_payment_method = self._get_auto_advance_payment_method()
        else:
            advance_payment_method = self.advance_payment_method

        # HITESH : Check if all saleorder have same report to send or not.
        if len(sale_orders) > 1:
            report_to_send = sale_orders.mapped('report_to_send')
            if len(set(report_to_send))!=1:
                raise UserError("Seems like SO's use different print method!")
        # ENDHITESH : report to send
        inv = False

        if advance_payment_method == 'delivered':
            inv = sale_orders.action_invoice_create()
            invoice = self.env['account.invoice'].browse(inv)
            if self._context.get('markant_auto_invoice'):
                invoice.action_invoice_open()
                for x in invoice:
                    if x.partner_id.email:
                        x.action_send_mail(email=x.partner_id.email,
                                           user=self.env.uid,
                                           lang=x.partner_id.lang)
                return invoice

        elif advance_payment_method == 'all':
            inv = sale_orders.action_invoice_create(final=True)
            invoice = self.env['account.invoice'].browse(inv)
            if self._context.get('markant_auto_invoice'):
                invoice.action_invoice_open()
                for x in invoice:
                    if x.partner_id.email:
                        x.action_send_mail(email=x.partner_id.email,
                                           user=self.env.uid,
                                           lang=x.partner_id.lang)
                return invoice

        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.config_parameter'].sudo().set_param(
                    'sale.default_deposit_product_id', self.product_id.id)

            sale_line_obj = self.env['sale.order.line']
            for order in sale_orders:
                if advance_payment_method == 'percentage':
                    amount = order.amount_untaxed * self.amount / 100
                else:
                    amount = self.amount
                if self.product_id.invoice_policy != 'order':
                    raise UserError(_(
                        'The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(_(
                        "The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))
                taxes = self.product_id.taxes_id.filtered(
                    lambda r: not order.company_id or
                              r.company_id == order.company_id)
                if order.fiscal_position_id and taxes:
                    tax_ids = order.fiscal_position_id.map_tax(
                        taxes, self.product_id, order.partner_shipping_id)\
                        .ids
                else:
                    tax_ids = taxes.ids
                context = {'lang': order.partner_id.lang}
                analytic_tag_ids = []
                for line in order.order_line:
                    analytic_tag_ids = [(4, analytic_tag.id, None) for
                                        analytic_tag in line.analytic_tag_ids]
                so_line = sale_line_obj.create({
                    'name': _('Advance: %s') % (time.strftime('%m %Y'),),
                    'price_unit': amount,
                    'product_uom_qty': 0.0,
                    'order_id': order.id,
                    'discount': 0.0,
                    'product_uom': self.product_id.uom_id.id,
                    'product_id': self.product_id.id,
                    'analytic_tag_ids': analytic_tag_ids,
                    'tax_id': [(6, 0, tax_ids)],
                    'is_downpayment': True,
                })
                del context
                invoice = self._create_invoice(order, so_line, amount)

                if self._context.get('markant_auto_invoice'):
                    for x in invoice:
                        x.action_invoice_open()
                        if x.partner_id.email:
                            x.action_send_mail(email=x.partner_id.email,
                                               user=self.env.uid,
                                               lang=x.partner_id.lang)
                if self._context.get('markant_auto_invoice'):
                    return invoice

    @api.multi
    def create_invoices(self):
        inv = []
        if self._context.get('markant_auto_invoice'):
            sale_orders = self._context.get('markant_orders')
        else:
            sale_orders = self.env['sale.order'].browse(
                self._context.get('active_ids', []))

        if self.one_invoice_per_order or self._context.get('markant_auto_invoice'):
            log_lines_obj = self.env['auto.invoice.sale.order.relation']
            invoice_log = self.env['auto.invoice.log'].sudo().create({
                'date': fields.Datetime.now()
            })
            for so in sale_orders:
                vals = {
                    'log_id': invoice_log.id,
                    'order_id': so.id,
                }
                log_line = log_lines_obj.create(vals)
                try:
                    invoice = self.create_invoices_per_order(so)
                    if invoice:
                        inv.append(invoice.id)
                        log_line.write({'cron_status': 'Successful',
                                        'invoice_status': so.invoice_status})
                    else:
                        log_line.write({'cron_status': 'No Changes',
                                        'invoice_status': so.invoice_status})
                except Exception as e:
                    log_line.write({'cron_status': 'Fail',
                                    'invoice_status': so.invoice_status,
                                    'error_log': str(e)})

            if invoice_log:
                invoice_log.sudo().write({
                    'sale_order_ref_ids': [(6, 0, sale_orders.ids)],
                    'invoice_ref_ids': [(6, 0, inv)]
                })
                for user in self.env['auto.invoice.mail'].\
                        sudo().search([]):
                    if user.email:
                        portal_url = "/web#id=%s&model=%s&" \
                                     "action=%s&view_type=form" % \
                            (invoice_log.id, invoice_log._name,
                             self.env.ref('markant_stock.'
                                          'action_markant_auto_invoice_log')
                             .id)
                        current_log_lines = log_lines_obj.search([('log_id', '=', invoice_log.id)])
                        invoice_log.action_send_auto_invoice_mail(
                            no_of_so=len(current_log_lines),
                            no_of_inv=len(invoice_log.invoice_ref_ids),
                            email=user.email,
                            user=user.user_id.name,
                            lang=user.user_id.partner_id.lang,
                            portal_url=portal_url)

        else:
            self.create_invoices_per_order(sale_orders)

        if self._context.get('open_invoices', False):
            return sale_orders.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}


    # This method should be called once a day by the scheduler
    @api.model
    def _do_auto_invoicing(self):
        orders = self.env['sale.order'].search([
            ('invoice_status', '=', 'to invoice'), ('no_auto_invoice', '=', False)])
        self._context.update({
            'markant_auto_invoice': True,
            'markant_orders': orders,
        })
        if orders:
            self.create_invoices()
