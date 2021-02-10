from odoo import models, fields
from datetime import datetime
from pytz import timezone, UTC
from collections import OrderedDict


class JanBeltmanReport(models.AbstractModel):
    _name = 'report.daily_management_report_wiz'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, wb, data, report):
        report_name = 'Daily Management Report'
        ws = wb.add_worksheet(report_name)
        self.set_paper(wb, ws)
        self.styles = self.get_report_styles(wb)
        self.set_header(ws, report)
        data = self.get_data(report)
        self.bind_data(ws, data, report)

    def set_paper(self, wb, ws):
        wb.formats[0].font_name = 'Times New Roman'
        wb.formats[0].font_size = 12
        ws.set_paper(9)
        ws.set_margins(left=0.28, right=0.28, top=0.5, bottom=0.5)
        ws.fit_to_pages(1, 0)
        ws.set_landscape()
        ws.set_column(0, 12, 25)

    def get_report_styles(self, wb):
        styles = {}

        styles['header'] = wb.add_format({
            'bold': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 12,
            'border': 1,
        })
        styles['column_header'] = wb.add_format({
            'bold': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 12,
            'border': 1,
            'fg_color': '#F5DD13',
        })
        styles['data_left'] = wb.add_format({
            'bold': 0,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 12,
            'border': 0,
        })
        styles['data_right'] = wb.add_format({
            'bold': 0,
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 12,
            'border': 0,
        })
        styles['data_right_bold'] = wb.add_format({
            'bold': 1,
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 12,
            'border': 0,
        })
        styles['date'] = wb.add_format({
            'bold': 0,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 12,
            'num_format': 'dd/mm/yyyy',
            'border': 0,
        })
        styles['num_data'] = wb.add_format({
            'bold': 0,
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 12,
            'num_format': '#,##0.00',
            'border': 0,
        })
        styles['num_data_bold'] = wb.add_format({
            'bold': 1,
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 12,
            'num_format': '#,##0.00',
            'border': 0,
        })

        return styles

    def set_header(self, ws, report):
        row = 0
        col = 0
        ws.write(row, col, 'Date', self.styles['column_header'])
        col += 1
        ws.write(row, col, 'Order Book', self.styles['column_header'])
        col += 1
        ws.write(row, col, 'Open SO Delivery date this month',
                 self.styles['column_header'])
        col += 1
        ws.write(row, col, 'Open SO Delivery date next month',
                 self.styles['column_header'])
        col += 1
        ws.write(row, col, 'Total Invoiced', self.styles['column_header'])
        col += 1
        ws.write(row, col, 'Sales Invoice Margin Amount',
                 self.styles['column_header'])
        col += 1
        ws.write(row, col, 'Sale Invoice Margin %',
                 self.styles['column_header'])
        col += 1
        ws.write(row, col, 'Sales Invoice Service',
                 self.styles['column_header'])
        col += 1
        ws.write(row, col, 'Sales Invoice Service Product',
                 self.styles['column_header'])
        col += 1
        ws.write(row, col, 'Total Stock Value',
                 self.styles['column_header'])
        col += 1
        ws.write(row, col, 'Total Invoiced not paid',
                 self.styles['column_header'])
        col += 1
        ws.write(row, col, 'Intake Mutations Today',
                 self.styles['column_header'])
        col += 1
        ws.write(row, col, 'SO Intake Today',
                 self.styles['column_header'])
        col += 1
        ws.write(row, col, 'SO Intake Margin',
                 self.styles['column_header'])

    def bind_data(self, ws, data, report):
        row = 1
        col = 0
        for keys, vals in data.items():
            for keys2, vals2 in vals.items():
                total_invoiced = 0
                total_invoiced_margin_amount = 0
                total_invoice_service = 0
                total_so_intake_today = 0
                count = 0
                for line in vals2:
                    count += 1
                    total_invoiced += line['total_invoiced']
                    total_invoiced_margin_amount += line[
                        'invoiced_margin_amount']
                    total_invoice_service += line['invoice_service']
                    total_so_intake_today += line['so_intake_today']
                    col = 0
                    ws.write(row, col, line['report_date'],
                             self.styles['date'])
                    col += 1
                    ws.write(row, col, line['order_book'],
                             self.styles['num_data'])
                    col += 1
                    ws.write(row, col, line['current_month_ob'],
                             self.styles['num_data'])
                    col += 1
                    ws.write(row, col, line['next_month_ob'],
                             self.styles['num_data'])
                    col += 1
                    ws.write(row, col, line['total_invoiced'],
                             self.styles['num_data'])
                    col += 1
                    ws.write(row, col, line['invoiced_margin_amount'],
                             self.styles['num_data'])
                    col += 1
                    ws.write(row, col, line['invoiced_margin_percentage'],
                             self.styles['num_data'])
                    col += 1
                    ws.write(row, col, line['invoice_service'],
                             self.styles['num_data'])
                    col += 1
                    ws.write(row, col, line['invoice_service_product'],
                             self.styles['num_data'])
                    col += 1
                    ws.write(row, col, line['total_stock_value'],
                             self.styles['num_data'])
                    col += 1
                    ws.write(row, col, line['total_invoiced_not_paid'],
                             self.styles['num_data'])
                    col += 1
                    ws.write(row, col, line['so_intake_today'],
                             self.styles['num_data'])
                    col += 1
                    ws.write(row, col, line['so_intake_day'],
                             self.styles['num_data'])
                    col += 1
                    ws.write(row, col, line['so_intake_margin_today'],
                             self.styles['num_data'])
                    row += 1

                row += 1
                col = 3
                ws.write(row, col, 'TOTAL', self.styles['data_right_bold'])
                ws.write(row, 4, total_invoiced, self.styles['num_data_bold'])
                ws.write(row, 5, total_invoiced_margin_amount,
                         self.styles['num_data_bold'])
                ws.write(row, 7, total_invoice_service,
                         self.styles['num_data_bold'])
                ws.write(row, 11, total_so_intake_today,
                         self.styles['num_data_bold'])
                row += 1
                col = 3
                ws.write(row, col, 'AVG', self.styles['data_right_bold'])
                ws.write(row, 4, total_invoiced / count,
                         self.styles['num_data_bold'])
                ws.write(row, 5, total_invoiced_margin_amount / count,
                         self.styles['num_data_bold'])
                ws.write(row, 7, total_invoice_service / count,
                         self.styles['num_data_bold'])
                ws.write(row, 11, total_so_intake_today / count,
                         self.styles['num_data_bold'])
                row += 2

    def get_data(self, report):
        today = fields.Date.context_today(self)

        if not report.start_date:
            sql = '''
                    SELECT * 
                    FROM 
                        daily_management_report_list
                    ORDER BY report_date DESC
                    '''
        else:
            sql = '''
                    SELECT * 
                    FROM 
                        daily_management_report_list
                    WHERE report_date BETWEEN '{start_date}' and '{today}'
                    ORDER BY report_date DESC
                    '''.format(start_date=report.start_date, today=today)
        self.env.cr.execute(sql)
        data = self.env.cr.dictfetchall()
        # sub-grouping data
        data_lines = {}
        for line in data:
            month = line['report_date'].month
            year = line['report_date'].year
            if year not in data_lines:
                data_lines[year] = {}
            if month not in data_lines[year]:
                data_lines[year][month] = []
            data_lines[year][month].append(line)
            data_lines = OrderedDict(sorted(data_lines.items(), reverse=True))
        return data_lines
