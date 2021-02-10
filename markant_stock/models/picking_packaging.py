from odoo import api, fields, models, _


class PickingPackaging(models.Model):
    _name = "picking.packaging"
    _description = "Packaging in Picking Form"

    active = fields.Boolean('Active', default=True)
    sequence = fields.Integer(string="Sequence")
    name = fields.Char(string="Name", required=True, copy=False, default='New',
                       readonly=True)
    partner_id = fields.Many2one('res.partner', string='Sender')
    partner_recipient_id = fields.Many2one('res.partner',
                                           string='Recipient')
    packaging_line_ids = fields.One2many('stock.packaging.table',
                                         'code_desc_id',
                                         string='Packaging Table')
    order_id = fields.Many2one('sale.order',
                               string="Order Number",
                               required=True)
    picking_id = fields.Many2one('stock.picking',
                                 string="Pickings",
                                 copy=False)
    warehouse_id = fields.Many2one('stock.warehouse',
                                   string="Stock Warehouse",
                                   required=True)

    @api.onchange('order_id')
    def _onchange_partner(self):
        if self.order_id:
            self.partner_id = self.order_id.partner_id
            self.partner_recipient_id = self.order_id.partner_shipping_id
            self.warehouse_id = self.order_id.warehouse_id

    @api.model
    def default_get(self, fields):
        record_ids = self.env.context.get('active_ids', False)
        res = super(PickingPackaging, self).default_get(fields)
        if record_ids:
            records_obj = self.env['stock.picking'].browse(record_ids)
            sale_id = records_obj.sale_id

        res.update({'picking_id': records_obj.id,
                    'order_id': sale_id.id})
        return res

    @api.model
    def create(self, vals):
        name = self.env['ir.sequence'].next_by_code('picking.packaging')
        vals.update({
            'name': name,
        })
        return super(PickingPackaging, self).create(vals)
