from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo.tools import float_round


class StockQuantityHistory(models.TransientModel):
    _inherit = 'stock.quantity.history'

    start_date = fields.Datetime('Start Date')
    no_of_days = fields.Integer('# of days after start date')

    def get_all_lines(self):
        start_date = self.start_date
        no_of_days = self.no_of_days
        all_dates = [start_date]
        datas = []

        for x in range(no_of_days):
            next_date = start_date + timedelta(days=x+1)
            all_dates.append(next_date)

        StockMove = self.env['stock.move']
        for to_date in all_dates:
            self.env.context = dict(self.env.context, to_date=to_date, company_owned=True)
            products = self.env['product.product'].with_context(self.env.context).search([
                ('type', '=', 'product'),
                ('qty_available', '!=', 0)])

            real_time_product_ids = [
                product.id for product in products
                if product.product_tmpl_id.valuation == 'real_time']
            if real_time_product_ids:
                self.env['account.move.line'].check_access_rights('read')
                fifo_automated_values = {}
                query = """SELECT aml.product_id, aml.account_id, sum(aml.debit) - sum(aml.credit), sum(quantity), array_agg(aml.id)
                        FROM account_move_line AS aml
                        WHERE aml.product_id IN %%s AND aml.company_id=%%s %s
                        GROUP BY aml.product_id, aml.account_id"""
                params = (tuple(real_time_product_ids),
                          self.env.user.company_id.id)

                query = query % ('AND aml.date <= %s',)
                params = params + (to_date,)

                self.env.cr.execute(query, params=params)

                res = self.env.cr.fetchall()
                for row in res:
                    fifo_automated_values[(row[0], row[1])] = \
                        (row[2], row[3], list(row[4]))

            product_values = {product.id: 0 for product in products}
            product_move_ids = {product.id: [] for product in products}

            domain = [('product_id', 'in', self.ids),
                      ('date', '<=', to_date)] + \
                     StockMove._get_all_base_domain()
            value_field_name = 'value'

            StockMove.check_access_rights('read')
            query = StockMove._where_calc(domain)
            StockMove._apply_ir_rules(query, 'read')
            from_clause, where_clause, params = query.get_sql()
            query_str = """
                SELECT stock_move.product_id, SUM(COALESCE(stock_move.{}, 0.0)), ARRAY_AGG(stock_move.id)
                FROM {}
                WHERE {}
                GROUP BY stock_move.product_id
            """.format(value_field_name, from_clause, where_clause)

            self.env.cr.execute(query_str, params)
            for product_id, value, move_ids in self.env.cr.fetchall():
                product_values[product_id] = value
                product_move_ids[product_id] = move_ids

            total_sum = 0.0
            for product in products:
                product_stock_value = 0.0
                if product.cost_method in ['standard', 'average']:
                    qty_available = product.with_context(
                        company_owned=True, owner_id=False).qty_available
                    price_used = product.get_history_price(
                        self.env.user.company_id.id,
                        date=to_date,
                    )
                    product_stock_value = price_used * qty_available
                elif product.cost_method == 'fifo':
                    if product.product_tmpl_id.valuation == 'manual_periodic':
                        product_stock_value = product_values[product.id]
                    elif product.product_tmpl_id.valuation == 'real_time':
                        valuation_account_id = product.categ_id.property_stock_valuation_account_id.id
                        value, quantity, aml_ids = \
                            fifo_automated_values.get(
                                (product.id, valuation_account_id)) or \
                            (0, 0, [])
                        product_stock_value = value
                total_sum += product_stock_value

            prec = self.env['decimal.precision'].precision_get('Product Price')
            total_sum_round = float_round(total_sum, precision_digits=prec)
            datas.append({
                'date': to_date,
                'value': total_sum_round
            })
        return datas

    @api.multi
    def print_report(self):
        self.ensure_one()
        self.env['stock.move']._run_fifo_vacuum()
        if self.start_date and (0 <= self.no_of_days <= 15):
            return self.env.ref(
                'markant_stock.report_stock_quantity_history_by_datetime'
            ).report_action(self)
        else:
            raise Warning(_('Invalid input data!'))
