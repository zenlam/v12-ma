from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_invoice_open(self):
        categs = []
        for inv in self:
            if inv.type == 'in_invoice':
                for line in inv.invoice_line_ids:
                    if line.purchase_line_id:
                        if line.price_unit != line.purchase_line_id.price_unit \
                                and not line.product_id.categ_id.\
                                property_account_creditor_price_difference_categ:
                            categs.append(line.product_id.categ_id)
        if categs:
            categs = list(set(categs))
            msg = _("There are invoice line(s) where the unit price is "
                    "different from the purchase line \n and the product's "
                    "category of the invoice line(s) have no Price Difference"
                    " Account configured.\n\n Please configure Price Difference"
                    " Account for the following product category:")
            msg += '\n\n'
            for categ in categs:
                msg += '- %s \n' % categ.name
            raise UserError(msg)
        return super(AccountInvoice, self).action_invoice_open()
