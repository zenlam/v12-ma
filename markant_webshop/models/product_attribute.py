from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MarkantProductAttribute(models.Model):
    _inherit = 'product.attribute'

    webshop_attribute_id = fields.Many2one('webshop.attribute',
                                           string='Webshop Attribute Name')
    shop = fields.Boolean(string='Shop', default=False, copy=False)


class MarkantProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    def _get_webshop_domain(self):
        params_context = self.env.context.get('params')
        if params_context:
            value_id = params_context.get('id')
            product_attribute_value = self.env['product.attribute.value'].search([('id', '=', value_id)])
            if product_attribute_value.attribute_id and product_attribute_value.attribute_id.webshop_attribute_id:
                ids = self.env['webshop.attribute.value'].search([('attribute_id', '=', product_attribute_value.attribute_id.webshop_attribute_id.id)])
                return [('id', 'in', ids.ids)]

    webshop_attribute_value_id = fields.Many2one('webshop.attribute.value',
                                                 string='Webshop Attribute Value',
                                                 domain=lambda self: self._get_webshop_domain())
    shop = fields.Boolean(string='Shop', default=False, copy=False)

    @api.multi
    def write(self, vals):
        res = super(MarkantProductAttributeValue, self).write(vals)
        for value in self:
            if value.webshop_attribute_value_id and \
                    value.webshop_attribute_value_id.attribute_id != \
                    value.attribute_id.webshop_attribute_id:
                raise ValidationError(_('The webshop attribute value selected '
                                        'does not matched with the webshop '
                                        'attribute!'))
        return res

    @api.model
    def create(self, values):
        res = super(MarkantProductAttributeValue, self).create(values)
        if res.webshop_attribute_value_id and \
                res.webshop_attribute_value_id.attribute_id != \
                res.attribute_id.webshop_attribute_id:
            raise ValidationError(_('The webshop attribute value selected '
                                    'does not matched with the webshop '
                                    'attribute!'))
        return res


class MarkantProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    @api.multi
    def write(self, vals):
        res = super(MarkantProductTemplateAttributeValue, self).write(vals)
        for value in self:
            if vals.get('price_extra'):
                products = self.env['product.product'].search(
                    [('product_tmpl_id', '=', value.product_tmpl_id.id)])
                api_config = self.env['webshop.api.config'].search(
                    [('active', '=', True)], limit=1)
                retries = 0
                if api_config:
                    retries = api_config.api_attempts
                products.with_delay(max_retries=retries)\
                    .webshop_api_product(method='write',
                                         delete=False,
                                         delete_response=False)
        return res
