from odoo import api, fields, models, _


class ProductConfigSteps(models.Model):
    _name = 'product.config.steps'
    _description = 'Product Config Steps'

    name = fields.Char(string='Name', required=True, copy=False)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Name must be unique!'),
    ]


class ProductConfigStepsAttr(models.Model):
    _name = 'product.config.steps.attr'
    _description = 'Product Config Steps Attr'
    _rec_name = 'step_id'

    sequence = fields.Integer(string='Sequence',
                              help="Determine the display order")
    step_id = fields.Many2one('product.config.steps',
                              string='Name', required=True)
    product_tmpl_id = fields.Many2one('product.template', 'Related Product',
                                      copy=True)
    attribute_ids = fields.Many2many(
        'product.attribute', 'product_template_attr_steps_rel',
        'step_id', 'attr_id', string='Attributes', required=True,
        domain="[('attribute_line_ids.product_tmpl_id','=',product_tmpl_id)]")
