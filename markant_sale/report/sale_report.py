# -*- coding: utf-8 -*-

from odoo import tools
from odoo import api, fields, models

class SaleOrderReport(models.AbstractModel):
    _name = 'report.sale.report_saleorder'
    _description = 'Markant Sale Report'

    @api.multi
    def _get_report_values(self, docids, data=None):
        docs = self.env['sale.order'].browse(docids)
        return {
            'doc_ids': docs.ids,
            'doc_model': 'sale.order',
            'docs': docs,
        }
