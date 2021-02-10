from odoo import api, fields, models


class StockChangeStandardPrice(models.TransientModel):
    _inherit = 'stock.change.standard.price'
    _description = "Change Standard Price"

    @api.model
    def default_get(self, fields):
        res = super(StockChangeStandardPrice, self).default_get(fields)

        account_id = int(self.env["ir.config_parameter"].sudo().get_param("markant_stock.revaluation_account_id"))
        res.update({
            'counterpart_account_id': account_id
        })
        return res
