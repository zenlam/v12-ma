# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
from werkzeug.utils import redirect

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from odoo.addons.sale.controllers.portal import CustomerPortal


class MarkantWebsiteSale(CustomerPortal):

    def _show_report(self, model, report_type, report_ref, download=False):
        if model._name == 'sale.order':
            if model.report_to_send == 'so_gross_total':
                report_ref = "markant_sale.action_report_saleorder_markant_gross_total"
            if model.report_to_send == 'so_discount':
                report_ref = "markant_sale.action_report_saleorder_markant_gross_disc_sub_total"
            if model.report_to_send == 'so_sub_total':
                report_ref = "markant_sale.action_report_saleorder_markant_subtotal_only"
        response = super(MarkantWebsiteSale, self)._show_report(model=model, report_type=report_type, report_ref=report_ref, download=download)
        return response
