from odoo import api, fields, models, tools, _


class WebshopProductTags(models.Model):
    _name = "webshop.product.tags"
    _description = "Webshop Product Tags"

    name = fields.Char(string='Name', copy=False, translate=True, required=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'You cant add same tag again !'),
    ]
