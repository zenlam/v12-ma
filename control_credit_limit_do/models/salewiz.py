from odoo import api, fields, models, _


class SaleConfirmLimit(models.TransientModel):
    _inherit = 'sale.control.limit.wizard'

    picking_id = fields.Many2one('stock.picking')

    @api.multi
    def agent_exceed_limit_do(self):
        self.picking_id.need_approval = True
        order = self.picking_id.sale_id
        if order:
            resp = order.write({
                'finance_block_urgent_so': True,
                'cl_request_approval_user_id': self.env.uid
            })

            group = self.env.ref('control_credit_limit.'
                             'group_sale_manager_credit_limit')
            if group.users:
                partner_ids = []
                for myu in group.users:
                    partner_ids.append(myu.partner_id.id)

                email_values = {}
                if partner_ids:
                    email_values['recipient_ids'] = [(4, pid) for pid in partner_ids]

                template = self.env.ref('control_credit_limit_do.email_template_cl_so_approval_request')
                resp = template.send_mail(order.id, force_send = True, email_values=email_values)

                # template.send_mail(self.id, force_send=True, email_values={'email_to': email_values})
                # order.message_subscribe(partner_ids)
                # order.message_post(body='Order Approval is requested for a customer with Credit Limit issue',
                #     subject='Order Approval is requested for a customer with Credit Limit issue',
                #     message_type='comment', subtype='mail.mt_comment', partner_ids=partner_ids)

        # group = self.env.ref('control_credit_limit_do.'
                             # 'group_transfer_manager_credit_limit')

        # if group.users:
        #     partner_ids = []
        #     for myu in group.users:
        #         partner_ids.append(myu.partner_id.id)
        #     self.picking_id.message_subscribe(partner_ids)
        #     self.picking_id.message_post(body='Transfer Approval is requested for a customer with Credit Limit issue',
        #         subject='Transfer Approval is requested for a customer with Credit Limit issue',
        #         message_type='comment', subtype='mail.mt_comment')
        return True

    @api.multi
    def agent_exceed_limit(self):
        self.sale_order.need_approval = True
        group = self.env.ref('control_credit_limit.'
                             'group_sale_manager_credit_limit')
        if group.users:
            partner_ids = []
            for myu in group.users:
                partner_ids.append(myu.partner_id.id)
            self.sale_order.message_subscribe(partner_ids)
            self.sale_order.message_post(body='Order Approval is requested for a customer with Credit Limit issue',
                subject='Order Approval is requested for a customer with Credit Limit issue',
                message_type='comment', subtype='mail.mt_comment')
        
    @api.multi
    def exceed_limit_approve_do(self):
        context = {'can_exceed_limit': 1}
        return self.picking_id.with_context(context).button_validate()
