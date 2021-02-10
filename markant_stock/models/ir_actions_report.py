from odoo import api, fields, models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.multi
    def render_qweb_pdf(self, res_ids=None, data=None):
        if self.model == 'stock.picking':
            if res_ids:
                current_date_time = fields.Datetime.now()
                for rec in self.env[self.model].browse(res_ids):
                    rec.write({
                        'last_print_date': current_date_time,
                        'no_of_print': rec.no_of_print + 1
                    })
        res = super(IrActionsReport, self).render_qweb_pdf(res_ids=res_ids,
                                                           data=data)
        return res
