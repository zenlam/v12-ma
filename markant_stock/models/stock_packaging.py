from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockPackaging(models.Model):
    _name = 'stock.packaging.table'
    _description = 'Packaging Lines'

    active = fields.Boolean('Active', default=True)
    sequence = fields.Integer(string="Sequence")
    code = fields.Char(string='Code')
    description = fields.Char(string='Description')
    table_package_id = fields.Many2one('stock.packaging.table.code.desc',
                                       required=True,
                                       string="Package")
    code_desc_id = fields.Many2one('picking.packaging',
                                   string='Packaging Table',
                                   required=True)

    @api.onchange('table_package_id')
    def _onchange_code_description(self):
        if self.table_package_id:
            self.code = self.table_package_id.code
            self.description = self.table_package_id.description

    @api.model
    def create(self, values):
        res = super(StockPackaging, self).create(values)
        res.update_sequence()
        return res

    @api.multi
    def write(self, vals):
        res = super(StockPackaging, self).write(vals)
        for rec in self:
            rec.update_sequence()
        return res

    def update_sequence(self):
        if self.sequence == 0:
            mylist = []
            for line in self.code_desc_id.packaging_line_ids:
                mylist.append(line.sequence)
            self.sequence = max(mylist) + 1
        

class StockPackagingCodeDesc(models.Model):
    _name = 'stock.packaging.table.code.desc'
    _description = 'Table to store all the packaging code'

    @api.multi
    @api.depends('description', 'code')
    def name_get(self):
        res = []
        for record in self:
            description = record.description
            if record.code:
                name = '[' + record.code + '] - ' + description
            res.append((record.id, name))
        return res

    active = fields.Boolean('Active', default=True)
    sequence = fields.Integer(string="Sequence")
    code = fields.Char(string='Code', required=True)
    description = fields.Char(string='Description')

    @api.constrains('code')
    def _unique_code_packaging(self):
        for type in self:
            packaging_code = self.search([
                ('code', '=', type.code),
                ('active', '=', type.active),
                ('id', '!=', type.id)])
            if type.active and type.code and packaging_code:
                raise ValidationError(_('This Packaging Code already '
                                        'exists. \n'
                                        'Please change the code.'))
