from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta

class PickingType(models.Model):
    _inherit = "stock.picking.type"

    credit_limit_check = fields.Boolean('Credit Limit Check')

class CreditPartner(models.Model):
    _inherit = 'res.partner'

    check_credit_limit = fields.Boolean(
        'Enforce Credit Limit', default=True,
        required=True) 
    bypass_so = fields.Boolean('Bypass for SO')
    credit_days = fields.Integer('Credit Days')
    cl_order_amount = fields.Float(compute='_compute_cl_order_amount', string="Orders Amt")
    cl_space = fields.Float(compute='_compute_cl_order_amount', string="Space")

    def _compute_cl_order_amount(self):
        for record in self:
            record.cl_order_amount = sum(record.sale_order_ids.mapped('amount_total'))
            record.cl_space = record.my_credit_limit - record.credit - record.cl_order_amount

class SaleOrder(models.Model):
    _inherit = "sale.order"


    cr_limit_finance_block = fields.Boolean('Finance Block', copy=False)
    cl_finance_block_reason = fields.Selection([
        ('credit_limit', 'Credit Limit'),
        ('credit_days', 'Credit Days'),
        ('credit_days_limit', 'Credit Days & Limit'),
    ], string="Finance Block Reason", copy=False)
    finance_block_urgent_so = fields.Boolean(copy=False)
    cl_request_approval_user_id = fields.Many2one('res.users')

    @api.one
    def check_credit_limit(self):
        if self.env.context.get('no_need_to_bypass') is not None:
            res = super(SaleOrder, self).check_credit_limit()
            return res[0]
        # partner = self.partner_id
        # # check if this is a customer for whom need to bypass 
        # if partner.bypass_so:
        #     return 1
        # else:
        #     res = super(SaleOrder, self).check_credit_limit()
        #     return res[0]
        res = super(SaleOrder, self).check_credit_limit()
        
        # Check exceed limit
        exceeded_limit = True
        if res[0] == 1:
            exceeded_limit = False


        # Check Exceed Days
        all_invoices = self.env['account.invoice'].search([
            ('partner_id', '=', self.partner_id.id),
            ('type', '=', 'out_invoice'),
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ['open']),
        ])
        exceeded_days = False
        if self.partner_id.credit_days:
            credit_days = self.partner_id.credit_days
            today_date = fields.Date.today()
            for invoice in all_invoices:
                if invoice.date_due:
                    date_due = fields.Date.from_string(invoice.date_due)
                    difference = relativedelta(today_date, date_due)
                    days = difference.days
                    if days > credit_days:
                        exceeded_days = True
                        break


        group = self.env.ref('control_credit_limit.'
                             'group_sale_manager_credit_limit')
        partner_ids = []
        if group.users:
            for myu in group.users:
                partner_ids.append(myu.partner_id.id)

        email_values = {}
        if partner_ids:
            email_values['recipient_ids'] = [(4, pid) for pid in partner_ids]

        template = self.env.ref('control_credit_limit_do.email_template_credit_limit_exceed_do')

        if exceeded_limit and exceeded_days:
            resp = self.write({
                'cl_finance_block_reason': 'credit_days_limit',
                'cr_limit_finance_block': True
            })
            resp = template.send_mail(self.id, force_send = True, email_values=email_values)
            return 1
        elif exceeded_limit:
            resp = self.write({
                'cl_finance_block_reason': 'credit_limit',
                'cr_limit_finance_block': True
            })
            resp = template.send_mail(self.id, force_send = True, email_values=email_values)
            return 1
        elif exceeded_days:
            self.write({
                'cl_finance_block_reason': 'credit_days',
                'cr_limit_finance_block': True
            })
            resp = template.send_mail(self.id, force_send = True, email_values=email_values)
            return 1
        return 1


    @api.multi
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if vals.get('cr_limit_finance_block') is not None:
            if not vals.get('cr_limit_finance_block', False):
                template = self.env.ref('control_credit_limit_do.email_template_cl_so_approved')
                for record in self:
                    if record.cl_request_approval_user_id:
                        for picking in record.picking_ids:
                            if picking.picking_type_id and picking.picking_type_id.credit_limit_check and picking.sale_id:
                                if picking.picking_type_code == 'outgoing':
                                    resp = template.send_mail(picking.id, force_send = True)
        return res

            

class StockPicking(models.Model):
    _inherit = 'stock.picking'


    need_approval = fields.Boolean(string='Pending Manager\'s Approval',
                                   default=False, copy=False)
    @api.multi
    def button_validate(self):
        self.ensure_one()
        # Condition only checked when transfer type is `outgoing` and 'credit limit' is checked
        if self._context.get('can_exceed_limit', False):
            return super(StockPicking, self).button_validate()

        if self.picking_type_id and self.picking_type_id.credit_limit_check and self.sale_id:
            if self.picking_type_code == 'outgoing':
                order = self.sale_id
                if order.cr_limit_finance_block:
                # params = order.with_context(no_need_to_bypass=True).check_credit_limit()
                # if params[0] == 1:
                #     return super(StockPicking, self).button_validate()
                # else:
                    view_id = self.env['sale.control.limit.wizard']
                    params = {'picking_id': self.id}
                    new = view_id.create(params)
                    # if self.env.user.has_group(
                    #         'control_credit_limit_do.'
                    #         'group_transfer_manager_credit_limit'):
                    #     return {
                    #         'type': 'ir.actions.act_window',
                    #         'name': 'Warning : Approve Transfer with Credit over Limit',
                    #         'res_model': 'sale.control.limit.wizard',
                    #         'view_type': 'form',
                    #         'view_mode': 'form',
                    #         'res_id': new.id,
                    #         'view_id': self.env.ref(
                    #             'control_credit_limit.'
                    #             'my_credit_limit_confirm_wizard',
                    #             False).id,
                    #         'target': 'new',
                    #     }

                    # else:
                    if True:
                        return {
                            'type': 'ir.actions.act_window',
                            'name': 'Request Approval for Transfer with Credit over Limit',
                            'res_model': 'sale.control.limit.wizard',
                            'view_type': 'form',
                            'view_mode': 'form',
                            'res_id': new.id,
                            'view_id': self.env.ref(
                                'control_credit_limit_do.my_credit_limit_confirm_transfer_approve_wizard',
                                False).id,
                            'target': 'new',
                        }
                else:
                    return super(StockPicking, self).button_validate()

        return super(StockPicking, self).button_validate()


