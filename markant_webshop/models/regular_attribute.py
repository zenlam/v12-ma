# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class RegularAttribute(models.Model):
    _name = "regular.attribute"
    _description = "Regular Product Attributes"
    _order = 'sequence, id'

    name = fields.Char('Attribute', required=True, translate=True)
    sequence = fields.Integer('Sequence', help="Determine the display order",
                              index=True)
    value_ids = fields.One2many('regular.attribute.value', 'attribute_id',
                                'Values', copy=True)


class RegularAttributeValue(models.Model):
    _name = "regular.attribute.value"
    _description = "Regular Product Attributes Values"
    _order = 'sequence, id'

    name = fields.Char(string='Value', required=True, translate=True)
    sequence = fields.Integer(string='Sequence',
                              help="Determine the display order", index=True)
    attribute_id = fields.Many2one('regular.attribute', string='Attribute',
                                   ondelete='cascade', required=True,
                                   index=True)
    product_tmpl_id = fields.Many2one('product.template',
                                      string='Product Template')

    _sql_constraints = [
        ('webshop_value_company_uniq', 'unique (name, attribute_id)',
         'This attribute value already exists !')
    ]


class ProductTmplRegularAttrLine(models.Model):
    """Attributes available on product.template with their selected values in a m2m.
    Used as a configuration model to generate the appropriate product.template.regular.attribute.value"""
    _name = "template.regular.attribute.line"
    _rec_name = 'attribute_id'
    _description = 'Product Template Regular Attribute Line'
    _order = 'attribute_id, id'

    product_tmpl_id = fields.Many2one('product.template', string='Product Template', ondelete='cascade', required=True, index=True)
    attribute_id = fields.Many2one('regular.attribute', string='Manual Attribute', ondelete='restrict', required=True, index=True)
    value_ids = fields.Many2many('regular.attribute.value', string='Manual Attribute Values')
    product_template_value_ids = fields.Many2many(
        'template.regular.attribute.value',
        string='Regular Product Attribute Values',
        compute="_set_product_template_value_ids",
        store=False)

    @api.constrains('value_ids', 'attribute_id')
    def _check_valid_attribute(self):
        if any(not line.value_ids or line.value_ids > line.attribute_id.value_ids for line in self):
            raise ValidationError(_('You cannot use this regular attribute with the following regular attribute value.'))
        return True

    @api.model
    def create(self, values):
        res = super(ProductTmplRegularAttrLine, self).create(values)
        res._update_product_template_attribute_values()
        return res

    def write(self, values):
        res = super(ProductTmplRegularAttrLine, self).write(values)
        self._update_product_template_attribute_values()

        if 'attribute_id' in values:
            # delete remaining product.template.attribute.value that are not used on any line
            product_template_attribute_values_to_remove = self.env['template.regular.attribute.value']
            for product_template in self.mapped('product_tmpl_id'):
                product_template_attribute_values_to_remove += product_template_attribute_values_to_remove.search([
                    ('product_tmpl_id', '=', product_template.id),
                    ('product_attribute_value_id', 'not in', product_template.regular_attribute_line_ids.mapped('value_ids').ids),
                ])
            product_template_attribute_values_to_remove.unlink()

        return res

    @api.depends('value_ids')
    def _set_product_template_value_ids(self):
        for product_template_attribute_line in self:
            product_template_attribute_line.product_template_value_ids = self.env['template.regular.attribute.value'].search([
                ('product_tmpl_id', 'in', product_template_attribute_line.product_tmpl_id.ids),
                ('product_attribute_value_id', 'in', product_template_attribute_line.value_ids.ids)]
            )

    @api.multi
    def unlink(self):
        for product_template_attribute_line in self:
            self.env['template.regular.attribute.value'].search([
                ('product_tmpl_id', 'in', product_template_attribute_line.product_tmpl_id.ids),
                ('product_attribute_value_id.attribute_id', 'in', product_template_attribute_line.value_ids.mapped('attribute_id').ids)]).unlink()

        return super(ProductTmplRegularAttrLine, self).unlink()

    def _update_product_template_attribute_values(self):
        """
        Create or unlink product.template.attribute.value based on the attribute lines.
        If the product.attribute.value is removed, remove the corresponding product.template.attribute.value
        If no product.template.attribute.value exists for the newly added product.attribute.value, create it.
        """
        for attribute_line in self:
            # All existing template.regular.attribute.value for this template
            product_template_attribute_values_to_remove = self.env['template.regular.attribute.value'].search([
                ('product_tmpl_id', '=', attribute_line.product_tmpl_id.id),
                ('product_attribute_value_id.attribute_id', 'in', attribute_line.value_ids.mapped('attribute_id').ids)])
            # All existing product.attribute.value shared by all products
            # eg (Yellow, Red, Blue, Small, Large)
            existing_product_attribute_values = product_template_attribute_values_to_remove.mapped('product_attribute_value_id')

            # Loop on regular.attribute.values for the line (eg: Yellow, Red, Blue)
            for product_attribute_value in attribute_line.value_ids:
                if product_attribute_value in existing_product_attribute_values:
                    # property is already existing: don't touch, remove it from list to avoid unlinking it
                    product_template_attribute_values_to_remove = product_template_attribute_values_to_remove.filtered(
                        lambda value: product_attribute_value not in value.mapped('product_attribute_value_id')
                    )
                else:
                    # property does not exist: create it
                    self.env['template.regular.attribute.value'].create({
                        'product_attribute_value_id': product_attribute_value.id,
                        'product_tmpl_id': attribute_line.product_tmpl_id.id})

            # at this point, existing properties can be removed to reflect the modifications on value_ids
            if product_template_attribute_values_to_remove:
                product_template_attribute_values_to_remove.unlink()

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        # TDE FIXME: currently overriding the domain; however as it includes a
        # search on a m2o and one on a m2m, probably this will quickly become
        # difficult to compute - check if performance optimization is required
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            args = args or []
            domain = ['|', ('attribute_id', operator, name), ('value_ids', operator, name)]
            attribute_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
            return self.browse(attribute_ids).name_get()
        return super(ProductTmplRegularAttrLine, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)


class ProductTmplRegularAttrValue(models.Model):
    """Materialized relationship between attribute values
    and product template generated by the product.template.attribute.line"""

    _name = "template.regular.attribute.value"
    _order = 'product_attribute_value_id, id'
    _description = 'Regular Product Attribute Value'

    name = fields.Char('Value', related="product_attribute_value_id.name")
    product_attribute_value_id = fields.Many2one(
        'regular.attribute.value', string='Attribute Value',
        required=True, ondelete='cascade', index=True)
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template',
        required=True, ondelete='cascade', index=True)
    attribute_id = fields.Many2one(
        'regular.attribute', string='Attribute',
        related="product_attribute_value_id.attribute_id")
    sequence = fields.Integer('Sequence', related="product_attribute_value_id.sequence")

    @api.multi
    def name_get(self):
        if not self._context.get('show_attribute', True):  # TDE FIXME: not used
            return super(ProductTmplRegularAttrValue, self).name_get()
        return [(value.id, "%s: %s" % (value.attribute_id.name, value.name)) for value in self]

class ProductProdRegularAttrLine(models.Model):
    """Attributes available on product.template with their selected values in a m2m.
    Used as a configuration model to generate the appropriate product.template.regular.attribute.value"""
    _name = "product.regular.attribute.line"
    _rec_name = 'attribute_id'
    _description = 'Product Product Regular Attribute Line'
    _order = 'attribute_id, id'

    product_id = fields.Many2one('product.product', string='Product Product', ondelete='cascade', required=True, index=True)
    attribute_id = fields.Many2one('regular.attribute', string='Manual Attribute', ondelete='restrict', required=True, index=True)
    value_ids = fields.Many2many('regular.attribute.value', string='Manual Attribute Values')
    product_product_value_ids = fields.Many2many(
        'product.regular.attribute.value',
        string='Regular Product Attribute Values',
        compute="_set_product_product_value_ids",
        store=False)

    @api.constrains('value_ids', 'attribute_id')
    def _check_valid_attribute(self):
        if any(not line.value_ids or line.value_ids > line.attribute_id.value_ids for line in self):
            raise ValidationError(_('You cannot use this regular attribute with the following regular attribute value.'))
        return True

    @api.model
    def create(self, values):
        res = super(ProductProdRegularAttrLine, self).create(values)
        res._update_product_prod_attribute_values()
        # raise_warning = False
        # msg = 'The webshop attribute and webshop attribute ' \
        #       'value is mapped wrongly! \n\n'
        # for value in res.value_ids:
        #     if value.attribute_id != res.attribute_id:
        #         raise_warning = True
        #         msg += ' - Regular Attribute: %s \n' \
        #                ' - Regular Attribute Value: %s \n\n' % (
        #                res.attribute_id.name,
        #                value.name)
        # if raise_warning is True:
        #     raise ValidationError(_(msg))
        return res

    def write(self, values):
        res = super(ProductProdRegularAttrLine, self).write(values)
        self._update_product_prod_attribute_values()

        if 'attribute_id' in values:
            # delete remaining product.template.attribute.value that are not used on any line
            product_prod_attribute_values_to_remove = self.env['product.regular.attribute.value']
            for product in self.mapped('product_id'):
                product_prod_attribute_values_to_remove += product_prod_attribute_values_to_remove.search([
                    ('product_id', '=', product.id),
                    ('product_attribute_value_id', 'not in', product.regular_attribute_line_ids.mapped('value_ids').ids),
                ])
            product_prod_attribute_values_to_remove.unlink()

        # raise_warning = False
        # msg = 'The webshop attribute and webshop attribute ' \
        #       'value is mapped wrongly! \n\n'
        # for line in self:
        #     for value in line.value_ids:
        #         if value.attribute_id != line.attribute_id:
        #             raise_warning = True
        #             msg += ' - Regular Attribute: %s \n' \
        #                    ' - Regular Attribute Value: %s \n\n' % (
        #                    line.attribute_id.name,
        #                    value.name)
        # if raise_warning is True:
        #     raise ValidationError(_(msg))

        return res

    @api.depends('value_ids')
    def _set_product_product_value_ids(self):
        for product_attribute_line in self:
            product_attribute_line.product_product_value_ids = self.env['product.regular.attribute.value'].search([
                ('product_id', 'in', product_attribute_line.product_id.ids),
                ('product_attribute_value_id', 'in', product_attribute_line.value_ids.ids)]
            )

    @api.multi
    def unlink(self):
        for product_attribute_line in self:
            self.env['product.regular.attribute.value'].search([
                ('product_id', 'in', product_attribute_line.product_id.ids),
                ('product_attribute_value_id.attribute_id', 'in', product_attribute_line.value_ids.mapped('attribute_id').ids)]).unlink()

        return super(ProductProdRegularAttrLine, self).unlink()

    def _update_product_prod_attribute_values(self):
        """
        Create or unlink product.product.attribute.value based on the attribute lines.
        If the product.attribute.value is removed, remove the corresponding product.template.attribute.value
        If no product.product.attribute.value exists for the newly added product.attribute.value, create it.
        """
        for attribute_line in self:
            # All existing template.regular.attribute.value for this template
            product_attribute_values_to_remove = self.env['product.regular.attribute.value'].search([
                ('product_id', '=', attribute_line.product_id.id),
                ('product_attribute_value_id.attribute_id', 'in', attribute_line.value_ids.mapped('attribute_id').ids)])
            # All existing product.attribute.value shared by all products
            # eg (Yellow, Red, Blue, Small, Large)
            existing_product_attribute_values = product_attribute_values_to_remove.mapped('product_attribute_value_id')

            # Loop on regular.attribute.values for the line (eg: Yellow, Red, Blue)
            for product_attribute_value in attribute_line.value_ids:
                if product_attribute_value in existing_product_attribute_values:
                    # property is already existing: don't touch, remove it from list to avoid unlinking it
                    product_attribute_values_to_remove = product_attribute_values_to_remove.filtered(
                        lambda value: product_attribute_value not in value.mapped('product_attribute_value_id')
                    )
                else:
                    # property does not exist: create it
                    self.env['product.regular.attribute.value'].create({
                        'product_attribute_value_id': product_attribute_value.id,
                        'product_id': attribute_line.product_id.id})

            # at this point, existing properties can be removed to reflect the modifications on value_ids
            if product_attribute_values_to_remove:
                product_attribute_values_to_remove.unlink()

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        # TDE FIXME: currently overriding the domain; however as it includes a
        # search on a m2o and one on a m2m, probably this will quickly become
        # difficult to compute - check if performance optimization is required
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            args = args or []
            domain = ['|', ('attribute_id', operator, name), ('value_ids', operator, name)]
            attribute_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
            return self.browse(attribute_ids).name_get()
        return super(ProductProdRegularAttrLine, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)


class ProductProdRegularAttrValue(models.Model):
    """Materialized relationship between attribute values
    and product template generated by the product.template.attribute.line"""

    _name = "product.regular.attribute.value"
    _order = 'product_attribute_value_id, id'
    _description = 'Regular Product Attribute Value'

    name = fields.Char('Value', related="product_attribute_value_id.name")
    product_attribute_value_id = fields.Many2one(
        'regular.attribute.value', string='Attribute Value',
        required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one(
        'product.product', string='Product Template',
        required=True, ondelete='cascade', index=True)
    attribute_id = fields.Many2one(
        'regular.attribute', string='Attribute',
        related="product_attribute_value_id.attribute_id")
    sequence = fields.Integer('Sequence', related="product_attribute_value_id.sequence")

    @api.multi
    def name_get(self):
        if not self._context.get('show_attribute', True):  # TDE FIXME: not used
            return super(ProductProdRegularAttrValue, self).name_get()
        return [(value.id, "%s: %s" % (value.attribute_id.name, value.name)) for value in self]
