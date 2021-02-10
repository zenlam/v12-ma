from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    kit_component = fields.Boolean(string='Consumable KIT Component')

    @api.onchange('kit_component')
    def onchange_kit_component(self):
        if self.kit_component:
            self.can_be_expensed = False
            self.landed_cost_ok = False
            self.configurable_ok = False
            self.obsolete_product = False
            self.mrp_cost_ok = False
            self.type = 'consu'

    @api.multi
    def write(self, vals):
        if vals.get('kit_component'):
            vals['can_be_expensed'] = False
            vals['landed_cost_ok'] = False
            vals['configurable_ok'] = False
            vals['mrp_cost_ok'] = False
            vals['type'] = 'consu'
            vals['obsolete_product'] = False
        result = super(ProductTemplate, self).write(vals)
        for rec in self:
            if rec.kit_component and rec.type != 'consu':
                raise ValidationError(_('Only "Consumable" type product can be mark as "KIT Component"'))
        return result


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def write(self, vals):
        if vals.get('kit_component'):
            vals['obsolete_product'] = False
        return super(ProductProduct, self).write(vals)
