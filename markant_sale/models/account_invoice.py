# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'


    # @api.onchange('partner_id', 'company_id')
    # def _onchange_partner_id(self):
    #     res = super(AccountInvoice, self)._onchange_partner_id()
    #     if self.partner_id:
    #         sub_partner_ids = [self.partner_id.id]
    #         if self.partner_id.child_ids:
    #             for child in self.partner_id.child_ids:
    #                 sub_partner_ids.append(child.id)
    #         if self.partner_id.child_ids_address:
    #             for child_adds in self.partner_id.child_ids_address:
    #                 sub_partner_ids.append(child_adds.id)
    #         res['domain']['partner_shipping_id'] =  [('id', 'in', sub_partner_ids)]
    #     else:
    #         res['domain']['partner_shipping_id'] =  [('id', 'in', [0])]
    #     return res

