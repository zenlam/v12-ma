# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning
from odoo.addons import decimal_precision as dp
from odoo.tools import pycompat
import base64
from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)

class SaleOrderOption(models.Model):
    _inherit = "sale.order.option"

    product_image = fields.Binary(related='product_id.image_medium',
                                  attachment=True,
                                  readonly=True, string='Product Image')
    product_image_small = fields.Binary(related='product_id.image_small',
                                        attachment=True,
                                        readonly=True, string='Product Image')


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_uom_qty', 'price_unit')
    def _compute_price_gross_total(self):
        for line in self:
            line.price_gross_total = line.price_unit * line.product_uom_qty

    price_gross_total = fields.Float(compute='_compute_price_gross_total', string='Gross Total', readonly=True, store=True, digits=dp.get_precision('Product Price'))
    is_project_discount_line = fields.Boolean()
    is_min_admin_cost_rule_line = fields.Boolean()
    is_montage_install_rule_line = fields.Boolean()

    margin_in_per = fields.Float(compute='_product_margin_percentage', digits=dp.get_precision('Product Price'))

    # Obsolete Product Checking
    order_qty_after_confirm_obsolete = fields.Integer(
        string='Qty saved after confirmation', default=0)


    @api.depends('margin')
    def _product_margin_percentage(self):
        for line in self:
            currency = line.order_id.pricelist_id.currency_id
            price = line.purchase_price
            if line.price_subtotal and line.product_uom_qty:
                revenue = line.price_subtotal / line.product_uom_qty
                line.margin_in_per = currency.round(((revenue-line.purchase_price)/revenue)*100)
            else:
                line.margin_in_per = 0.0

    @api.multi
    def write(self, vals):
        res = super(SaleOrderLine, self).write(vals)

        order_ids = []
        if self.env.context.get('markant_manual_sequence_change') is None:
            for record in self:
                if record.order_id not in order_ids:
                    order_ids.append(record.order_id)

        if order_ids:
            for order in order_ids:
                order_lines = order.order_line
                max_sequence = max(order_lines.mapped('sequence'))
                max_sequence += 1
                pd_order_line = order_lines.filtered(lambda ol: ol.is_project_discount_line)
                admin_order_line = order_lines.filtered(lambda ol: ol.is_min_admin_cost_rule_line)
                mont_install_order_line = order_lines.filtered(lambda ol: ol.is_montage_install_rule_line)
                if pd_order_line:
                    pd_order_line.with_context(markant_manual_sequence_change=True).sequence = max_sequence
                    max_sequence += 1
                if admin_order_line:
                    admin_order_line.with_context(markant_manual_sequence_change=True).sequence = max_sequence
                    max_sequence += 1
                if mont_install_order_line:
                    mont_install_order_line.with_context(markant_manual_sequence_change=True).sequence = max_sequence

        return res

    @api.model
    def create(self, values):
        res = super(SaleOrderLine, self).create(values)
        res.delivery_date = res.order_id.commitment_date
        res.delivery_option = res.order_id.delivery_option
        if res.order_id.delivery_option == 'partial':
            res.allow_partial = True
        else:
            res.allow_partial = False
        return res

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # @api.multi
    # @api.onchange('partner_id')
    # def onchange_partner_id(self):
    #     res = super(SaleOrder, self).onchange_partner_id()
    #     if not res:
    #         res = {}
    #     if not res.get('domain', False):
    #         res['domain'] = {}
    #     partners_invoice = []
    #     partners_shipping = []
    #     domain = {}
    #     if self.partner_id:
    #         sub_partner_ids = [self.partner_id.id]
    #         if self.partner_id.child_ids:
    #             for child in self.partner_id.child_ids:
    #                 sub_partner_ids.append(child.id)
    #         if self.partner_id.child_ids_address:
    #             for child_adds in self.partner_id.child_ids_address:
    #                 sub_partner_ids.append(child_adds.id)
    #         res['domain']['partner_invoice_id'] =  [('id', 'in', sub_partner_ids)]
    #         res['domain']['partner_shipping_id'] =  [('id', 'in', sub_partner_ids)]
    #     else:
    #         res['domain']['partner_invoice_id'] =  [('id', 'in', [0])]
    #         res['domain']['partner_shipping_id'] =  [('id', 'in', [0])]
    #     return res

    @api.depends('order_line.price_gross_total')
    def _amount_all_sale_markant(self):
        for order in self:
            amount_gross_total = amount_discount_total = amount_subtotal_total = amount_project_disc_total = amount_installation_total = amount_admin_total = 0.0
            pd_order_line = order.order_line.filtered(lambda ol: ol.is_project_discount_line)
            admin_order_line = order.order_line.filtered(lambda ol: ol.is_min_admin_cost_rule_line)
            mont_install_order_line = order.order_line.filtered(lambda ol: ol.is_montage_install_rule_line)
            for line in order.order_line:
                if line.is_project_discount_line:
                    continue
                if line.is_min_admin_cost_rule_line:
                    continue
                if line.is_montage_install_rule_line:
                    continue
                amount_gross_total += line.price_gross_total
                amount_discount_total += line.price_gross_total - line.price_subtotal

            for line in pd_order_line:
                amount_project_disc_total += line.price_unit

            for line in admin_order_line:
                amount_admin_total += line.price_unit

            for line in mont_install_order_line:
                amount_installation_total += line.price_unit

            order.update({
                'amount_gross_total': amount_gross_total,
                'amount_discount_total': amount_discount_total,
                'amount_subtotal_total': amount_gross_total - amount_discount_total,
                'amount_project_disc_total': amount_project_disc_total,
                'amount_installation_total': amount_installation_total,
                'amount_admin_total': amount_admin_total,
            })

    @api.model
    def get_default_note(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'sale.use_sale_note') and self.env.user.company_id.sale_notes or ''

    amount_gross_total = fields.Monetary(string='Gross Total', store=True, readonly=True, compute='_amount_all_sale_markant')
    amount_discount_total = fields.Monetary(string='Total Disc Lines', store=True, readonly=True, compute='_amount_all_sale_markant')
    amount_subtotal_total = fields.Monetary(string='Sum of Subtotal', store=True, readonly=True, compute='_amount_all_sale_markant')
    amount_project_disc_total = fields.Monetary(string='Project Discount', store=True, readonly=True, compute='_amount_all_sale_markant')
    amount_installation_total = fields.Monetary(string='Installation', store=True, readonly=True, compute='_amount_all_sale_markant')
    amount_admin_total = fields.Monetary(string='Administration', store=True, readonly=True, compute='_amount_all_sale_markant')


    is_project_discount = fields.Boolean(string="Apply Project Discount")
    project_discount_type = fields.Selection([('percentage', 'Percentage'), ('fix_amount', 'Fixed Amount')], string="Discount Type")
    project_discount_amount = fields.Float(string='Percentage/Amount')
    project_discount_apply_on = fields.Selection([
        ('sum_of_subtotal','Sum of Subtotal (excl Admin and Installation)'),
        ('sum_of_gross_total','Sum of Gross Total (excl Admin & Installation)')
    ], string="Apply On")


    is_min_admin_cost_rule = fields.Boolean(string="Apply Min Administration Cost Rule", default=True)
    admin_cost_rule_min_amount = fields.Float(string="Minimum Amount", default=lambda self: self.env["ir.config_parameter"].sudo().get_param("sale.admin_cost_default_min_amount"))
    admin_cost_rule_admin_amount = fields.Float(string='Admin Charges', default=lambda self: self.env["ir.config_parameter"].sudo().get_param("sale.admin_cost_default_admin_amount"))
    admin_cost_rule_apply_on = fields.Selection([
        ('sum_of_subtotal','Sum of Subtotal (excl Admin and Installation)'),
        ('sum_of_gross_total','Sum of Gross Total (excl Admin & Installation)')
    ], string="Apply On")

    is_montage_install_rule = fields.Boolean(string="Apply Installation Cost")
    montage_install_rule_id = fields.Many2one('montage.installation.rule', string="Delivery & Installation")
    montage_install_multiple_of = fields.Float(string='Multiple of', default=1.0)
    montage_install_level_of_floor = fields.Integer(string='Level of Floor')
    montage_install_rule_price = fields.Float(string='Montage Installation Price', readonly=True, copy=False)
    montage_install_rule_message = fields.Char(readonly=True, copy=False)

    carrier_name_id = fields.Many2one('carrier', string='Carrier', copy=False)
    terms_note = fields.Html('Terms and conditions', default=get_default_note)

    commitment_date = fields.Datetime('Commitment Date', readonly=False,
                                      track_visibility='onchange')

    contact_person_id = fields.Many2one('res.users', string='Markant Contact Person', default=lambda self: self.env.user)

    # Installation Form Link
    installation_form_ids = fields.Many2many('markant.installation.form',
                                             'installation_form_sale_rel',
                                             'form_id', 'order_id',
                                             string='Installation Forms')
    installation_checked = fields.Boolean(string='Carrier Installation',
                                          default=False,
                                          copy=False)
    inst_from_proposed_date = fields.Datetime(string='Proposed Date', copy=False)
    inst_to_proposed_date = fields.Datetime(string='Proposed Date',
                                            copy=False)
    inst_from_planned_date = fields.Datetime(string='Planned Date', copy=False)
    inst_to_planned_date = fields.Datetime(string='To', copy=False)
    inst_survey_date = fields.Date(string='Survey Date')
    inst_survey_id = fields.Many2one('survey', string='Survey Form')
    inst_survey_necessary = fields.Selection([('yes', 'Yes'),
                                              ('no', 'No'),
                                              ('na', 'Not applicable')],
                                             string='Survey Necessary')
    inst_staircase_avail = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                            string='Staircase Available')
    inst_lift_available = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                           string='Lift Available')
    inst_distance_place_unloading = fields.Integer(
        string='Distance to Place of Unloading (in Meter)')
    inst_any_empty_clean_zone = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                                 string='Empty/Clean '
                                                        'rooms available')
    inst_total_number_floors = fields.Integer(string='Total Number of Floors')
    inst_floor_of_installation = fields.Integer(string='Floor of installation')
    inst_site_drawing_avail = fields.Selection([('yes', 'Yes'),
                                                ('no', 'No')],
                                               string='Site Drawing Necessary')
    inst_drawing_included = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                             string='Drawing Included')
    inst_pre_assembly = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                         string='Pre Assembly')
    inst_back_order = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                       string='Back Order')
    inst_note = fields.Html(string='Comment')
    inst_installation_type_id = fields.Many2one('markant.installation.type',
                                                string='Type')
    installation_count = fields.Integer(string='Installation Forms',
                                        compute='_compute_installation_ids')
    calculation_type_id = fields.Many2one('markant.calculation.type',
                                          string='Calculation')
    inst_require_initial_so = fields.Boolean(string="Require Initial SO")
    inst_initial_so_id = fields.Many2one('sale.order', string='Initial SO',
                                         copy=False)

    # Override from base to change the logic
    @api.onchange('partner_shipping_id')
    def _onchange_partner_shipping_id(self):
        for picking in self.picking_ids.filtered(
                lambda p: p.state not in ['done', 'cancel'] and
                          p.partner_id != self.partner_shipping_id):
            if picking.picking_type_id.is_delivery_order:
                picking.write({
                    'partner_id': self.partner_shipping_id.id
                })
            # res['warning'] = {
            #     'title': _('Warning!'),
            #     'message': _(
            #         'Do not forget to change the partner on the following delivery orders: %s'
            #     ) % (','.join(pickings.mapped('name')))
            # }

    @api.onchange('inst_installation_type_id')
    def _onchange_installation_type_id(self):
        if self.inst_installation_type_id:
            self.inst_require_initial_so = \
                self.inst_installation_type_id.require_initial_so
        else:
            self.inst_require_initial_so = False

    @api.onchange('inst_require_initial_so')
    def _onchange_require_initial_so(self):
        if not self.inst_require_initial_so:
            self.inst_initial_so_id = False

    @api.onchange('departure_time', 'arrival_time')
    def onchange_arrival_departure_time(self):
        if self.departure_time and not self.arrival_time:
            self.departure_time = False
            return {
                'warning': {'title': _('Warning!'),
                            'message': _('Arrival Time is missing!')}
            }
        # if (self.arrival_time and self.departure_time) and \
        #         (self.departure_time < self.arrival_time):
        #     self.departure_time = False
        #     return {
        #         'warning': {'title': _('Warning!'),
        #                     'message': _('Departure Time should always '
        #                                  'greater than Arrival Time.')}
        #     }

    @api.depends('installation_form_ids')
    def _compute_installation_ids(self):
        for order in self:
            order.installation_count = len(order.installation_form_ids)

    @api.multi
    def action_view_installation(self):
        action = self.env.ref('markant_installation.action_markant_installation_form').read()[0]

        installations = self.mapped('installation_form_ids')
        if len(installations) > 1:
            action['domain'] = [('id', 'in', installations.ids)]
        elif installations:
            form_view = [(self.env.ref('markant_installation.view_installation_form_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in
                                               action['views'] if
                                               view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = installations.id
        return action

    def get_installation_form_email(self):
        installation = self.env['markant.installation.form'].search([])
        records =[]
        for ins in installation:
            inst = {}
            for sale in ins.sale_order_ids:
                if sale.id == self.id:
                    inst['id'] = ins.id
                    inst['name'] = ins.name
                    records.append(inst)
        return records

    @api.multi
    def action_send_mail_notification_installation(self):
        self.ensure_one()
        email_to = self.env.user.company_id.inst_notification_email
        template = self.env.ref(
            'markant_sale.email_template_cancelled_so_link_installation')

        if email_to:
            template.send_mail(self.id, force_send=True,
                               email_values={'email_to': email_to})
        return True

    @api.multi
    def action_cancel(self):
        """
        Inherit cancel button, to cancel the origin picking when this negative
        SO is cancelled. But not allow to cancel this negative SO if the
        origin picking is validated.
        """
        res = super(SaleOrder, self).action_cancel()
        for so in self:
            so.action_send_mail_notification_installation()
            cancel_stage = self.env['markant.installation.stage'].search([('cancel_stage', '=', True)])
            for installation in so.installation_form_ids:
                if cancel_stage:
                    installation.write({
                        'stage_id': cancel_stage.id
                    })
                else:
                    raise Warning(_('There are installation forms linked to this SO but there are no cancellation stage being defined in Installation Stages!'))
        return res

    @api.onchange('carrier_name_id')
    def _onchange_installation_tab(self):
        if self.carrier_name_id and self.carrier_name_id.installation_link:
            self.installation_checked = True
        else:
            self.installation_checked = False

    @api.onchange('montage_install_rule_id', 'montage_install_multiple_of', 'montage_install_level_of_floor')
    def _onchange_montage_fields(self):
        self.montage_install_rule_price = 0.0
        self.montage_install_rule_message = False


    @api.multi
    def get_montage_installation_price(self):
        for record in self:
            rule_id = record.montage_install_rule_id
            montage_price = 0.0
            so_gross_amount = record.amount_gross_total
            if rule_id.condition == 'fixed_price':
                rule_price = rule_id.price
                if record.montage_install_level_of_floor >= 1:
                    rule_price += rule_id.charges_level
                montage_price = rule_price * record.montage_install_multiple_of

                record.montage_install_rule_price = montage_price
                if montage_price > 0.0:
                    record.montage_install_rule_message = None
                else:
                    record.montage_install_rule_message = 'Cost Computed but due to wrong configuration it look like zero.'
            else:
                pricing_rule_match = False
                for pricing_rule in rule_id.mont_install_pricing_rule_ids:
                    if (so_gross_amount > pricing_rule.price_more_than) and (so_gross_amount <= pricing_rule.price_less_than_eqto):
                        pricing_rule_match = pricing_rule
                        break
                if rule_id.get_rate == 'percentage':
                    get_rate_percentage = 0.0
                    if pricing_rule_match:
                        get_rate_percentage = pricing_rule_match.value
                        if record.montage_install_level_of_floor >= 1:
                            get_rate_percentage += rule_id.charges_level
                        montage_price = (record.amount_gross_total * get_rate_percentage)/ 100.00
                        montage_price = montage_price * record.montage_install_multiple_of
                        record.montage_install_rule_price = montage_price
                        if montage_price > 0.0:
                            record.montage_install_rule_message = None
                        else:
                            record.montage_install_rule_message = 'Cost Computed but due to wrong configuration it look like zero.'
                    else:
                        record.montage_install_rule_price = montage_price
                        record.montage_install_rule_message = 'No Price rule matching this order, cost cannot be computed.'
                else:
                    if pricing_rule_match:
                        rule_price = pricing_rule_match.value
                        if record.montage_install_level_of_floor >= 1:
                            rule_price += rule_id.charges_level
                        montage_price = rule_price * record.montage_install_multiple_of
                        record.montage_install_rule_price = montage_price
                        if montage_price > 0.0:
                            record.montage_install_rule_message = None
                        else:
                            record.montage_install_rule_message = 'Cost Computed but due to wrong configuration it look like zero.'
                    else:
                        record.montage_install_rule_price = montage_price
                        record.montage_install_rule_message = 'No Price rule matching this order, cost cannot be computed.'

            mir_order_line = record.order_line.filtered(lambda ol: ol.is_montage_install_rule_line)
            if mir_order_line:
                resp = mir_order_line.unlink()

    @api.one
    @api.constrains('project_discount_amount')
    def _check_project_discount_amount(self):
        if self.is_project_discount:
            if self.project_discount_type == 'percentage':
                if self.project_discount_amount > 100:
                    raise Warning(_('Percentage, the number keyed‐in in this field cannot be >100'))
            elif self.project_discount_type == 'fix_amount':
                if self.project_discount_amount > self.amount_total:
                    raise Warning(_('Fixed Amount, the number keyed‐in in this field cannot be > Total Amount of the Sales Order.'))

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        if res.apply_order_cycle and res.sale_order_cycle_id:
            cycle_name = res.sale_order_cycle_id.name + "/"
            if cycle_name not in res.name:
                resp = res.with_context(only_name_write_again=True).write({'name': cycle_name + res.name, 'sale_order_cycle_prefix': cycle_name})
        if res.is_project_discount:
            res.update_project_discount()
        if res.is_min_admin_cost_rule:
            res.update_min_admin_cost_rule()

        if res.inst_from_proposed_date and not res.inst_to_proposed_date:
            raise Warning(_('Proposed To Date & Time is missing!'))
        elif not res.inst_from_proposed_date and res.inst_to_proposed_date:
            raise Warning(_('Proposed From Date & Time is missing!'))

        if res.inst_from_planned_date and not res.inst_to_planned_date:
            raise Warning(_('Planned To Date & Time is missing!'))
        elif not res.inst_from_planned_date and res.inst_to_planned_date:
            raise Warning(_('Planned From Date & Time is missing!'))

        if res.inst_to_planned_date < res.inst_from_planned_date:
            raise Warning(_('Planned From date & time should always '
                            'be greater than Planned To.'))
        elif res.inst_to_proposed_date < res.inst_from_proposed_date:
            raise Warning(_('Proposed From date & time should always '
                            'be greater than Proposed To.'))

        return res

    @api.multi
    def write(self, vals):
        self = self.with_context(from_so=True)
        check = {}
        discount_before = 0
        for record in self:
            if record.obsolete:
                if not self.env.context.get(
                        '123skip_obsolete') and not self.env.context.get('from_do'):
                    if record.state == 'sale':
                        product = []
                        for line in record.order_line:
                            if line.product_id.obsolete_product:
                                product.append(line.product_id)
                        if product:
                            for p in set(product):
                                forecast = p.qty_signed_total
                                if p not in check:
                                    check.update({
                                        p.id: forecast
                                    })
            discount_before = record.amount_project_disc_total
        res = super(SaleOrder, self).write(vals)
        if self.env.context.get("only_name_write_again") is not None:
            return res
        for record in self:
            record_name = record.name
            if self.sale_order_cycle_id:
                cycle_name = self.sale_order_cycle_id.name + "/"
                to_process = True
                if self.sale_order_cycle_prefix:
                    if cycle_name != self.sale_order_cycle_prefix:
                        record_name = record_name.replace(self.sale_order_cycle_prefix, cycle_name, 1)
                        resp = record.with_context(only_name_write_again=True).write({'name': record_name , 'sale_order_cycle_prefix': cycle_name})
                        to_process = False
                if to_process:
                    record_name = record_name
                    if cycle_name not in record_name:
                        record_name = cycle_name + record_name
                        resp = record.with_context(only_name_write_again=True).write({'name': record_name, 'sale_order_cycle_prefix':cycle_name})
            elif self.sale_order_cycle_prefix:
                if self.sale_order_cycle_prefix in record_name:
                    record_name = record_name.replace(self.sale_order_cycle_prefix, "", 1)
                    resp = record.with_context(only_name_write_again=True).write({'name': record_name, 'sale_order_cycle_prefix': ""})

        if vals.get('is_project_discount') is not None or vals.get('project_discount_type', False) or vals.get('project_discount_amount') or vals.get('project_discount_apply_on'):
            if self.env.context.get('no_update_project_discount') is None:
                for record in self:
                    record.update_project_discount()
        if vals.get('is_min_admin_cost_rule') is not None or vals.get('admin_cost_rule_min_amount', False) or vals.get('admin_cost_rule_admin_amount') or vals.get('admin_cost_rule_apply_on'):
            if self.env.context.get('no_update_min_admin_cost_rule') is None:
                for record in self:
                    record.update_min_admin_cost_rule()
        for record in self:
            record.update_montage_install_cost_line()
            if record.state in ['sent', 'disc_approv', 'sale']:
                if discount_before != record.amount_project_disc_total:
                    raise UserError(_(
                        "You cannot change Project Discount line in this stage."))

            if record.obsolete:
                if not self.env.context.get('skip_obsolete') and not self.env.context.get('from_do'):
                    if record.state == 'sale':
                        product = []
                        for line in record.order_line:
                            if line.product_id.obsolete_product:
                                product.append(line.product_id)
                        if product:
                            for p in set(product):
                                forecast = 0
                                for order in record.order_line.filtered(
                                        lambda x: x.product_id == p):
                                    for ck, cv in check.items():
                                        if ck == order.product_id.id:
                                            forecast = cv
                                    qty = order.product_uom_qty - order.order_qty_after_confirm_obsolete
                                    if qty > 0:
                                        if qty <= forecast:
                                            order.order_qty_after_confirm_obsolete += qty
                                            forecast -= qty
                                        else:
                                            if forecast > 0:
                                                order.order_qty_after_confirm_obsolete += forecast

            if record.inst_from_proposed_date and not record.inst_to_proposed_date:
                raise Warning(_('Proposed To Date & Time is missing!'))
            elif not record.inst_from_proposed_date and record.inst_to_proposed_date:
                raise Warning(_('Proposed From Date & Time is missing!'))

            if record.inst_from_planned_date and not record.inst_to_planned_date:
                raise Warning(_('Planned To Date & Time is missing!'))
            elif not record.inst_from_planned_date and record.inst_to_planned_date:
                raise Warning(_('Planned From Date & Time is missing!'))

            if record.inst_to_planned_date < record.inst_from_planned_date:
                raise Warning(_('Planned From date & time should always '
                                'be greater than Planned To.'))
            elif record.inst_to_proposed_date < record.inst_from_proposed_date:
                raise Warning(_('Proposed From date & time should always '
                                'be greater than Proposed To.'))

        return res

    @api.multi
    def calculate_obsolete_qty_after(self):
        for record in self:
            if record.obsolete:
                if not self.env.context.get('skip_obsolete'):
                    if record.state == 'sale':
                        product = []
                        for line in record.order_line:
                            if line.product_id.obsolete_product:
                                product.append(line.product_id)
                        if product:
                            for p in set(product):
                                forecast = p.qty_signed_total
                                for order in record.order_line.filtered(
                                        lambda x: x.product_id == p):
                                    qty = order.product_uom_qty - order.order_qty_after_confirm_obsolete
                                    if qty > 0:
                                        if qty <= forecast:
                                            order.order_qty_after_confirm_obsolete += qty
                                            forecast -= qty
                                        else:
                                            if forecast > 0:
                                                order.order_qty_after_confirm_obsolete += forecast
                                    if qty < 0:
                                        order.order_qty_after_confirm_obsolete += qty

    def check_so_obsolete_product(self):
        for record in self:
            obsolete_warning = False
            msg = record.name + '\n\nThe following obsolete products in Sales Order Lines has exceed the available qty of the system : \n\n'
            if record.state != 'sale':
                product_checking = {}
                for line in record.order_line:
                    if line.product_id.obsolete_product:
                        if line.product_id not in product_checking:
                            product_checking.update({
                                line.product_id: line.product_uom_qty
                            })
                        else:
                            for ck, cv in product_checking.items():
                                if line.product_id.id == ck.id:
                                    product_checking[ck] += line.product_uom_qty

                for ck, cv in product_checking.items():
                    if ck.qty_signed_total < cv:
                        obsolete_warning = True
                        if ck.default_code:
                            msg += '[ ' + ck.default_code + ' ] ' + ck.name + ' ( Available Qty: ' + str(
                                ck.qty_signed_total) + ' , Total Sold in SO Line: ' + str(cv) + ' )\n\n'
                        else:
                            msg += ck.name + ' ( Available Qty: ' + str(
                                ck.qty_signed_total) + ' , Total Sold in SO Line: ' + str(cv) + ' )\n\n'
            else:
                product_checking = {}
                for line in record.order_line:
                    if line.product_id.obsolete_product:
                        if line.product_uom_qty > line.order_qty_after_confirm_obsolete:
                            if line.product_id not in product_checking:
                                qty = line.product_uom_qty - line.order_qty_after_confirm_obsolete
                                product_checking.update({
                                    line.product_id: qty
                                })
                            else:
                                for ck, cv in product_checking.items():
                                    qty = line.product_uom_qty - line.order_qty_after_confirm_obsolete
                                    if line.product_id.id == ck.id:
                                        product_checking[
                                            ck] += qty

                for ck, cv in product_checking.items():
                    if ck.qty_signed_total < cv:
                        obsolete_warning = True
                        if ck.default_code:
                            msg += '[ ' + ck.default_code + ' ] ' + ck.name + ' ( Available Qty: ' + str(
                                ck.qty_signed_total) + ' , Total Sold in SO Line: ' + str(
                                cv) + ' )\n\n'
                        else:
                            msg += ck.name + ' ( Available Qty: ' + str(
                                ck.qty_signed_total) + ' , Total Sold in SO Line: ' + str(
                                cv) + ' )\n\n'

            return obsolete_warning, msg

    def update_montage_install_cost_line(self):
        # add line using add to order , but user untick then we need to remove using code
        if not self.is_montage_install_rule:
            if self.state not in ['sale', 'done', 'cancel']:
                mir_order_line = self.order_line.filtered(lambda ol: ol.is_montage_install_rule_line)
                if mir_order_line:
                    resp = mir_order_line.unlink()

    def update_project_discount(self):
        project_discount_product = self.env['ir.config_parameter'].sudo().get_param('sale.project_disc_default_product_id')
        if not project_discount_product:
            raise UserError(_('Please Configure the Project Discount Product from Sale settings.'))
        try:
            project_discount_product = self.env['product.product'].browse(int(project_discount_product))
            if not project_discount_product:
                raise UserError(_('Please Configure the Project Discount Product from Sale settings.'))
        except Exception as e:
            raise UserError(_('Please Configure the Project Discount Product from Sale settings.'))


        if self.is_project_discount:
            match_project_discount_line = self.order_line.filtered(lambda ol: ol.is_project_discount_line)
            if match_project_discount_line:
                if len(match_project_discount_line) > 1:
                    raise UserError(_('More then one line found with project discount product so remove other ones.'))
                else:
                    line_name = project_discount_product.name + " - " + str(self.project_discount_amount)
                    line_price_unit = 0.0
                    if self.project_discount_type == 'percentage':
                        line_name +=  "%"
                        if self.project_discount_apply_on == 'sum_of_subtotal':
                            line_price_unit = -((self.project_discount_amount * self.amount_subtotal_total)/100.00)
                        elif self.project_discount_apply_on == 'sum_of_gross_total':
                            line_price_unit = -((self.project_discount_amount * self.amount_gross_total)/100.00)
                    elif self.project_discount_type == 'fix_amount':
                        line_price_unit = -self.project_discount_amount
                    vals = {'name': line_name,
                            'product_id': project_discount_product.id,
                            'product_uom_qty': 1,
                            'product_uom': project_discount_product.uom_id.id,
                            'price_unit': line_price_unit}
                    resp = match_project_discount_line.write(vals)

            else:
                line_name = project_discount_product.name + " - " + str(self.project_discount_amount)
                line_price_unit = 0.0
                if self.project_discount_type == 'percentage':
                    line_name +=  "%"
                    if self.project_discount_apply_on == 'sum_of_subtotal':
                        line_price_unit = -((self.project_discount_amount * self.amount_subtotal_total)/100.00)
                    elif self.project_discount_apply_on == 'sum_of_gross_total':
                        line_price_unit = -((self.project_discount_amount * self.amount_gross_total)/100.00)
                elif self.project_discount_type == 'fix_amount':
                    line_price_unit = -self.project_discount_amount

                vals = {'order_line': [(0, 0, {
                    'name': line_name,
                    'product_id': project_discount_product.id,
                    'product_uom_qty': 1,
                    'product_uom': project_discount_product.uom_id.id,
                    'price_unit': line_price_unit,
                    'is_project_discount_line': True,
                    'sequence': 997,
                })]}
                resp = self.with_context(no_update_project_discount=True).write(vals)
        else:
            project_discount_order_line = self.order_line.filtered(lambda ol: ol.is_project_discount_line)
            if project_discount_order_line:
                resp = project_discount_order_line.unlink()

    def update_min_admin_cost_rule(self):
        minadmin_discount_product = self.env['ir.config_parameter'].sudo().get_param('sale.admin_cost_default_product_id')
        if not minadmin_discount_product:
            raise UserError(_('Please Configure the Administration Cost Discount Product from Sale settings.'))
        try:
            minadmin_discount_product = self.env['product.product'].browse(int(minadmin_discount_product))
            if not minadmin_discount_product:
                raise UserError(_('Please Configure the Administration Cost Discount Product from Sale settings.'))
        except Exception as e:
            raise UserError(_('Please Configure the Administration Cost Discount Product from Sale settings.'))


        if self.is_min_admin_cost_rule:
            match_discount_line = self.order_line.filtered(lambda ol: ol.is_min_admin_cost_rule_line)
            if match_discount_line:
                if len(match_discount_line) > 1:
                    raise UserError(_('More then one line found with project Admin Discount product so remove other ones.'))
                else:
                    line_name = minadmin_discount_product.name + " - " + str(self.admin_cost_rule_admin_amount)
                    line_price_unit = 0.0
                    need_to_add = False
                    if self.admin_cost_rule_apply_on == 'sum_of_subtotal':
                        if self.amount_subtotal_total < self.admin_cost_rule_min_amount:
                            need_to_add = True
                            line_price_unit = self.admin_cost_rule_admin_amount
                    elif self.admin_cost_rule_apply_on == 'sum_of_gross_total':
                        if self.amount_gross_total < self.admin_cost_rule_min_amount:
                            need_to_add = True
                            line_price_unit = self.admin_cost_rule_admin_amount
                    if need_to_add:
                        vals = {'name': line_name,
                                'product_id': minadmin_discount_product.id,
                                'product_uom_qty': 1,
                                'product_uom': minadmin_discount_product.uom_id.id,
                                'price_unit': line_price_unit}
                        resp = match_discount_line.write(vals)
                    else:
                        discount_order_line = self.order_line.filtered(lambda ol: ol.is_min_admin_cost_rule_line)
                        if discount_order_line:
                            resp = discount_order_line.unlink()
            else:
                line_name = minadmin_discount_product.name + " - " + str(self.admin_cost_rule_admin_amount)
                line_price_unit = 0.0
                need_to_add = False
                if self.admin_cost_rule_apply_on == 'sum_of_subtotal':
                    if self.amount_subtotal_total < self.admin_cost_rule_min_amount:
                        need_to_add = True
                        line_price_unit = self.admin_cost_rule_admin_amount
                elif self.admin_cost_rule_apply_on == 'sum_of_gross_total':
                    if self.amount_gross_total < self.admin_cost_rule_min_amount:
                        need_to_add = True
                        line_price_unit = self.admin_cost_rule_admin_amount
                if need_to_add:
                    vals = {'order_line': [(0, 0, {
                        'name': line_name,
                        'product_id': minadmin_discount_product.id,
                        'product_uom_qty': 1,
                        'product_uom': minadmin_discount_product.uom_id.id,
                        'price_unit': line_price_unit,
                        'is_min_admin_cost_rule_line': True,
                        'sequence': 998,
                    })]}
                    resp = self.with_context(no_update_min_admin_cost_rule=True).write(vals)
        else:
            discount_order_line = self.order_line.filtered(lambda ol: ol.is_min_admin_cost_rule_line)
            if discount_order_line:
                resp = discount_order_line.unlink()

    def set_montage_installation_price(self):
        if self.is_montage_install_rule:
            if not self.montage_install_rule_message and self.montage_install_rule_price and self.montage_install_rule_id:
                service_product_id = self.montage_install_rule_id.service_product_id
                match_line = self.order_line.filtered(lambda ol: ol.is_montage_install_rule_line)
                if match_line:
                    vals = {
                        'name': service_product_id.name,
                        'product_id': service_product_id.id,
                        'product_uom_qty': 1,
                        'product_uom': service_product_id.uom_id.id,
                        'price_unit': self.montage_install_rule_price,
                        'is_montage_install_rule_line': True,
                        'sequence': 999,
                    }
                    resp = match_line.with_context(no_update_montage_installation_rule=True).write(vals)
                else:
                    vals = {'order_line': [(0, 0, {
                        'name': service_product_id.name,
                        'product_id': service_product_id.id,
                        'product_uom_qty': 1,
                        'product_uom': service_product_id.uom_id.id,
                        'price_unit': self.montage_install_rule_price,
                        'is_montage_install_rule_line': True,
                        'sequence': 999,
                    })]}
                    resp = self.with_context(no_update_montage_installation_rule=True).write(vals)
            else:
                mir_order_line = self.order_line.filtered(lambda ol: ol.is_montage_install_rule_line)
                if mir_order_line:
                    resp = mir_order_line.unlink()
        else:
            mir_order_line = self.order_line.filtered(lambda ol: ol.is_montage_install_rule_line)
            if mir_order_line:
                resp = mir_order_line.unlink()


    # project discount Approval
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('draft_disc_approv', 'Pending Discount Approval'),
        ('disc_rej', 'Discount Rejected'),
        ('disc_approv', 'Discount Approved'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ])

    @api.multi
    def action_submit_aprroval(self):
        self.ensure_one()
        self.state = 'draft_disc_approv'

    @api.multi
    def action_pd_approve(self):
        self.ensure_one()
        self.state = 'disc_approv'

    @api.multi
    def action_pd_reject(self):
        self.ensure_one()
        self.state = 'disc_rej'


    @api.multi
    def action_draft(self):
        orders = self.filtered(lambda s: s.state in ['cancel', 'sent'])
        resp = orders.write({
            'is_project_discount': False,
        })
        return super(SaleOrder, self).action_draft()

    @api.multi
    def print_quotation(self):
        self.filtered(lambda s: s.state in ['draft','disc_approv']).write({'state': 'sent'})
        if self.report_to_send == 'so_gross_total':
            return self.env.ref('markant_sale.action_report_saleorder_markant_gross_total') \
                .with_context({'discard_logo_check': True}).report_action(self)
        if self.report_to_send == 'so_discount':
            return self.env.ref('markant_sale.action_report_saleorder_markant_gross_disc_sub_total') \
                .with_context({'discard_logo_check': True}).report_action(self)
        if self.report_to_send == 'so_sub_total':
            return self.env.ref('markant_sale.action_report_saleorder_markant_subtotal_only') \
                .with_context({'discard_logo_check': True}).report_action(self)
        return self.env.ref('sale.action_report_saleorder') \
            .with_context({'discard_logo_check': True}).report_action(self)

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        resp = super(SaleOrder, self).message_post(**kwargs)
        if self.env.context.get('mark_so_as_sent'):
            self.filtered(lambda o: o.state == 'disc_approv').with_context(tracking_disable=True).write({'state': 'sent'})
        return resp


    # Order Cycle
    sale_order_cycle_id = fields.Many2one('order.cycle', string="Order Cycle", default=lambda self: self.env["order.cycle"].sudo().search([('is_default', '=', True)], order='id') and self.env["order.cycle"].sudo().search([('is_default', '=', True)], order='id').id or False)
    apply_order_cycle = fields.Boolean(default=lambda self: self.env["ir.sequence"].sudo().search([('code', '=', 'sale.order')], order='id') and self.env["ir.sequence"].sudo().search([('code', '=', 'sale.order')], order='id')[0].apply_order_cycle or False)
    sale_order_cycle_prefix = fields.Char()

    @api.onchange('sale_order_cycle_id')
    def onchange_sale_order_cycle(self):
        if self.name != _('New'):
            record_name = self.name
            if self.sale_order_cycle_id:
                cycle_name = self.sale_order_cycle_id.name + "/"
                to_process = True
                if self.sale_order_cycle_prefix:
                    if cycle_name != self.sale_order_cycle_prefix:
                        record_name = record_name.replace(self.sale_order_cycle_prefix, cycle_name, 1)
                        self.name = record_name
                        self.sale_order_cycle_prefix = cycle_name
                        to_process = False
                if to_process:
                    record_name = record_name
                    if cycle_name not in record_name:
                        record_name = cycle_name + record_name
                        self.name = record_name
                        self.sale_order_cycle_prefix = cycle_name
            elif self.sale_order_cycle_prefix:
                if self.sale_order_cycle_prefix in record_name:
                    record_name = record_name.replace(self.sale_order_cycle_prefix, "", 1)
                    self.name = record_name
                    self.sale_order_cycle_prefix = ""


    # Email which need to be send
    report_to_send = fields.Selection([
        ('so_gross_total', 'SO - Gross Total'),
        ('so_discount', 'SO - Discount'),
        ('so_sub_total', 'SO - Subtotal'),
    ], string="Report to send/print", required=True, default='so_discount')

    # Autolock Scheduler
    @api.multi
    def auto_lock_scheduler(self):
        to_process = self.env['ir.config_parameter'].get_param('sale.enable_lock_sales_automatic', False)
        try:
            if to_process and bool(to_process):
                config_hours = self.env['ir.config_parameter'].get_param('sale.time_needed_lock_sales', 24)
                before_time = fields.Datetime.to_string(datetime.now() - timedelta(hours=int(config_hours)))
                sale_orders = self.search([('state', '=', 'sale'), ('confirmation_date', '<=', before_time)])
                for record in sale_orders:
                    resp = record.action_done()
                self.env.cr.commit()
        except Exception as e:
            _logger.exception("Transaction Auto Lock failed")
            self.env.cr.rollback()
        return True


    # Down Payment
    require_down_payment = fields.Boolean(string="Need Down-Payment")
    is_downpayment_paid = fields.Boolean(string="Down-payment Paid", copy=False)
    downpayment_invoice_id = fields.Many2one('account.invoice', copy=False)
    obsolete = fields.Boolean(string='Obsolute Confirmed', copy=False, default=False)

    @api.multi
    def action_confirm(self):
        self = self.with_context(skip_obsolete=True)
        if not self.commitment_date:
            raise UserError(_("Commitment Date should not be empty."))
        for so in self:
            if not self.env.user.has_group('markant_sale.group_markant_approve_so_with_unpaid_downpayment'):
                if so.require_down_payment:
                    downpayment_line = False
                    for line in so.order_line:
                        if line.is_downpayment:
                            downpayment_line = True
                        if line.is_downpayment:
                            invoices = line.order_id.mapped('invoice_ids')
                            if invoices:
                                filter_invoices = invoices.filtered(lambda inv: inv.is_down_payment_invoice)
                                if filter_invoices:
                                    for fi in filter_invoices:
                                        if fi.state not in ('paid'):
                                            raise UserError(_("Until Down payment is paid, you cant confirm the sale order."))
                            else:
                                raise UserError(_("Something wrong downpayment is there but no invoice is created."))

                    if not downpayment_line:
                        raise UserError(_("Down payment is required before confirm sale order."))

            for so in self:
                product = []
                for line in so.order_line:
                    if line.product_id.obsolete_product:
                        product.append(line.product_id)

                if product:
                    for p in set(product):
                        forecast = p.qty_signed_total
                        for order in so.order_line.filtered(
                                lambda x: x.product_id == p):
                            if order.product_uom_qty <= forecast:
                                order.order_qty_after_confirm_obsolete = order.product_uom_qty
                                forecast -= order.product_uom_qty
                            else:
                                order.order_qty_after_confirm_obsolete = forecast
                so.obsolete = True

                if not so.carrier_name_id:
                    raise Warning(_('Carrier field should not be empty!'))
                else:
                    if so.carrier_name_id.installation_link:
                        inst_values = {
                            'proposed_date_from': so.inst_from_proposed_date or False,
                            'proposed_date_to': so.inst_to_proposed_date or False,
                            'planned_date_from': so.inst_from_planned_date or False,
                            'planned_date_to': so.inst_to_planned_date or False,
                            'survey_needed': so.inst_survey_necessary,
                            'staircase_available': so.inst_staircase_avail,
                            'lift_available': so.inst_lift_available,
                            'distance_place_unloading': so.inst_distance_place_unloading,
                            'any_empty_clean_zone': so.inst_any_empty_clean_zone,
                            'total_number_floors': so.inst_total_number_floors,
                            'floor_of_installation': so.inst_floor_of_installation,
                            'site_drawing_avail': so.inst_site_drawing_avail,
                            'drawing_included': so.inst_drawing_included,
                            'pre_assembly': so.inst_pre_assembly,
                            'back_order': so.inst_back_order,
                            'installation_type_id': so.inst_installation_type_id.id or False,
                            'note': so.inst_note or '',
                            'sale_order_ids': [(4, so.id)],
                            'address_id': so.partner_shipping_id.id,
                            'dealer_id': so.partner_id.id,
                            'street_number': so.partner_shipping_id.street_number,
                            'street_number2': so.partner_shipping_id.street_number2,
                            'street_name': so.partner_shipping_id.street_name,
                            'street2': so.partner_shipping_id.street2,
                            'city': so.partner_shipping_id.city,
                            'state_id': so.partner_shipping_id.state_id.id or False,
                            'zip': so.partner_shipping_id.zip,
                            'country_id': so.partner_shipping_id.country_id.id or False,
                            'phone_dealer': so.partner_id.phone,
                            'mobile': so.partner_id.mobile,
                            'email_dealer': so.partner_id.email,
                            'calculation_type_id': so.calculation_type_id.id or False,
                            'survey_id': so.inst_survey_id.id or False,
                            'survey_date': so.inst_survey_date or False,
                            'require_initial_so': so.inst_require_initial_so,
                            'initial_so_id': so.inst_initial_so_id.id or False,
                        }
                        self.env['markant.installation.form'].create(inst_values)

        res = super(SaleOrder, self).action_confirm()
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                        submenu=False):

        res = super(SaleOrder, self).fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu)

        if res.get('toolbar', False) and res.get('toolbar').get('print',False):
            reports = res.get('toolbar').get('print')
            for report in list(reports):
                if report.get('report_file', False) and report \
                        .get('report_file') == 'sale.report_saleorder':
                    res['toolbar']['print'].remove(report)

        return res

    # Incoterm : when partner changed we need to change this.
    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = super(SaleOrder, self).onchange_partner_id()
        if not self.partner_id:
            return res
        if self.partner_id and self.partner_id.incoterm_id:
            self.incoterm = self.partner_id.incoterm_id.id
        elif self.partner_id and self.partner_id.parent_id:
            if self.partner_id.parent_id.incoterm_id:
                self.incoterm = self.partner_id.parent_id.incoterm_id.id
            else:
                self.incoterm = False
        else:
            self.incoterm = False
        return res



    @api.multi
    def action_quotation_send(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference(
                'sale', 'email_template_edi_sale')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(
                'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'sale.order',
            'default_res_id': self.ids[0],
            'default_use_template': template_id,
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "markant_sale.mail_notification_paynow_sale_order",
            'proforma': self.env.context.get('proforma', False),
            'force_email': True
        }
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

class MailTemplate(models.Model):
    _inherit = 'mail.template'

    @api.multi
    def generate_email(self, res_ids, fields=None):
        """ Method overridden in order to attach the print based on configured in sale order. As markant have three different 
        type of report so which need to be include in the email that is decided based on dropdown in SO.
        """
        rslt = super(MailTemplate, self).generate_email(res_ids, fields)

        multi_mode = True
        if isinstance(res_ids, pycompat.integer_types):
            res_ids = [res_ids]
            multi_mode = False

        res_ids_to_templates = self.get_email_template(res_ids)
        for res_id in res_ids:
            related_model = self.env[self.model_id.model].browse(res_id)
            if related_model._name == 'sale.order' and related_model.report_to_send:

                template = res_ids_to_templates[res_id]
                if template.id != self.env.ref('sale.email_template_edi_sale').id:
                    continue

                report_name = self._render_template(template.report_name, template.model, res_id)

                report = template.report_template
                if related_model.report_to_send == 'so_gross_total':
                    report = self.env.ref('markant_sale.action_report_saleorder_markant_gross_total')
                if related_model.report_to_send == 'so_discount':
                    report = self.env.ref('markant_sale.action_report_saleorder_markant_gross_disc_sub_total')
                if related_model.report_to_send == 'so_sub_total':
                    report = self.env.ref('markant_sale.action_report_saleorder_markant_subtotal_only')

                report_service = report.report_name

                if report.report_type not in ['qweb-html', 'qweb-pdf']:
                    raise UserError(_('Unsupported report type %s found.') % report.report_type)
                result, format = report.render_qweb_pdf([res_id])

                result = base64.b64encode(result)
                if not report_name:
                    report_name = 'report.' + report_service
                ext = "." + format
                if not report_name.endswith(ext):
                    report_name += ext

                attachments_list = multi_mode and rslt[res_id]['attachments'] or rslt['attachments']
                new_list = []
                for t in attachments_list:
                    if t[0] != report_name:
                        new_list.append(t)
                attachments_list = new_list
                attachments_list.append((report_name, result))
                if multi_mode:
                    rslt[res_id]['attachments'] = attachments_list
                else:
                    rslt['attachments'] = attachments_list


        return rslt

class MontageInstallPricingRule(models.Model):
    _name = 'montage.installation.pricing.rule'
    _order = 'price_more_than'

    price_more_than = fields.Float(required=True)
    price_less_than_eqto = fields.Float(required=True)
    value = fields.Float(required=True, string="Amt/% ")
    mont_install_rule_id = fields.Many2one('montage.installation.rule')


    @api.one
    @api.constrains('price_more_than', 'price_less_than_eqto')
    def _check_price_rule(self):
        if self.price_more_than > self.price_less_than_eqto:
            raise Warning(_('Greather than price should be less than Less than or equal to.'))

class MontageInstallationRule(models.Model):
    _name = 'montage.installation.rule'
    _description = 'Montage and Installation'

    name = fields.Char()
    service_product_id = fields.Many2one('product.product', string="Service Product", domain="[('type', '=', 'service')]", required=True)
    condition = fields.Selection([
        ('fixed_price','Fixed Price'),
        ('based_on_rule','Based on Rules')
    ], default="fixed_price")
    price = fields.Float(string="Fixed Price")
    get_rate = fields.Selection([
        ('percentage','Percentage'),
        ('fixed','Fixed')
    ])
    based_on = fields.Selection([
        ('sum_of_gros_amount','Sum of Gross Amount (excl Admin & Installation)'),
    ], default="sum_of_gros_amount", readonly=True)
    charges_level = fields.Float(string="Charges for Level 1 & Above")
    mont_install_pricing_rule_ids = fields.One2many('montage.installation.pricing.rule', 'mont_install_rule_id', string="Pricing Rules")


    @api.model
    def create(self, vals):
        res = super(MontageInstallationRule, self).create(vals)
        res.validate_pricing_rules()
        return res

    @api.multi
    def write(self, vals):
        res = super(MontageInstallationRule, self).write(vals)
        for record in self:
            record.validate_pricing_rules()
        return res

    def validate_pricing_rules(self):
        sorted_rules = self.mont_install_pricing_rule_ids.sorted(key=lambda r: r.price_more_than)
        curr_amount = 0
        for record in sorted_rules:
            if record.price_more_than < curr_amount:
                raise Warning(_('Montage amounts should not overlap'))
            curr_amount = record.price_less_than_eqto

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    is_down_payment_invoice = fields.Boolean()

    @api.multi
    def action_invoice_paid(self):
        res = super(AccountInvoice, self).action_invoice_paid()
        todo = set()
        for invoice in self:
            if invoice.is_down_payment_invoice:
                for line in invoice.invoice_line_ids:
                    for sale_line in line.sale_line_ids:
                        todo.add((sale_line.order_id, invoice.number))
        for (order, name) in todo:
            write_done = order.with_context(no_need_check_dp=True).write({'is_downpayment_paid': True})
        return res

    @api.multi
    def write(self, vals):
        res = super(AccountInvoice, self).write(vals)
        if self.env.context.get('no_need_check_dp') is None:
            todo = set()
            for invoice in self:
                if invoice.is_down_payment_invoice:
                    for line in invoice.invoice_line_ids:
                        for sale_line in line.sale_line_ids:
                            if invoice.state == 'paid':
                                todo.add((sale_line.order_id, True))
                            else:
                                todo.add((sale_line.order_id, False))
            for (order, name) in todo:
                write_done = order.with_context(no_need_check_dp=True).write({'is_downpayment_paid': name})
        return res



    @api.multi
    def action_invoice_open(self):
        res = super(AccountInvoice, self).action_invoice_open()
        downpayment_invoices = self.filtered(lambda inv: inv.is_down_payment_invoice)
        if downpayment_invoices:
            user_ids = []
            for dpa in self.env['downpayment.email.alert'].search([]):
                user_ids.append(dpa.name.partner_id.id)
            recipients_str = ','.join(str(e) for e in user_ids)
            if recipients_str:
                template = self.env.ref('markant_sale.email_template_down_payment_invoice')
                for invoice in downpayment_invoices:
                    template.write({'partner_to': recipients_str})
                    template.send_mail(invoice.id, force_send = True)
        return res


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    advance_payment_method_temp  = fields.Selection([
        ('percentage', 'Down payment (percentage)'),
        ('fixed', 'Down payment (fixed amount)')
    ], string='What do you want to invoice?', default='percentage', required=True)

    @api.onchange('advance_payment_method_temp')
    def onchange_advance_payment_method_temp(self):
        self.advance_payment_method = self.advance_payment_method_temp

    @api.multi
    def _create_invoice(self, order, so_line, amount):
        invoice = super(SaleAdvancePaymentInv, self)._create_invoice(order, so_line, amount)
        if self.env.context.get('markant_down_payment') is not None:
            write_done = invoice.write({'is_down_payment_invoice': True})
            write_done = order.write({'downpayment_invoice_id': invoice.id})
        return invoice

class DownpaymentEmailAlert(models.Model):
    _name = "downpayment.email.alert"

    name = fields.Many2one("res.users", string="User", domain=lambda self: [( "groups_id", "=", self.env.ref( "account.group_account_manager").id )] , required=True)
    email = fields.Char(compute="compute_email", string="Email")

    @api.depends('name')
    def compute_email(self):
        for rec in self:
            if rec.name:
                if rec.name.partner_id and rec.name.partner_id.email:
                    rec.email = rec.name.partner_id.email
                else:
                    rec.email = ''
            else:
                rec.email = ''

    _sql_constraints = [
        ('code_company_uniq', 'unique (name)', 'You cant add same user again !'),
    ]

#HITESH : This is temprary fix to do not send the email when sale order
class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    def _message_auto_subscribe_notify(self, partner_ids, template):
        if not self or self.env.context.get('mail_auto_subscribe_no_notify'):
            return
        if not self.env.registry.ready:  # Don't send notification during install
            return
        if template and template == "mail.message_user_assigned":
            final_records = self
            sale_order = False
            for record in self:
                if record._name == 'sale.order':
                    sale_order = True
                    final_records -= record
            if sale_order and not final_records:
                return
        super(MailThread, self)._message_auto_subscribe_notify(partner_ids=partner_ids, template=template)

