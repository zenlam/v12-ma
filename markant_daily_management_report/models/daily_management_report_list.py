from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from datetime import date, datetime, timedelta
from pytz import timezone, UTC
from dateutil.relativedelta import relativedelta
from odoo.tools.float_utils import float_round


class DailyManagementReportList(models.Model):
    _name = "daily.management.report.list"
    _order = "report_date desc"

    report_date = fields.Date('Date')
    order_book = fields.Float(string="Order Book", digits=dp.get_precision(
        'Product Price'))
    current_month_ob = fields.Float(string="Current Month Order Book",
                                    digits=dp.get_precision(
                                        'Product Price'))
    next_month_ob = fields.Float(string="Next Month Order Book",
                                 digits=dp.get_precision(
                                     'Product Price'))
    total_invoiced = fields.Float(string="Total SO Invoiced",
                                  digits=dp.get_precision(
                                      'Product Price'))
    invoiced_margin_amount = fields.Float(string="SO Invoiced Margin Amount",
                                          digits=dp.get_precision(
                                              'Product Price'))
    invoiced_margin_percentage = fields.Float(string="SO Invoiced Margin %",
                                              digits=dp.get_precision(
                                                  'Product Price'))
    invoice_service = fields.Float(string="Invoice Service",
                                   digits=dp.get_precision(
                                       'Product Price'))
    invoice_service_product = fields.Float(string="Invoice Service Product",
                                           digits=dp.get_precision(
                                               'Product Price'))
    total_stock_value = fields.Float(string="Total Stock Value",
                                     digits=dp.get_precision(
                                         'Product Price'))
    total_invoiced_not_paid = fields.Float(string="Total Invoiced Not Paid",
                                           digits=dp.get_precision(
                                               'Product Price'))
    so_intake_today = fields.Float(string="Intake Mutations Today",
                                   digits=dp.get_precision(
                                       'Product Price'))
    so_intake_day = fields.Float(string="SO intake today",
                                   digits=dp.get_precision(
                                       'Product Price'))
    so_intake_margin_today = fields.Float(string="SO Intake Margin Today",
                                          digits=dp.get_precision(
                                              'Product Price'))

    def get_query_date(self):
        date = {}
        date['today'] = fields.Datetime.context_timestamp(self, datetime.now())
        date['offset'] = date['today'].utcoffset() / timedelta(hours=1)
        date['today'] = date['today'].replace(tzinfo=None).date()
        date['this_month_start'] = date['today'] + relativedelta(day=1)
        date['this_month_end'] = date['today'] + relativedelta(day=1,
                                                               months=+1,
                                                               days=-1)
        date['next_month_start'] = date['today'] + relativedelta(day=1,
                                                                 months=+1)
        date['next_month_end'] = date['today'] + relativedelta(day=1,
                                                               months=+2,
                                                               days=-1)
        return date

    def get_data(self):
        date_dict = self.get_query_date()

        wheres = {
            'this_month_start': datetime.combine(date_dict['this_month_start'],
                                                 datetime.min.time()) -
                                timedelta(hours=date_dict['offset']),
            'this_month_end': datetime.combine(date_dict['this_month_end'],
                                               datetime.max.time()) -
                              timedelta(hours=date_dict['offset']),
            'next_month_start': datetime.combine(date_dict['next_month_start'],
                                                 datetime.min.time()) -
                                timedelta(hours=date_dict['offset']),
            'next_month_end': datetime.combine(date_dict['next_month_end'],
                                               datetime.max.time()) -
                              timedelta(hours=date_dict['offset']),
            'today_start': datetime.combine(date_dict['today'],
                                            datetime.min.time()) -
                           timedelta(hours=date_dict['offset']),
            'today_end': datetime.combine(date_dict['today'],
                                          datetime.max.time()) -
                         timedelta(hours=date_dict['offset']),
            'today': date_dict['today']
        }

        query = """
        WITH all_book AS(
        SELECT
            sol.price_subtotal,
            sol.delivery_date,
            pp.stored_standard_price AS cost,
            sol.product_uom_qty,
            sol.qty_invoiced,
            pt.type,
            pt.product_group,
            so.confirmation_date,
            (sol.price_subtotal / sol.product_uom_qty) AS unit_price
        FROM 
            sale_order_line sol
            JOIN sale_order so ON sol.order_id = so.id
            JOIN product_product pp ON sol.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
        WHERE 
            so.state IN ('sale','done')
        AND sol.product_uom_qty > 0
        ),order_book AS(
            SELECT 
                SUM((ab.product_uom_qty - ab.qty_invoiced) * ab.unit_price) 
                AS current_ob 
            FROM 
                all_book ab
            WHERE 
                ab.product_group != 'service' OR ab.product_group IS NULL
        ),next_order_book AS( 
            SELECT 
                SUM((ab.product_uom_qty - ab.qty_invoiced) * ab.unit_price) 
                AS next_ob 
            FROM 
                all_book ab
            WHERE 
                ab.delivery_date BETWEEN '{next_month_start}' and '{next_month_end}'
            AND (ab.product_group != 'service' OR ab.product_group IS NULL)
        ),last_order_book AS(
            SELECT 
                SUM((ab.product_uom_qty - ab.qty_invoiced) * ab.unit_price) 
                AS this_ob 
            FROM 
                all_book ab
            WHERE 
                ab.delivery_date BETWEEN '{this_month_start}' and '{this_month_end}'
            AND (ab.product_group != 'service' OR ab.product_group IS NULL)
        ),total_so_invoiced AS(
            SELECT 
                SUM(ail.price_subtotal)
                AS total_invoiced_amt, 
                SUM(ail.price_subtotal - (pp.stored_standard_price * ail.quantity))
                AS total_invoice_margin_amt,
                SUM(ail.price_subtotal - (pp.stored_standard_price * ail.quantity)) * 100 / SUM(ail.price_subtotal)
                AS total_invoice_margin_percentage
            FROM account_invoice_line ail
                JOIN account_invoice ai ON ail.invoice_id = ai.id
                JOIN product_product pp ON ail.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                JOIN sale_order_line_invoice_rel solir ON ail.id = solir.invoice_line_id
                JOIN sale_order_line sol ON solir.order_line_id = sol.id
            WHERE
                CASE
                    WHEN ai.date_invoice IS NULL
                    THEN ai.create_date BETWEEN '{today_start}' AND '{today_end}'
                    ELSE ai.date_invoice = '{today}'
                END
            AND pt.product_group IS NULL
            AND ai.type = 'out_invoice'
        ),install_service AS(
            --SELECT
            --    SUM(ab.qty_invoiced * ab.unit_price)
            --    AS install_service
            --FROM
            --    all_book ab
            --WHERE
            --    ab.product_group = 'install'
            -----------------
            SELECT 
                SUM(ail.price_subtotal)
                AS install_service
            FROM 
                account_invoice_line ail
                JOIN product_product pp ON ail.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                JOIN account_invoice ai ON ail.invoice_id = ai.id
            WHERE 
                CASE
                    WHEN ai.date_invoice IS NULL
                    THEN ai.create_date BETWEEN '{today_start}' AND '{today_end}'
                    ELSE ai.date_invoice = '{today}'
                END
            AND pt.product_group = 'install'
            AND ai.type = 'out_invoice'
        ),service_product AS(
            --SELECT
            --    SUM(ab.qty_invoiced * ab.unit_price)
            --    AS service_product
            --FROM
            --    all_book ab
            --WHERE
            --    ab.product_group = 'service'
            -----------------------
            SELECT 
                SUM(ail.price_subtotal)
                AS service_product
            FROM 
                account_invoice_line ail
                JOIN product_product pp ON ail.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                JOIN account_invoice ai ON ail.invoice_id = ai.id
            WHERE 
                CASE
                    WHEN ai.date_invoice IS NULL
                    THEN ai.create_date BETWEEN '{today_start}' AND '{today_end}'
                    ELSE ai.date_invoice = '{today}'
                END
            AND pt.product_group = 'service'
            AND ai.type = 'out_invoice'
        ),invoiced_not_paid AS(
            SELECT 
                SUM(aml.debit) - SUM(aml.credit) 
                AS invoiced_not_paid 
            FROM 
                account_move_line aml
            JOIN account_account aa on aml.account_id = aa.id
            WHERE aa.is_daily_management = True
        ),so_today AS(
            SELECT 
                SUM(ab.price_subtotal) 
                AS so_intake_today,
                ((SUM(ab.unit_price)) - SUM(ab.cost)) * 100 / SUM(ab.unit_price) 
                AS so_intake_margin 
            FROM 
                all_book ab
            WHERE ab.confirmation_date BETWEEN '{today_start}' and '{today_end}'
            AND (ab.product_group != 'service' OR ab.product_group IS NULL)
            AND ab.unit_price > 0)
        SELECT 
            current_ob,
            next_ob,
            this_ob,
            total_invoiced_amt,
            total_invoice_margin_amt,
            total_invoice_margin_percentage,
            install_service,
            service_product,
            invoiced_not_paid,
            so_intake_today,
            so_intake_margin
        FROM 
            order_book,
            next_order_book,
            last_order_book,
            total_so_invoiced,
            install_service,
            service_product,
            invoiced_not_paid,
            so_today
        """.format(**wheres)

        self.env.cr.execute(query)
        data = self.env.cr.dictfetchall()
        return data

    def _create_record_cron(self):
        # if fields.Date.context_today(self).weekday() > 4:
        #     return

        def round_up(number):
            if number:
                rounded_number = float_round(number, precision_digits=0,
                                     rounding_method='HALF-UP')

                return int(rounded_number)
            return number

        date_dict = self.get_query_date()
        # total stock value
        Product = self.env['product.product'].search(
            [('type', '=', 'product')])
        stock_values = Product.mapped('stock_value')
        total_stock_value = sum(stock_values)

        datas = self.get_data()
        for data in datas:
            daily = self.create({
                'report_date': fields.Date.context_today(self),
                'order_book': round_up(data['current_ob']),
                'current_month_ob': round_up(data['this_ob']),
                'next_month_ob': round_up(data['next_ob']),
                'total_invoiced': round_up(data['total_invoiced_amt']),
                'invoiced_margin_amount': round_up(
                    data['total_invoice_margin_amt']),
                'invoiced_margin_percentage': data[
                    'total_invoice_margin_percentage'],
                'invoice_service': round_up(data['install_service']),
                'invoice_service_product': round_up(data['service_product']),
                'total_stock_value': round_up(total_stock_value),
                'total_invoiced_not_paid': round_up(data['invoiced_not_paid']),
                'so_intake_today': round_up(data['so_intake_today']),
                'so_intake_margin_today': data['so_intake_margin'],
            })
            query = """
                        WITH so_intake_day AS (
                            SELECT
                                id,
                                so_intake_today,
                                (order_book - (LAG(order_book,1) OVER (ORDER BY report_date)) + total_invoiced) as netto_intake
                            FROM   
                                daily_management_report_list
                        )
                        SELECT
                            id,
                            netto_intake
                        FROM   
                            so_intake_day
                        WHERE 
                            id={daily}
                    """.format(daily=daily.id)
            self.env.cr.execute(query)
            intake = self.env.cr.dictfetchall()
            for data in intake:
                daily.sudo().write({
                    'so_intake_day': round_up(data.get('netto_intake')) or 0.0,
                })
