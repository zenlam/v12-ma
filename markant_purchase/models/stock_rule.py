from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class StockRule(models.Model):
    _inherit = 'stock.rule'

    # Do not run `_run_buy` method from odoo base,
    # as markant call it manually, check `_run_buy_advice` method
    @api.multi
    def _run_buy(self, product_id, product_qty, product_uom, location_id, name,
                 origin, values):
        return True

    # Copy of `_run_buy` from `purchase_stock`
    @api.multi
    def _run_buy_advice(self, product_id, product_qty, product_uom,
                        location_id, name, origin, values):

        values.setdefault('company_id',
                          self.env['res.company']._company_default_get(
                              'procurement.group'))
        values.setdefault('priority', '1')
        values.setdefault('date_planned', fields.Datetime.now())
        rule = self.env['procurement.group']._get_rule(
            product_id, location_id, values)
        if not rule:
            raise UserError(_('No procurement rule found in location "%s" '
                              'for product "%s".\n '
                              'Check routes configuration.') % (
                location_id.display_name, product_id.display_name))
        action = 'pull' if rule.action == 'pull_push' else rule.action
        if action == 'buy':
            self = rule
            cache = {}
            suppliers = product_id.seller_ids\
                .filtered(lambda r: (not r.company_id or r.company_id == values[
                    'company_id']) and (not r.product_id or
                                        r.product_id == product_id))
            if not suppliers:
                msg = _('There is no vendor associated to the product %s. '
                        'Please define a vendor for this product.') % (
                    product_id.display_name,)
                raise UserError(msg)
            supplier = self._make_po_select_supplier(values, suppliers)
            partner = supplier.name
            # we put `supplier_info` in values for extensibility purposes
            values['supplier'] = supplier

            domain = self._make_po_get_domain(values, partner)
            if domain in cache:
                po = cache[domain]
            else:
                po = self.env['purchase.order'].sudo().search([dom for dom in domain])
                po = po[0] if po else False
                cache[domain] = po
            if not po:
                vals = self._prepare_purchase_order(
                    product_id, product_qty, product_uom, origin, values, partner)
                company_id = values.get('company_id') and \
                    values['company_id'].id or self.env.user.company_id.id
                po = self.env['purchase.order'].with_context(
                    force_company=company_id).sudo().create(vals)
                # Make the date_order as today
                po.date_order = fields.Datetime.now()
                cache[domain] = po
            elif not po.origin or origin not in po.origin.split(', '):
                if po.origin:
                    if origin:
                        po.write({'origin': po.origin + ', ' + origin})
                    else:
                        po.write({'origin': po.origin})
                else:
                    po.write({'origin': origin})

            # Create Line
            po_line = False
            for line in po.order_line:
                if line.product_id == product_id and line.product_uom == product_id.uom_po_id:
                    if line._merge_in_existing_line(product_id, product_qty,
                                                    product_uom, location_id,
                                                    name, origin, values):
                        vals = self._update_purchase_order_line(
                            product_id, product_qty, product_uom,
                            values, line, partner)
                        po_line = line.write(vals)
                        break
            if not po_line:
                vals = self._prepare_purchase_order_line(
                    product_id, product_qty, product_uom, values, po, partner)
                self.env['purchase.order.line'].sudo().create(vals)

            # Return Advice Log Item
            return (0, 0, {
                'origin': origin,
                'partner_id': po.partner_id.id,
                'po_id': po.id,
                'product_id': product_id.id,
                'qty': product_qty,
                'uom_id': product_uom.id
            })
