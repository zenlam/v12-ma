from odoo import api, fields, models, tools, _


class WebshopDeliveryService(models.Model):
    _name = "webshop.product.delivery"
    _description = "Webshop Delivery Service"

    name = fields.Char(string='Name', copy=False, translate=True,
                       required=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'You cant add same delivery service again !'),
    ]
