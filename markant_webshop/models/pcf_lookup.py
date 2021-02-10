from odoo import api, fields, models, _


class WebStockApiLog(models.Model):
    _name = "webshop.stock.api.log"
    _description = "Webshop Stock API Log"
    _rec_name = 'product_id'
    _order = 'create_date desc'

    internal_ref = fields.Char('Internal Ref', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    qty_synced = fields.Char('Qty Synced', readonly=True)
    req_type = fields.Char('Request Type', readonly=True)
    sync_method = fields.Char('Sync Method', readonly=True)
    sync_time = fields.Char('Sync Time', readonly=True)
    sync_status = fields.Char('Sync Status', readonly=True)
    response_body = fields.Text('Response Body', readonly=True)


class PCFMaxQtyLogItem(models.Model):
    _name = "pcf.max.qty.log.item"
    _description = "PCF Max Qty Log Item"

    pcf_log = fields.Many2one('pcf.max.qty.log', 'PCF Log')
    product_id = fields.Many2one('product.product', 'Product')
    status = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], 'Status')
    reason = fields.Char('Reason')


class PCFMaxQtyLog(models.Model):
    _name = 'pcf.max.qty.log'
    _description = 'PCF Max Qty Log'
    _rec_name = 'date'

    date = fields.Datetime('Create Date')
    user_id = fields.Many2one('res.users', 'User')
    log_item_ids = fields.One2many('pcf.max.qty.log.item', 'pcf_log',
                                   'Items')


class PCFLookup(models.AbstractModel):
    _inherit = 'pcf.lookup'

    @api.model
    def _compute_pcf_max_qty(self):
        all_products = self.env['product.product'].sudo().search([
            ('active', '=', True), ('webshop_boolean_variant', '=', True)])
        log_items = []
        api_config = self.env['webshop.api.config'].search(
            [('active', '=', True)])

        retries = 0
        if api_config:
            retries = api_config.api_attempts

        for product in all_products:
            if product.configurable_ok:
                product_tmpl_id = product.product_tmpl_id and \
                                  product.product_tmpl_id.id
                bom = self.env['mrp.bom']._bom_find(
                    product_tmpl=self.env['product.template'].browse(
                        product_tmpl_id))
                if bom:
                    status = 'pass'
                    reason = ''
                    qty = 1
                    max_producible_qty = self.get_all_lines(
                        product_tmpl_id, product.id, qty)
                    if max_producible_qty == '<h2>Can not produce.</h2>':
                        result = 0
                    else:
                        max_producible_qty_lst = max_producible_qty.split(' ')
                        result = max_producible_qty_lst[2]

                    product.write({
                        'pcf_max_producible_qty': float(result)
                    })
                    product.with_delay(max_retries=retries).webshop_api_stock(
                        api_config)
                else:
                    status = 'fail'
                    reason = 'BoM not Found for ' + \
                             product.product_tmpl_id.name
            else:
                status = 'pass'
                reason = ''
                result = product.virtual_available
                if result <= 0:
                    result = 0
                product.write({
                    'pcf_max_producible_qty': result
                })
                product.with_delay(max_retries=retries).webshop_api_stock(
                    api_config)
            log_items.append((0, 0, {
                'product_id': product.id,
                'status': status,
                'reason': reason
            }))

        if log_items:
            self.env['pcf.max.qty.log'].create({
                'date': fields.Datetime.now(),
                'user_id': self.env.user.id,
                'log_item_ids': log_items
            })
