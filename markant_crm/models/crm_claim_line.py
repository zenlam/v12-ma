from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp


class CrmClaimLine(models.Model):
    _name = 'crm.claim.line'
    _description = 'CRM Claim Line'

    crm_claim_id = fields.Many2one('crm.claim', string='Claim')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char('Description')
    qty = fields.Float(string='Quantity',
                       digits=dp.get_precision('Product Unit of Measure'))
    document_type = fields.Selection(selection=[('invoice', 'Invoice'),
                                                ('sale_order', 'Sale Order')],
                                     string='Document type')
    so_id = fields.Many2one('sale.order', string='Sale Order Number')
    inv_id = fields.Many2one('account.invoice', string='Invoice Number')
    as400_doc = fields.Text(string='AS400 Document')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.name
            self.qty = 1

    @api.onchange('document_type', 'so_id', 'inv_id')
    def load_line_domain(self):
        doc_type = self.document_type
        domain = []
        product_ids = []
        if doc_type:
            if doc_type == 'invoice':
                self.so_id = None
            else:
                self.inv_id = None
            if self.inv_id:
                self.so_id = None
                product_ids = \
                    self.inv_id.invoice_line_ids.mapped('product_id').ids
            elif self.so_id:
                self.inv_id = None
                product_ids = self.so_id.order_line.mapped('product_id').ids
            if product_ids:
                domain += [('id', 'in', product_ids)]
        return {'domain': {'product_id': domain}}
