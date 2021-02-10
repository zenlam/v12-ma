from odoo import api, fields, models, _
from odoo.exceptions import Warning


class ReserveSalePicking(models.TransientModel):
    _name = 'reserve.sale.picking'
    _description = 'Reserve Orders / Un-reserve Transfers'

    picking_ids = fields.Many2many('stock.picking', 'unreserve_picking_rel',
                                   'rec1', 'rec2', readonly=True,
                                   string='Do un-reserve following transfers!')
    sale_order_id = fields.Many2one('sale.order', required=True,
                                    domain=[('state', '=', 'sale')],
                                    string='Do reserve following order!')

    @api.multi
    def action_unreserve_and_reserve(self):
        # Un-reserve following pickings
        for picking in self.picking_ids:
            picking.do_unreserve()

        # Reserve following pickings which are related to selected orders
        for picking in self.sale_order_id.picking_ids:
            if picking.show_check_availability:
                picking.action_assign()

        # Check availability again for the same pickings which
        # we un-reserve before...
        #
        # But this time it might be partially reserve...!!
        for picking in self.picking_ids:
            picking.action_assign()
        return True

    @api.model
    def default_get(self, fields):
        record_ids = self.env.context.get('active_ids', False)
        res = super(ReserveSalePicking, self).default_get(fields)
        if record_ids:
            records_obj = self.env['stock.picking'].browse(record_ids)
            for record in records_obj:
                if record.state not in  ('assigned','confirmed'):
                    raise Warning(_('Can only select `Transfers` which '
                                    'are in `Waiting` or `Ready` stage!'))
        res.update({'picking_ids': record_ids})
        return res
