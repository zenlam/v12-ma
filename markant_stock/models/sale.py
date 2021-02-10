from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_option = fields.Selection(
        [('full', 'Full'), ('partial', 'Partial')],
        string='Delivery Option', default='full', required=True)
    no_auto_invoice = fields.Boolean(string="No Auto-Invoice")
    picking_policy = fields.Selection([
        ('direct', 'Deliver each product when available'),
        ('one', 'Deliver all products at once')],
        readonly=False, default='one')
    block_do = fields.Boolean(string="Block Delivery")
    order_line_notes = fields.Text('Combine Order Line Notes', copy=False)

    @api.model
    def create(self, vals):
        result = super(SaleOrder, self).create(vals)
        result.order_line_notes = False
        for line in result.order_line:
            line.section_note_id = False

            # Get data of line Notes & Save it to Field
            if line.display_type == 'line_note':
                if result.order_line_notes:
                    result.order_line_notes += "\n" + line.name
                else:
                    result.order_line_notes = line.name

        for idx, val in enumerate(result.order_line):
            if val.display_type in ['line_section']:
                for line in result.order_line[idx:]:
                    if line.display_type not in ['line_section',
                                                 'line_note']:
                        line.section_name = val.name
        return result

    @api.multi
    def _write(self, values):
        res = super(SaleOrder, self)._write(values)
        order_lines = values.get('order_line')

        for block in self:
            block.picking_ids.write({'block_do': block.block_do})

        if values.get('contact_person_id'):
            for record in self:
                record.picking_ids.write({
                    'contact_person_id': record.contact_person_id.id})

        if values.get('commitment_date'):
            for record in self:
                for picking in record.picking_ids:
                    if picking.state != 'done':
                        picking.write({
                            'so_commitment_date': record.commitment_date
                        })
            
        if values.get('delivery_option'):
            for record in self:
                if record.picking_ids:
                    record.picking_ids.write({'delivery_option': record.delivery_option, 'move_type' : record.picking_policy})

        if order_lines:
            # Check if sequence is triggered in write, if yes means need to
            # recompute orderpoint
            # Check if allow_partial is triggered in write, if yes means need
            # to recompute allow_partial
            run_orderpoint = False
            compute_partial = False
            vals = [x for x in order_lines if
                    x[0] != 4 and x[2] is not False]
            values['order_line'] = vals
            seq = values.get('order_line')
            for val in seq:
                if val[2].get('sequence') or val[2].get('name'):
                    run_orderpoint = True
                partial = val[2].get('allow_partial')
                if partial or partial is False:
                    compute_partial = True
            if compute_partial:
                for order in self:
                    for line in order.order_line:
                        if line.display_type not in ['line_section',
                                                     'line_note']:
                            for move in line.move_ids:
                                if move.state not in ['done', 'cancel']:
                                    move.allow_partial = line.allow_partial
            if run_orderpoint:
                for order in self:
                    for line in order.order_line:
                        line.section_name = False

                    for idx, val in enumerate(order.order_line):
                        if val.display_type in ['line_section']:
                            for line in order.order_line[idx:]:
                                if line.display_type not in ['line_section',
                                                             'line_note']:
                                    line.section_name = val.name

                                    for move in line.move_ids:
                                        if move.state not in ['done', 'cancel']:
                                            if move.article_description:
                                                if "\n" in move.article_description:
                                                    move.article_description = \
                                                        move.article_description.replace(
                                                            move.article_description.split(
                                                                '\n')[0], val.name)
                                                    move.article_description_move = \
                                                        move.article_description_move.replace(
                                                            move.article_description_move.split(
                                                                '\n')[0], val.name)
                                                else:
                                                    move.article_description = val.name
                                                    move.article_description_move = val.name
                                            else:
                                                if len(move.sale_line_id.move_ids) == 1:
                                                    move.article_description = val.name
                                                    move.article_description_move = val.name
                                                else:
                                                    move.sale_line_id.move_ids[0].\
                                                        article_description = \
                                                        val.name + '\n' + line.name + \
                                                        '\nQty: ' + \
                                                        str(line.product_uom_qty)
                                                    for mov in move.sale_line_id.move_ids:
                                                        mov.article_description_move = move.sale_line_id.move_ids[0].article_description

                    for line in order.order_line:
                        if line.display_type not in ['line_section', 'line_note']:
                            for move in line.move_ids:
                                if move.state not in ['done', 'cancel']:
                                    if len(move.sale_line_id.move_ids) == 1:
                                        move.article_description = 'No Order Point'
                                        move.article_description_move = 'No Order Point'
                                    else:
                                        move.sale_line_id.move_ids[0].article_description = \
                                            move.sale_line_id.move_ids[0].article_description.replace(
                                                move.sale_line_id.move_ids[0].article_description.split('\n')[0],
                                                'No Order Point')
                                        move.sale_line_id.move_ids[0].article_description_move = \
                                            move.sale_line_id.move_ids[0].article_description.replace(
                                                move.sale_line_id.move_ids[0].article_description.split('\n')[0],
                                                'No Order Point')
                                        for mov in move.sale_line_id.move_ids:
                                            mov.article_description_move = move.sale_line_id.move_ids[0].article_description
                        else:
                            break

                    order.order_line_notes = False
                    for line in order.order_line:
                        # Get data of line Notes & Save it to Field
                        if line.display_type == 'line_note':
                            if order.order_line_notes:
                                order.order_line_notes += "\n" + line.name
                            else:
                                order.order_line_notes = line.name

                    # Save Order Line Notes to All related Pickings
                    for picking in order.picking_ids:
                        picking.note = order.order_line_notes
        return res

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for record in self:
            if record.picking_ids:
                record.picking_ids.write({
                    'delivery_option': record.delivery_option,
                    'move_type': record.picking_policy,
                    'block_do': record.block_do,
                    'so_commitment_date': record.commitment_date,
                    'note': record.order_line_notes,
                })
        return res

    @api.onchange('delivery_option')
    def onchange_delivery_option(self):
        for line in self.order_line:
            if not line.is_project_discount_line:
                line.delivery_option = self.delivery_option
                if self.delivery_option == 'full':
                    line.allow_partial = False
                elif self.delivery_option == "partial":
                    line.allow_partial = True

        if self.delivery_option == 'full':
            self.picking_policy = 'one'
        elif self.delivery_option == 'partial':
            self.picking_policy = 'direct'

    @api.onchange('delivery_option')
    def onchange_delivery_date(self):
        for line in self.order_line:
            line.delivery_date = self.commitment_date

    @api.onchange('picking_policy')
    def _onchange_picking_policy(self):
        if self.picking_policy == 'one':
            self.delivery_option = 'full'
        elif self.picking_policy == 'direct':
            self.delivery_option = 'partial'

    @api.onchange('commitment_date')
    def _onchange_commitment_date(self):
        res = super(SaleOrder, self)._onchange_commitment_date()
        if self.state not in ['sale', 'done', 'cancel']:
            for line in self.order_line:
                line.delivery_date = self.commitment_date
        else:
            if self.picking_ids and len(self.picking_ids) == 1 and \
                    self.picking_ids.state not in ['done', 'cancel']:
                for line in self.order_line:
                    line.delivery_date = self.commitment_date
        return res

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        inv_obj = self.env['account.invoice']
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        invoices = {}
        references = {}
        invoices_origin = {}
        invoices_name = {}

        # Keep track of the sequences of the lines
        # To keep lines under their section
        inv_line_sequence = 0
        for order in self:
            group_key = order.id if grouped else (
                order.partner_invoice_id.id, order.currency_id.id)

            # We only want to create sections that have at least one
            # invoiceable line
            pending_section = None

            # Create lines in batch to avoid performance problems
            line_vals_list = []

            # Used to check if order have delivered qty or not
            delivered_qty_exist = False

            # Run only if order triggered by Auto Invoice Cron Job
            # Also, check if delivered qty exists for current record or not
            if self._context.get('markant_auto_invoice'):
                for line in order.order_line:
                    if line.qty_delivered > 0:
                        delivered_qty_exist = True

                if delivered_qty_exist:
                    # sequence is the natural order of order_lines
                    for line in order.order_line:
                        if line.display_type == 'line_section':
                            pending_section = line
                            continue
                        if float_is_zero(line.qty_to_invoice,
                                         precision_digits=precision):
                            continue
                        if group_key not in invoices:
                            inv_data = order._prepare_invoice()
                            # Remove user_id from `inv_data` as at
                            # this point we do not know that this invoice's
                            # total amount is +ve or -ve,
                            # if -ve then we are going to delete that Invoice
                            if inv_data.get('user_id'):
                                inv_data['so_ref_id'] = order.id
                                inv_data['user_id'] = False
                            invoice = inv_obj.create(inv_data)
                            references[invoice] = order
                            invoices[group_key] = invoice
                            invoices_origin[group_key] = [invoice.origin]
                            invoices_name[group_key] = [invoice.name]
                        elif group_key in invoices:
                            if order.name not in invoices_origin[group_key]:
                                invoices_origin[group_key].append(order.name)
                            if order.client_order_ref and order.client_order_ref \
                                    not in invoices_name[group_key]:
                                invoices_name[group_key].append(
                                    order.client_order_ref)

                        if line.qty_to_invoice > 0 or (
                                line.qty_to_invoice < 0 and final):
                            if pending_section:
                                section_invoice = pending_section. \
                                    invoice_line_create_vals(
                                    invoices[group_key].id,
                                    pending_section.qty_to_invoice
                                )
                                inv_line_sequence += 1
                                section_invoice[0][
                                    'sequence'] = inv_line_sequence
                                line_vals_list.extend(section_invoice)
                                pending_section = None

                            inv_line_sequence += 1
                            inv_line = line.invoice_line_create_vals(
                                invoices[group_key].id, line.qty_to_invoice
                            )
                            inv_line[0]['sequence'] = inv_line_sequence
                            line_vals_list.extend(inv_line)

            else:
                # sequence is the natural order of order_lines
                for line in order.order_line:
                    if line.display_type == 'line_section':
                        pending_section = line
                        continue
                    if float_is_zero(line.qty_to_invoice,
                                     precision_digits=precision):
                        continue
                    if group_key not in invoices:
                        inv_data = order._prepare_invoice()
                        invoice = inv_obj.create(inv_data)
                        references[invoice] = order
                        invoices[group_key] = invoice
                        invoices_origin[group_key] = [invoice.origin]
                        invoices_name[group_key] = [invoice.name]
                    elif group_key in invoices:
                        if order.name not in invoices_origin[group_key]:
                            invoices_origin[group_key].append(order.name)
                        if order.client_order_ref and order.client_order_ref \
                                not in invoices_name[group_key]:
                            invoices_name[group_key].append(order.client_order_ref)

                    if line.qty_to_invoice > 0 or (
                            line.qty_to_invoice < 0 and final):
                        if pending_section:
                            section_invoice = pending_section.\
                                invoice_line_create_vals(
                                    invoices[group_key].id,
                                    pending_section.qty_to_invoice
                                )
                            inv_line_sequence += 1
                            section_invoice[0]['sequence'] = inv_line_sequence
                            line_vals_list.extend(section_invoice)
                            pending_section = None

                        inv_line_sequence += 1
                        inv_line = line.invoice_line_create_vals(
                            invoices[group_key].id, line.qty_to_invoice
                        )
                        inv_line[0]['sequence'] = inv_line_sequence
                        line_vals_list.extend(inv_line)

            if references.get(invoices.get(group_key)):
                if order not in references[invoices[group_key]]:
                    references[invoices[group_key]] |= order

            self.env['account.invoice.line'].create(line_vals_list)

        for group_key in invoices:
            invoices[group_key].write(
                {'name': ', '.join(invoices_name[group_key]),
                 'origin': ', '.join(invoices_origin[group_key])})
            sale_orders = references[invoices[group_key]]
            if len(sale_orders) == 1:
                invoices[group_key].reference = sale_orders.reference

        if not invoices and not self._context.get('markant_auto_invoice'):
            raise UserError(_(
                'There is no invoiceable line. '
                'If a product has a Delivered quantities invoicing policy, '
                'please make sure that a quantity has been delivered.'))

        if self._context.get('markant_auto_invoice'):
            clear_dict = False
            for invoice in invoices.values():
                if invoice.amount_total < 0:
                    invoice.unlink()
                    clear_dict = True
                else:
                    # We write the user_id from SO to current Invoice,
                    # if SO available...
                    invoice.user_id = invoice.so_ref_id and \
                                      invoice.so_ref_id.user_id and \
                                      invoice.so_ref_id.user_id.id
            if clear_dict is True:
                invoices.clear()
        self._finalize_invoices(invoices, references)
        return [inv.id for inv in invoices.values()]


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    delivery_option = fields.Selection(
        [('full', 'Full'), ('partial', 'Partial')],
        string='Delivery Option', copy=False)
    section_name = fields.Char(string='Order Point', readonly=True)
    allow_partial = fields.Boolean(string='Allow Partial?', copy=False)
    delivery_date = fields.Datetime(string='Delivery Date')


    @api.multi
    def write(self, vals):
        res = super(SaleOrderLine, self).write(vals)
        if vals.get('delivery_date') is not None:
            for record in self:
                for move in record.move_ids:
                    if record.order_id.state not in ['done', 'cancel']:
                        if move.state not in ['done', 'cancel']:
                            write_done = move.write({'date_expected': record.delivery_date})
        return res

    # Overwrite method from sale_mrp module
    @api.multi
    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()

        for line in self:
            if line.qty_delivered_method == 'stock_move':
                # In the case of a kit, we need to check if all
                # components are shipped. Since the BOM might
                # have changed, we don't compute the quantities
                # but verify the move state.
                bom = self.env['mrp.bom']._bom_find(
                    product=line.product_id, company_id=line.company_id.id)
                if bom and bom.type == 'phantom':
                    moves = line.move_ids.filtered(
                        lambda m: m.picking_id and
                        m.picking_id.state != 'cancel')
                    bom_delivered = moves and all(
                        [move.state == 'done' for move in moves])
                    if bom_delivered:
                        line.qty_delivered = line.product_uom_qty
                    else:
                        partial_qty_lst = []
                        for move in moves:
                            if move.state == 'done':
                                partial_qty_lst.append(move.product_uom_qty)
                        if partial_qty_lst:
                            qty = min(partial_qty_lst)
                            if qty == line.product_uom_qty:
                                line.qty_delivered = round(
                                    (qty / line.product_uom_qty))
                            elif qty > line.product_uom_qty:
                                line.qty_delivered = round(
                                    (line.product_uom_qty / qty) *
                                    line.product_uom_qty)
                            else:
                                line.qty_delivered = round(
                                    (qty / line.product_uom_qty) *
                                    line.product_uom_qty)
                        else:
                            line.qty_delivered = 0.0
            if line.qty_delivered_method == 'manual':
                # In the case of a kit, we need to check
                # if partial kits are shipped. Since the BOM might
                # have changed, we don't compute the quantities
                # but verify the shipped items with original ordered items.
                bom = self.env['mrp.bom']._bom_find(
                    product=line.product_id, company_id=line.company_id.id)
                if bom and bom.type == 'phantom':
                    moves = line.move_ids.filtered(
                        lambda m: m.picking_id and
                        m.picking_id.state != 'cancel')
                    partial_qty_lst = []
                    for move in moves:
                        if move.state == 'done':
                            partial_qty_lst.append(move.product_uom_qty)
                    if partial_qty_lst:
                        qty = min(partial_qty_lst)
                        if qty == line.product_uom_qty:
                            line.qty_delivered = round(
                                (qty / line.product_uom_qty))
                        elif qty > line.product_uom_qty:
                            line.qty_delivered = round(
                                (line.product_uom_qty / qty) *
                                line.product_uom_qty)
                        else:
                            line.qty_delivered = round(
                                (qty / line.product_uom_qty) *
                                line.product_uom_qty)
                    else:
                        line.qty_delivered = 0.0


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    so_ref_id = fields.Many2one('sale.order', string='SO Ref',
                                readonly=True,
                                help='Used for chatter mail purpose. '
                                     'As we delete the invoice if it is -ve, '
                                     'which is created from auto-invoice cron')

    @api.multi
    def action_send_mail(self, lang=False, email=None, user=False,
                         portal_url=False):
        self.ensure_one()
        try:
            template = self.env.ref(
                'account.email_template_edi_invoice')
        except ValueError:
            template = False
        if email:
            template.with_context(email=email, portal_url=portal_url,
                                  user=user, lang=lang)\
                .send_mail(self.id, force_send=True)
        return True


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    def _message_auto_subscribe_notify(self, partner_ids, template):
        if not self or self.env.context.get('mail_auto_subscribe_no_notify'):
            return
        if not self.env.registry.ready:  # Don't send notification during install
            return
        if template and template == "mail.message_user_assigned":
            for record in self:
                if record._name == 'account.invoice':
                    return
        super(MailThread, self)._message_auto_subscribe_notify(
            partner_ids=partner_ids, template=template)
