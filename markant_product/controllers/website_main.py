# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class MarkantWebsiteSale(WebsiteSale):
    @http.route(['/shop/product/<model("product.template"):product>'], type='http', auth="user", website=True)
    def product(self, product, category='', search='', **kwargs):
        return request.render('website.404')
