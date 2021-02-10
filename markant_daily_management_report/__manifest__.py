{
    'name': 'Markant Daily Management Report',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Daily Management Report
===============================
    """,
    'website': 'https://on.net.my/',
    'depends': ['sale', 'account', 'report_xlsx_helper'],
    'data': [
        'views/daily_management_report_list.xml',
        'views/product_template.xml',
        'views/account_account.xml',
        'wizard/daily_management_report_wiz.xml',
        'data/ir_cron.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}
