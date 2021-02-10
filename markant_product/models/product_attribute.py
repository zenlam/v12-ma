from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo.osv import expression


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    product_tmpl_ids = fields.Many2many('product.template',
                                        'product_tmpl_attr_rel',
                                        'product_id', 'attr_id',
                                        string='Products',
                                        copy=False, readonly=True)
    allow_image = fields.Boolean(string='Allow Images for Attribute Values!')

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100,
                     name_get_uid=None):
        if self.env.context.get('product_tmpl_id') and \
                self.env.context.get('configurator'):
            used_attr = []
            changes_in_steps = []
            removed_steps = []

            for step in self.env.context.get('all_steps'):
                if step[1] and (step[0] != 2 and step[2]):
                    changes_in_steps.append(step[1])
                if step[1] and step[0] == 2:
                    removed_steps.append(step[1])
                if step[2] and step[2].get('attribute_ids'):
                    for attr in step[2]['attribute_ids'][0][2]:
                        used_attr.append(attr)

            existing_steps = self.env['product.template'].browse(
                self.env.context['product_tmpl_id']).product_config_steps_ids
            for step in existing_steps:
                if step.id not in changes_in_steps + removed_steps:
                    for attr in step.attribute_ids.ids:
                        used_attr.append(attr)

            args = [['attribute_line_ids.product_tmpl_id', '=',
                     self.env.context['product_tmpl_id']],
                    ['id', 'not in', used_attr]]
        return super(ProductAttribute, self)._name_search(
            name=name, args=args, operator=operator,
            limit=limit, name_get_uid=name_get_uid)


class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    article_code = fields.Char(string='Article Code', copy=False)
    product_tmpl_ids = fields.Many2many('product.template',
                                        'product_tmpl_attr_val_rel',
                                        'product_id', 'attr_id',
                                        string='Products',
                                        copy=False, readonly=True)
    image = fields.Binary('Image', attachment=True)

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100,
                     name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name),
                      ('attribute_id', operator, name)]
        attr_vals_ids = self._search(expression.AND([domain, args]),
                                     limit=limit,
                                     access_rights_uid=name_get_uid)
        return self.browse(attr_vals_ids).name_get()


class ProductTemplateAttributeLine(models.Model):
    _inherit = 'product.template.attribute.line'
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence',
                              help="Determine the display order")
    is_display = fields.Boolean(string='Is display')
    include_inside_d = fields.Boolean(string='Include in D-Number',
                                      default=True)
    excl_desc = fields.Boolean(string='Exclude Description')
    desc_sequence = fields.Integer(string='Desc Seq',
                                   help="Determine the sequence of"
                                        "displaying the description")

    @api.model
    def create(self, values):
        res = super(ProductTemplateAttributeLine, self).create(values)
        res.update_desc_sequence()
        return res

    def update_desc_sequence(self):
        if self.desc_sequence == 0:
            mylist = []
            for line in self.product_tmpl_id.attribute_line_ids:
                mylist.append(line.desc_sequence)
            self.desc_sequence = max(mylist) + 5

    @api.onchange('attribute_id')
    def onchange_attribute_id(self):
        if self.product_tmpl_id.configurable_ok and self.attribute_id:
            self.is_display = True

    @api.onchange('is_display')
    def onchange_is_display(self):
        if self.product_tmpl_id.configurable_ok:
            if not self.is_display and len(self.value_ids) > 1:
                raise Warning(_("Can not set `Is display` to `False` as "
                                "attribute have multiple values."))

    @api.onchange('value_ids')
    def onchange_value_ids(self):
        if self.product_tmpl_id.configurable_ok:
            if len(self.value_ids) > 1:
                self.is_display = True

