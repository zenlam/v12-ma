from odoo import api, fields, models, _


class AS400Product(models.Model):
    _name = 'as400.product'
    _description = 'AS400 Product'

    # Ignored columns are...
    # external_ID, old item number, name (english),
    # product category (sub group), stock administration,

    default_code = fields.Char(string='Default Code')
    barcode = fields.Char(string='Barcode')
    name = fields.Char(string='Name')
    vendor = fields.Char(string='Vendor Name')
    minimal_quantity = fields.Float(string='Minimal Quantity')
    qty_multiple = fields.Float(string='Qty Multiple')
    minimum_quantity = fields.Float(string='Minimum Quantity')
    maximum_quantity = fields.Float(string='Maximum Quantity')
    cost = fields.Float(string='Fixed Settle')
    price = fields.Float(string='Purchase Price')
    currency = fields.Char(string='Currency Code')
    salesprice = fields.Float(string='Sales Price')
    sale_ok = fields.Boolean(string='Sale Ok?')
    purchase_ok = fields.Integer(string='Purchase Ok?')
    taxes_id = fields.Char(string='VAT Code')
    vendor_product_code = fields.Char(string='Vendor Product Code')
    uom_po_id = fields.Char(string='Purchase Unit')
    uom_id = fields.Char(string='Sales Unit')
    inside_odoo = fields.Boolean(string='Already inside Odoo')
    manufacturing_lead_time = fields.Float(string="Manufacturing Lead Time")
    reordering_rules_lead_time = fields.Float(string="Re-ordering rules lead time")

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # TODO : Hitesh : removed delivery_option in onchange as it not required here
    # @api.onchange('delivery_option', 'order_line')
    # def onchange_delivery_option(self):
    #     super(SaleOrder, self).onchange_delivery_option()
    @api.onchange('order_line')
    def onchange_order_line_as400(self):
        for line in self.order_line:
            current_product = line.product_id
            as400_line = self.env['as400.product'].sudo().search([
                ('default_code', '=', current_product.default_code)], limit=1)
            if as400_line and not as400_line.inside_odoo:
                s_uom = self.env['uom.uom'].search(
                    [('name', '=', as400_line.uom_id)], limit=1)
                p_uom = self.env['uom.uom'].search(
                    [('name', '=', as400_line.uom_po_id)], limit=1)
                tax_id = self.env['account.tax'].search(
                    [('name', '=', as400_line.taxes_id)], limit=1)
                vendor_id = self.env['res.partner'].search(
                    [('name', '=', as400_line.vendor),
                     ('supplier', '=', True)], limit=1)
                currency = self.env['res.currency'].search(
                    [('name', '=', as400_line.currency)], limit=1)

                current_product.write({
                    'produce_delay': as400_line.manufacturing_lead_time or 0.0,
                    'sale_ok': as400_line.sale_ok,
                    'purchase_ok': True
                    if as400_line.purchase_ok == 1 else False,
                    'uom_id': s_uom.id if s_uom
                    else current_product.uom_id.id,
                    'uom_po_id': p_uom.id if p_uom
                    else current_product.uom_id.id,
                    'taxes_id': [(4, tax_id.id)] if tax_id else '',
                    'barcode': as400_line.barcode or current_product.barcode,
                })

                # After UoM update call write to update the pricing
                current_product.write({
                    'price': as400_line.salesprice,
                    'lst_price': as400_line.salesprice,
                    'standard_price': as400_line.cost,
                })

                if vendor_id:
                    product_supplierinfo = self.env['product.supplierinfo'].create({
                        'name': vendor_id.id,
                        'product_id': current_product.id,
                        'product_tmpl_id': current_product.product_tmpl_id.id,
                        'product_code': as400_line.vendor_product_code or '',
                        'price': as400_line.price,
                        'min_qty': as400_line.minimal_quantity,
                        'currency_id': currency.id if currency else
                        self.env.user.company_id.currency_id.id
                    })
                    if as400_line.reordering_rules_lead_time:
                       product_supplierinfo.write({'delay' : as400_line.reordering_rules_lead_time}) 

                reordering = self.env['stock.warehouse.orderpoint'] \
                    .search([('product_id', '=', current_product.id),
                             ('product_min_qty', '=',
                              as400_line.minimum_quantity),
                             ('product_max_qty', '=',
                              as400_line.maximum_quantity),
                             ('qty_multiple', '=',
                              as400_line.qty_multiple)])
                if not reordering:
                    reordering_exist = self.env[
                        'stock.warehouse.orderpoint'] \
                        .search([('product_id', '=', current_product.id)],
                                limit=1)
                    reordering_exist.write({
                        'product_id': current_product.id,
                        'product_min_qty': as400_line.minimum_quantity,
                        'product_max_qty': as400_line.maximum_quantity,
                        'qty_multiple': as400_line.qty_multiple,
                    })
                    if not reordering_exist and (as400_line.minimum_quantity
                                                 or as400_line.maximum_quantity
                                                 or as400_line.qty_multiple):
                        variant_reordering = self.env[
                            'stock.warehouse.orderpoint']
                        variant_reordering.create({
                            'product_id': current_product.id,
                            'product_min_qty': as400_line.minimum_quantity,
                            'product_max_qty': as400_line.maximum_quantity,
                            'qty_multiple': as400_line.qty_multiple,
                        })

                as400_line.write({
                    'inside_odoo': True,
                })

                # Call the product onchange method at last
                line.product_id_change()
                line.product_id_change_margin()


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def _create_product_variant(self, combination, log_warning=False):
        res = super(ProductTemplate, self)._create_product_variant(
            combination, log_warning=log_warning)

        context = self.env.context or {}
        as400_line = self.env['as400.product'].sudo().search([
            ('default_code', '=', res.default_code)], limit=1)

        if not context.get('import_file') and as400_line and \
                not as400_line.inside_odoo:
            s_uom = self.env['uom.uom'].search(
                [('name', '=', as400_line.uom_id)], limit=1)
            p_uom = self.env['uom.uom'].search(
                [('name', '=', as400_line.uom_po_id)], limit=1)
            tax_id = self.env['account.tax'].search(
                [('name', '=', as400_line.taxes_id)], limit=1)
            vendor_id = self.env['res.partner'].search(
                [('name', '=', as400_line.vendor),
                 ('supplier', '=', True)], limit=1)
            currency = self.env['res.currency'].search(
                [('name', '=', as400_line.currency)], limit=1)

            if as400_line.manufacturing_lead_time:
                res.write({'produce_delay': as400_line.manufacturing_lead_time})

            res.write({
                'sale_ok': as400_line.sale_ok,
                'purchase_ok': True
                if as400_line.purchase_ok == 1 else False,
                'uom_id': s_uom.id if s_uom
                else res.uom_id.id,
                'uom_po_id': p_uom.id if p_uom
                else res.uom_id.id,
                'taxes_id': [(4, tax_id.id)] if tax_id else '',
                'barcode': as400_line.barcode or res.barcode,
            })

            # After UoM update call write to update the pricing
            res.write({
                'price': as400_line.salesprice,
                'lst_price': as400_line.salesprice,
                'standard_price': as400_line.cost,
            })

            if vendor_id:
                product_supplierinfo = self.env['product.supplierinfo'].create({
                    'name': vendor_id.id,
                    'product_id': res.id,
                    'product_tmpl_id': res.product_tmpl_id.id,
                    'product_code': as400_line.vendor_product_code or '',
                    'price': as400_line.price,
                    'min_qty': as400_line.minimal_quantity,
                    'currency_id': currency.id if currency else
                    self.env.user.company_id.currency_id.id
                })
                if as400_line.reordering_rules_lead_time:
                       product_supplierinfo.write({'delay' : as400_line.reordering_rules_lead_time,}) 

            reordering = self.env['stock.warehouse.orderpoint'] \
                .search([('product_id', '=', res.id),
                         ('product_min_qty', '=',
                          as400_line.minimum_quantity),
                         ('product_max_qty', '=',
                          as400_line.maximum_quantity),
                         ('qty_multiple', '=',
                          as400_line.qty_multiple)])
            if not reordering:
                reordering_exist = self.env[
                    'stock.warehouse.orderpoint'] \
                    .search([('product_id', '=', res.id)], limit=1)
                reordering_exist.write({
                    'product_id': res.id,
                    'product_min_qty': as400_line.minimum_quantity,
                    'product_max_qty': as400_line.maximum_quantity,
                    'qty_multiple': as400_line.qty_multiple,
                })
                if not reordering_exist and (as400_line.minimum_quantity
                                             or as400_line.maximum_quantity
                                             or as400_line.qty_multiple):
                    variant_reordering = self.env['stock.warehouse.orderpoint']
                    variant_reordering.create({
                        'product_id': res.id,
                        'product_min_qty': as400_line.minimum_quantity,
                        'product_max_qty': as400_line.maximum_quantity,
                        'qty_multiple': as400_line.qty_multiple,
                    })

            as400_line.write({
                'inside_odoo': True,
            })
        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def write(self, vals):
        res = super(ProductProduct, self).write(vals)
        for prod in self:
            if vals.get('default_code'):
                context = self.env.context or {}
                as400_line = self.env['as400.product'].sudo().search([
                    ('default_code', '=', prod.default_code)], limit=1)

                if not context.get('import_file') and as400_line and \
                        not as400_line.inside_odoo:
                    s_uom = self.env['uom.uom'].search(
                        [('name', '=', as400_line.uom_id)], limit=1)
                    p_uom = self.env['uom.uom'].search(
                        [('name', '=', as400_line.uom_po_id)], limit=1)
                    tax_id = self.env['account.tax'].search(
                        [('name', '=', as400_line.taxes_id)], limit=1)
                    vendor_id = self.env['res.partner'].search(
                        [('name', '=', as400_line.vendor),
                         ('supplier', '=', True)], limit=1)
                    currency = self.env['res.currency'].search(
                        [('name', '=', as400_line.currency)], limit=1)

                    if as400_line.manufacturing_lead_time:
                        prod.write({'produce_delay': as400_line.manufacturing_lead_time})

                    prod.write({
                        'sale_ok': as400_line.sale_ok,
                        'purchase_ok': True
                        if as400_line.purchase_ok == 1 else False,
                        'uom_id': s_uom.id if s_uom
                        else prod.uom_id.id,
                        'uom_po_id': p_uom.id if p_uom
                        else prod.uom_id.id,
                        'taxes_id': [(4, tax_id.id)] if tax_id else '',
                        'barcode': as400_line.barcode or prod.barcode,
                    })

                    # After UoM update call write to update the pricing
                    prod.write({
                        'price': as400_line.salesprice,
                        'lst_price': as400_line.salesprice,
                        'standard_price': as400_line.cost,
                    })
                    

                    if vendor_id:
                        product_supplierinfo = self.env['product.supplierinfo'].create({
                            'name': vendor_id.id,
                            'product_id': prod.id,
                            'product_tmpl_id': prod.product_tmpl_id.id,
                            'product_code': as400_line.vendor_product_code or '',
                            'price': as400_line.price,
                            'min_qty': as400_line.minimal_quantity,
                            'currency_id': currency.id if currency else
                            self.env.user.company_id.currency_id.id
                        })
                        if as400_line.reordering_rules_lead_time:
                            product_supplierinfo.write({'delay' : as400_line.reordering_rules_lead_time,}) 

                    reordering = self.env['stock.warehouse.orderpoint'] \
                        .search([('product_id', '=', prod.id),
                                 ('product_min_qty', '=',
                                  as400_line.minimum_quantity),
                                 ('product_max_qty', '=',
                                  as400_line.maximum_quantity),
                                 ('qty_multiple', '=',
                                  as400_line.qty_multiple)])
                    if not reordering:
                        reordering_exist = self.env[
                            'stock.warehouse.orderpoint'] \
                            .search([('product_id', '=', prod.id)], limit=1)
                        reordering_exist.write({
                            'product_id': prod.id,
                            'product_min_qty': as400_line.minimum_quantity,
                            'product_max_qty': as400_line.maximum_quantity,
                            'qty_multiple': as400_line.qty_multiple,
                        })
                        if not reordering_exist and (
                                as400_line.minimum_quantity or
                                as400_line.maximum_quantity or
                                as400_line.qty_multiple):
                            variant_reordering = self.env[
                                'stock.warehouse.orderpoint']
                            variant_reordering.create({
                                'product_id': prod.id,
                                'product_min_qty': as400_line.minimum_quantity,
                                'product_max_qty': as400_line.maximum_quantity,
                                'qty_multiple': as400_line.qty_multiple,
                            })

                    as400_line.write({
                        'inside_odoo': True,
                    })
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super(ProductProduct, self).create(vals_list)

        for prod in res:
            context = self.env.context or {}
            as400_line = self.env['as400.product'].sudo().search([
                ('default_code', '=', prod.default_code)], limit=1)

            if not context.get('import_file') and as400_line and \
                    not as400_line.inside_odoo:
                s_uom = self.env['uom.uom'].search(
                    [('name', '=', as400_line.uom_id)], limit=1)
                p_uom = self.env['uom.uom'].search(
                    [('name', '=', as400_line.uom_po_id)], limit=1)
                tax_id = self.env['account.tax'].search(
                    [('name', '=', as400_line.taxes_id)], limit=1)
                vendor_id = self.env['res.partner'].search(
                    [('name', '=', as400_line.vendor),
                     ('supplier', '=', True)], limit=1)
                currency = self.env['res.currency'].search(
                    [('name', '=', as400_line.currency)], limit=1)

                if as400_line.manufacturing_lead_time:
                    prod.write({'produce_delay': as400_line.manufacturing_lead_time})

                prod.write({
                    'sale_ok': as400_line.sale_ok,
                    'purchase_ok': True
                    if as400_line.purchase_ok == 1 else False,
                    'uom_id': s_uom.id if s_uom
                    else prod.uom_id.id,
                    'uom_po_id': p_uom.id if p_uom
                    else prod.uom_id.id,
                    'taxes_id': [(4, tax_id.id)] if tax_id else '',
                    'barcode': as400_line.barcode or prod.barcode,
                })

                # After UoM update call write to update the pricing
                prod.write({
                    'price': as400_line.salesprice,
                    'lst_price': as400_line.salesprice,
                    'standard_price': as400_line.cost,
                })

                if vendor_id:
                    product_supplierinfo = self.env['product.supplierinfo'].create({
                        'name': vendor_id.id,
                        'product_id': prod.id,
                        'product_tmpl_id': prod.product_tmpl_id.id,
                        'product_code': as400_line.vendor_product_code or '',
                        'price': as400_line.price,
                        'min_qty': as400_line.minimal_quantity,
                        'currency_id': currency.id if currency else
                        self.env.user.company_id.currency_id.id
                    })
                    if as400_line.reordering_rules_lead_time:
                        product_supplierinfo.write({'delay' : as400_line.reordering_rules_lead_time,})

                reordering = self.env['stock.warehouse.orderpoint'] \
                    .search([('product_id', '=', prod.id),
                             ('product_min_qty', '=',
                              as400_line.minimum_quantity),
                             ('product_max_qty', '=',
                              as400_line.maximum_quantity),
                             ('qty_multiple', '=',
                              as400_line.qty_multiple)])
                if not reordering:
                    reordering_exist = self.env['stock.warehouse.orderpoint']\
                        .search([('product_id', '=', prod.id)], limit=1)
                    reordering_exist.write({
                        'product_id': prod.id,
                        'product_min_qty': as400_line.minimum_quantity,
                        'product_max_qty': as400_line.maximum_quantity,
                        'qty_multiple': as400_line.qty_multiple,
                    })
                    if not reordering_exist and (as400_line.minimum_quantity
                                                 or as400_line.maximum_quantity
                                                 or as400_line.qty_multiple):
                        variant_reordering = self.env[
                            'stock.warehouse.orderpoint']
                        variant_reordering.create({
                            'product_id': prod.id,
                            'product_min_qty': as400_line.minimum_quantity,
                            'product_max_qty': as400_line.maximum_quantity,
                            'qty_multiple': as400_line.qty_multiple,
                        })

                as400_line.write({
                    'inside_odoo': True,
                })
        return res


class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.multi
    def create_products_for_bom(self, new_prod_attr_vals_lst, conf_line):
        res = super(StockRule, self).create_products_for_bom(
            new_prod_attr_vals_lst, conf_line)

        for prod in res:
            context = self.env.context or {}
            as400_line = self.env['as400.product'].sudo().search([
                ('default_code', '=', prod.default_code)], limit=1)

            if not context.get('import_file') and as400_line and \
                    not as400_line.inside_odoo:
                s_uom = self.env['uom.uom'].search(
                    [('name', '=', as400_line.uom_id)], limit=1)
                p_uom = self.env['uom.uom'].search(
                    [('name', '=', as400_line.uom_po_id)], limit=1)
                tax_id = self.env['account.tax'].search(
                    [('name', '=', as400_line.taxes_id)], limit=1)
                vendor_id = self.env['res.partner'].search(
                    [('name', '=', as400_line.vendor),
                     ('supplier', '=', True)], limit=1)
                currency = self.env['res.currency'].search(
                    [('name', '=', as400_line.currency)], limit=1)


                if as400_line.manufacturing_lead_time:
                    res.write({'produce_delay': as400_line.manufacturing_lead_time})

                res.write({
                    'sale_ok': as400_line.sale_ok,
                    'purchase_ok': True
                    if as400_line.purchase_ok == 1 else False,
                    'uom_id': s_uom.id if s_uom
                    else prod.uom_id.id,
                    'uom_po_id': p_uom.id if p_uom
                    else prod.uom_id.id,
                    'taxes_id': [(4, tax_id.id)] if tax_id else '',
                    'barcode': as400_line.barcode or prod.barcode,
                })

                # After UoM update call write to update the pricing
                prod.write({
                    'price': as400_line.salesprice,
                    'lst_price': as400_line.salesprice,
                    'standard_price': as400_line.cost,
                })

                if vendor_id:
                    product_supplierinfo = self.env['product.supplierinfo'].create({
                        'name': vendor_id.id,
                        'product_id': prod.id,
                        'product_tmpl_id': prod.product_tmpl_id.id,
                        'product_code': as400_line.vendor_product_code or '',
                        'price': as400_line.price,
                        'min_qty': as400_line.minimal_quantity,
                        'currency_id': currency.id if currency else
                        self.env.user.company_id.currency_id.id
                    })
                    if as400_line.reordering_rules_lead_time:
                        product_supplierinfo.write({'delay' : as400_line.reordering_rules_lead_time,})

                reordering = self.env['stock.warehouse.orderpoint'] \
                    .search([('product_id', '=', prod.id),
                             ('product_min_qty', '=',
                              as400_line.minimum_quantity),
                             ('product_max_qty', '=',
                              as400_line.maximum_quantity),
                             ('qty_multiple', '=',
                              as400_line.qty_multiple)])
                if not reordering:
                    reordering_exist = self.env['stock.warehouse.orderpoint'] \
                        .search([('product_id', '=', prod.id)], limit=1)
                    reordering_exist.write({
                        'product_id': prod.id,
                        'product_min_qty': as400_line.minimum_quantity,
                        'product_max_qty': as400_line.maximum_quantity,
                        'qty_multiple': as400_line.qty_multiple,
                    })
                    if not reordering_exist and (as400_line.minimum_quantity
                                                 or as400_line.maximum_quantity
                                                 or as400_line.qty_multiple):
                        variant_reordering = self.env[
                            'stock.warehouse.orderpoint']
                        variant_reordering.create({
                            'product_id': prod.id,
                            'product_min_qty': as400_line.minimum_quantity,
                            'product_max_qty': as400_line.maximum_quantity,
                            'qty_multiple': as400_line.qty_multiple,
                        })

                as400_line.write({
                    'inside_odoo': True,
                })
        return res
