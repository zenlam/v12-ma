# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_caln_factor = fields.Boolean(string="Landed Cost Applied",
                                    default=False)
    caln_factor = fields.Float(string="Landed Cost Factor(%)")
    landed_cost_count = fields.Integer(string="Landed Cost Count",
                                       compute='_compute_lcost_count')

    @api.multi
    def write(self, vals):
        """
        Inherit write function to restrict, if one of the picking of the PO is
        validated (completed), then user can no longer change the landed cost
        settings

        Also, we will update the landed cost settings in Picking if these
        settings change in PO (only incoming picking will be updated)

        Validation of caln factor, cannot be negative
        """
        if ('is_caln_factor' in vals) or ('caln_factor' in vals):
            for record in self:
                if vals.get('is_caln_factor',
                            record.is_caln_factor) and vals.get('caln_factor',
                                                                False) < 0:
                    raise UserError(_("Caln Factor can't be Negative!"))
                for picking in record.picking_ids:
                    if picking.state == 'done':
                        raise UserError(_(
                            'You cannot change the landed cost settings '
                            'for Purchase Order with completed deliveries.'))
                    if picking.picking_type_code == 'incoming':
                        picking.is_caln_factor = vals.get(
                            'is_caln_factor', record.is_caln_factor)
                        picking.caln_factor = vals.get(
                            'caln_factor', record.caln_factor)
        res = super(PurchaseOrder, self).write(vals)
        return res

    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        super(PurchaseOrder, self).onchange_partner_id()
        if self.partner_id:
            self.is_caln_factor = self.caln_factor \
                = self.partner_id.landed_cost_factor

    @api.multi
    def _compute_lcost_count(self):
        for record in self:
            self.landed_cost_count = self.env[
                'stock.landed.cost'].search_count(
                [('purchase_order_id', '=', record.id)])

    @api.multi
    def action_view_landed_cost(self):
        self.ensure_one()
        landed_cost_ids = self.env[
            'stock.landed.cost'].search(
            [('purchase_order_id', '=', self.id)])
        action = self.env.ref(
            'stock_landed_costs.action_stock_landed_cost').read()[0]
        action['domain'] = [('id', 'in', landed_cost_ids.ids)]
        return action

    @api.model
    def _prepare_picking(self):
        """
        Inherit this function to pass landed cost fields to Picking when we
        create Picking from PO, based on landed cost settings in PO
        """
        res = super(PurchaseOrder, self)._prepare_picking()
        res.update({'is_caln_factor': self.is_caln_factor,
                    'caln_factor': self.caln_factor})
        return res

    @api.multi
    def button_confirm(self):
        """
        Inherit this function to validate the following fields is configured:
        1) Default Landed Cost Product
        2) Default Landed Cost Journal
        3) Expense Account of the Default Landed Cost Product
        4) Price Difference Account of the Product Category in purchase order line
        """
        if self.is_caln_factor:
            for record in self:
                if not record.company_id.default_caln_factor_product:
                    raise UserError(_(
                        'You have to configure a default Landed'
                        ' Cost Product in settings.'))
                if not record.company_id.default_lcost_journal:
                    raise UserError(_(
                        'You have to configure a '
                        'default Account Journal for landed cost in settings.'))
                if not record.company_id.default_caln_factor_product. \
                        property_account_expense_id:
                    raise UserError(_(
                        'You have to configure a '
                        'expense account for the default landed cost product, %s.')
                                    % record.company_id.
                                    default_caln_factor_product.name)

        return super(PurchaseOrder, self).button_confirm()
