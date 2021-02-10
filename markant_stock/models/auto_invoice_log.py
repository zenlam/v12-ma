from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AutoInvoiceLog(models.Model):
    _name = 'auto.invoice.log'
    _inherit = ['mail.thread']
    _description = 'Auto Invoice Log'
    _rec_name = 'date'

    date = fields.Datetime(string='Date', readonly=True)
    sale_order_ref_ids = fields.Many2many(
        'sale.order', 'sale_order_log_rel',
        'col1', 'col2', string='Sale Order Reference', readonly=True)
    invoice_ref_ids = fields.Many2many(
        'account.invoice', 'account_invoice_log_rel',
        'col1', 'col2', string='Invoice Reference', readonly=True)
    auto_invoice_so_rel = fields.One2many('auto.invoice.sale.order.relation',
                                          inverse_name='log_id',
                                          string='Sale Order Reference',
                                          readonly=True)


    @api.multi
    def action_send_auto_invoice_mail(self, lang=False, email=None, user=False,
                                      no_of_so=False, no_of_inv=False,
                                      portal_url=False):
        self.ensure_one()
        try:
            template = self.env.ref(
                'markant_stock.email_template_markant_auto_invoice')
        except ValueError:
            template = False

        if email:
            template.with_context(
                lang=lang, no_of_so=no_of_so, no_of_inv=no_of_inv,
                email=email, portal_url=portal_url, user=user).send_mail(
                self.id, force_send=True)
        return True


class AutoInvoiceSaleOrderRelation(models.Model):
    _name = 'auto.invoice.sale.order.relation'
    _inherit = ['mail.thread']
    _description = 'Auto Invoice Sale Order Relation'

    log_id = fields.Many2one(comodel_name='product.variant.compute.price.log',
                             string='Auto Invoice Log')
    order_id = fields.Many2one('sale.order', string='Order Number')
    confirmation_date = fields.Datetime(string='Confirmation Date', related='order_id.confirmation_date')
    commitment_date = fields.Datetime(string='Commitment Date', related='order_id.commitment_date')
    expected_date = fields.Datetime(string='Expected Date', related='order_id.expected_date')
    partner_id = fields.Many2one('res.partner', string='Customer', related='order_id.partner_id')
    salesperson = fields.Many2one('res.users', string='Salesperson', related='order_id.user_id')
    currency_id = fields.Many2one("res.currency", related='order_id.currency_id', string="Currency", readonly=True, required=True)
    amount_total = fields.Monetary(string='Total', related='order_id.amount_total')
    invoice_status = fields.Selection([
        ('upselling', 'Upselling Opportunity'),
        ('invoiced', 'Fully Invoiced'),
        ('to invoice', 'To Invoice'),
        ('no', 'Nothing to Invoice')
    ], string='Invoice Status')
    cron_status = fields.Char(string='Cron Status')
    error_log = fields.Char(string='Error Log')

    @api.multi
    def action_show_error_message(self):
        self.ensure_one()
        raise UserError(self.error_log)
