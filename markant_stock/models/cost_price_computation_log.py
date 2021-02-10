from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp


class ProductVariantComputePriceLog(models.Model):
    _name = 'product.variant.compute.price.log'
    _description = 'Product Variant Cost Price Computation Log'
    _rec_name = 'date'

    date = fields.Datetime(string='Date', readonly=True)
    total_record = fields.Integer(string='Total Records')
    record_passed = fields.Integer(string='Number of Records Passed')
    record_failed = fields.Integer(string='Number of Records Failed')
    record_no_changes = fields.Integer(string='Number of Records Without Changes')
    log_line_ids = fields.One2many('product.variant.compute.price.log.line', inverse_name='log_id', string='Log Lines')


class ProductVariantComputePriceLogLine(models.Model):
    _name = 'product.variant.compute.price.log.line'
    _description = 'Product Variant Cost Price Computation Log Line'

    @api.depends('journal_entry')
    def get_entry_link(self):
        for line in self:
            if line.journal_entry:
                link = []
                journal_entry = line.journal_entry.strip()
                account_move_id = self.env['account.move'].search([('name', '=', journal_entry)])
                if account_move_id:
                    link.append('<a href=web#id=%s&action=%s&model=%s&view_type=form>%s</a>' %
                                (account_move_id.id, self.env.ref('account.action_move_journal_line').id,
                                 account_move_id.name, journal_entry))
                line.journal_entry_link = ', '.join(link)

    log_id = fields.Many2one(comodel_name='product.variant.compute.price.log', string='Variant Compute Cost Price Log')
    product_id = fields.Many2one('product.product', string='Product Variant')
    old_price = fields.Float(string='Old Price', digits=dp.get_precision('Product Price'))
    new_price = fields.Float(string='New Price', digits=dp.get_precision('Product Price'))
    variance = fields.Float(string='Variance', digits=dp.get_precision('Product Price'))
    qty_on_hand = fields.Float(string='Qty On Hand', digits=dp.get_precision('Product Unit of Measure'))
    total_variance = fields.Float(string='Total Variance', digits=dp.get_precision('Product Price'))
    journal_entry = fields.Char(string='Journal Entry')
    journal_entry_link = fields.Html(string='Journal Entry', compute=get_entry_link)
    status = fields.Char(string='Status')
    error_log = fields.Char(string='Error Log')

    @api.multi
    def action_show_error_message(self):
        self.ensure_one()
        raise UserError(self.error_log)
