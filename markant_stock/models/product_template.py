from odoo import api, fields, models, registry, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_round
from datetime import datetime, timedelta
import math
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    last_update_cost_price = fields.Datetime('Cost Price Last Updated On')

    @api.onchange('mrp_cost_ok')
    def onchange_mrp_cost_ok(self):
        self.ensure_one()
        super(ProductTemplate, self).onchange_mrp_cost_ok()
        if self.mrp_cost_ok:
            self.configurable_ok = False

    @api.multi
    def write(self, vals):
        if vals.get('mrp_cost_ok'):
            vals['configurable_ok'] = False
        return super(ProductTemplate, self).write(vals)


class ProductProduct(models.Model):
    _inherit = "product.product"

    standard_price = fields.Float(track_visibility='onchange')

    def _compute_reservation_count(self):
        for product in self:
            reservation_count = []
            for move in self.env['stock.move'].search(
                    [('state', 'in', ['confirmed', 'assigned', 'partially_available']),
                     ('product_id', '=', product.id)]):
                if move.reserved_availability > 0:
                    if move.picking_type_id.code == 'outgoing' or \
                            move.picking_type_id.code == 'internal':
                        reservation_count.append(move.picking_id.id)
            product.reservation_count = len(reservation_count)

    reservation_count = fields.Integer(string='# Reservation',
                                       compute='_compute_reservation_count')

    @api.multi
    def write(self, vals):
        res = super(ProductProduct, self).write(vals)
        for prod in self:
            if vals.get('standard_price'):
                prod.last_update_cost_price = fields.Datetime.now()
        return res

    def open_reservation_picking(self):
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        reservation_count = []
        for move in self.env['stock.move'].search(
                [('state', 'in', ['confirmed', 'assigned', 'partially_available']),
                 ('product_id', '=', self.id)]):
            if move.reserved_availability > 0:
                if move.picking_type_id.code == 'outgoing' or \
                        move.picking_type_id.code == 'internal':
                    reservation_count.append(move.picking_id.id)
        action['domain'] = [('id', 'in', reservation_count)]
        return action

    # MARKANT: Development for compute variant cost price
    @api.model
    def _compute_list_of_product_for_cron(self):
        all_product_variant = self.search([])
        product_variant = [product.id for product in all_product_variant if product.bom_count > 0]
        ids = ",".join(str(id) for id in product_variant)
        product_list_compute_cost = self.env['ir.config_parameter']
        product_list_compute_cost.sudo().set_param('product.list.compute.cost', ids)
        auto_compute_cron = self.env.ref('markant_stock.ir_cron_markant_variant_cost_price_computation_auto')
        if auto_compute_cron:
            auto_compute_cron.nextcall = fields.Datetime.now() + timedelta(hours=1)
            auto_compute_cron.numbercall = math.ceil(len(product_variant)/100)
            auto_compute_cron.interval_number = 15
            auto_compute_cron.interval_type = 'minutes'
            auto_compute_cron.active = True

    def _compute_bom_price(self, bom, boms_to_recompute=False):
        self.ensure_one()
        if not bom:
            return 0
        if not boms_to_recompute:
            boms_to_recompute = []
        total = 0
        for opt in bom.routing_id.operation_ids:
            duration_expected = (
                    opt.workcenter_id.time_start +
                    opt.workcenter_id.time_stop +
                    opt.time_cycle)
            total += (duration_expected / 60) * opt.workcenter_id.costs_hour
        for line in bom.bom_line_ids:
            if line._skip_bom_line(self):
                continue

            # Compute recursive if line has `child_line_ids`
            if line.child_bom_id and line.child_bom_id in boms_to_recompute:
                child_total = line.product_id._compute_bom_price(line.child_bom_id, boms_to_recompute=boms_to_recompute)
                total += line.product_id.uom_id._compute_price(child_total, line.product_uom_id) * line.product_qty
            else:
                if line.product_id.bom_count > 0:
                    sub_bom = self.env['mrp.bom']._bom_find(product=line.product_id)
                    sub_line_total = line.product_id._compute_bom_price(sub_bom, boms_to_recompute=boms_to_recompute)
                    total += line.product_id.uom_id._compute_price(sub_line_total, line.product_uom_id) * line.product_qty
                else:
                    total += line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id) * line.product_qty
        return bom.product_uom_id._compute_price(total / bom.product_qty, self.uom_id)

    @api.multi
    def do_change_standard_price(self, new_price, account_id):
        """ Changes the Standard Price of Product and creates an account move accordingly."""
        AccountMove = self.env['account.move']

        quant_locs = self.env['stock.quant'].sudo().read_group([('product_id', 'in', self.ids)], ['location_id'],
                                                               ['location_id'])
        quant_loc_ids = [loc['location_id'][0] for loc in quant_locs]
        locations = self.env['stock.location'].search(
            [('usage', '=', 'internal'), ('company_id', '=', self.env.user.company_id.id), ('id', 'in', quant_loc_ids)])

        product_accounts = {product.id: product.product_tmpl_id.get_product_accounts() for product in self}
        product_journal = self.env["ir.config_parameter"].sudo().get_param("markant_stock.revaluation_posting_journal_id")

        prec = self.env['decimal.precision'].precision_get('Product Price')

        for location in locations:
            for product in self.with_context(location=location.id, compute_child=False).filtered(
                    lambda r: r.valuation == 'real_time'):
                diff = product.standard_price - new_price
                if float_is_zero(diff, precision_digits=prec):
                    raise UserError(_("No difference between the standard price and the new price."))
                if not product_accounts[product.id].get('stock_valuation', False):
                    raise UserError(_(
                        'You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
                if not product_journal:
                    raise UserError(_('You don\'t have any revaluation posting journal configured. You must defined one before processing this!'))
                if not account_id:
                    raise UserError(_(
                        'You don\'t have any Revaluation Account configured. You must defined one before processing this!'))
                qty_available = product.qty_available
                if qty_available:
                    # Accounting Entries
                    if diff * qty_available > 0:
                        debit_account_id = account_id
                        credit_account_id = product_accounts[product.id]['stock_valuation'].id
                    else:
                        debit_account_id = product_accounts[product.id]['stock_valuation'].id
                        credit_account_id = account_id

                    move_vals = {
                        'journal_id': product_journal,
                        'company_id': location.company_id.id,
                        'ref': product.default_code,
                        'line_ids': [(0, 0, {
                            'name': _('%s changed cost from %s to %s - %s') % (
                                self.env.user.name, product.standard_price, new_price, product.display_name),
                            'account_id': debit_account_id,
                            'debit': abs(diff * qty_available),
                            'credit': 0,
                            'product_id': product.id,
                        }), (0, 0, {
                            'name': _('%s changed cost from %s to %s - %s') % (
                                self.env.user.name, product.standard_price, new_price, product.display_name),
                            'account_id': credit_account_id,
                            'debit': 0,
                            'credit': abs(diff * qty_available),
                            'product_id': product.id,
                        })],
                    }
                    move = AccountMove.create(move_vals)
                    move.post()
                    if self._context.get('markant_auto_compute'):
                        if self._context.get('log_line'):
                            log_line = self._context.get('log_line')
                            log_line.write({'journal_entry': move.name})

        self.write({'standard_price': new_price})
        return True


    # This method should be called once a day ( Cron to Compute Cost Price )
    @api.model
    def _cron_compute_cost_price_auto(self):
        with api.Environment.manage():
            ids = self.env['ir.config_parameter'].sudo().get_param('product.list.compute.cost')

            if ids and ids != 'False':
                ids = ids.split(",")
                if len(ids) > 100:
                    to_process = ids[:100]
                    remain = ids[100:]
                else:
                    to_process = ids
                    remain = []

                if remain:
                    ids = ",".join(str(id) for id in remain)
                    product_list_compute_cost = self.env['ir.config_parameter']
                    product_list_compute_cost.sudo().set_param('product.list.compute.cost', ids)
                else:
                    ids = False
                    product_list_compute_cost = self.env['ir.config_parameter']
                    product_list_compute_cost.sudo().set_param('product.list.compute.cost', ids)

                if to_process:
                    product_variant = self.env['product.product'].search([('id', 'in', to_process)])
                    log_obj = self.env['product.variant.compute.price.log']
                    log_lines_obj = self.env['product.variant.compute.price.log.line']
                    log_lines = []
                    log = log_obj.create({
                        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    })
                    account_id = int(self.env["ir.config_parameter"].sudo().get_param("markant_stock.revaluation_account_id"))
                    for product in product_variant:
                        old_price = product.standard_price
                        vals = {
                            'log_id': log.id,
                            'product_id': product.id,
                            'old_price': old_price,
                            'qty_on_hand': product.qty_available,
                        }
                        log_line = log_lines_obj.create(vals)
                        with registry(self.env.cr.dbname).cursor() as new_cr:
                            self._context.update({
                                'markant_auto_compute': True,
                                'log_line': log_line,
                            })
                            new_env = api.Environment(new_cr, self.env.uid, self.env.context)
                            product = product.with_env(new_env)
                            prec = self.env['decimal.precision'].precision_get('Product Price')
                            try:
                                bom_price = product._get_price_from_bom()
                                standard_price = float_round(product.standard_price, precision_digits=prec)
                                new_price = float_round(bom_price, precision_digits=prec)
                                diff = float_round(standard_price - new_price, precision_digits=prec)
                                if not float_is_zero(diff, precision_digits=prec):
                                    if product.valuation == 'real_time':
                                        product.do_change_standard_price(new_price, account_id)
                                        log_line.write({'status': 'Pass'})
                                    else:
                                        product.standard_price = new_price
                                        log_line.write({'status': 'Pass'})
                                else:
                                    log_line.write({'status': 'No Changes'})
                            except Exception as e:
                                new_env.cr.rollback()
                                _logger.info(str(e))
                                log_line.write({'status': 'Fail',
                                                'error_log': str(e)})

                            tot_variance = float_round(product.qty_available * (new_price - old_price), precision_digits=prec)
                            variance = float_round(new_price - old_price, precision_digits=prec)
                            log_line.write({
                                'new_price': new_price,
                                'variance': variance,
                                'total_variance': tot_variance,
                            })
                            new_env.cr.commit()
                        log_lines.append(log_line)
                    log.write({
                        'log_line_ids': [(6, 0, [line.id for line in log_lines])],
                        'total_record': len(log_lines),
                        'record_passed': len([line.id for line in log_lines if line['status'] == 'Pass']),
                        'record_failed': len([line.id for line in log_lines if line['status'] == 'Fail']),
                        'record_no_changes': len([line.id for line in log_lines if line['status'] == 'No Changes'])
                    })
