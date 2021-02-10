{
    'name': 'Markant Account',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Account
===============
    """,
    'website': 'https://on.net.my/',
    'depends': ['account', 'sale_stock', 'purchase'],
    'data': [
        'security/ir.model.access.csv',

        'views/invoice_terms_view.xml',
        'views/invoice_views.xml',
        'views/invoices_bills_view.xml',
        'views/account_view.xml',

        'data/markant_invoice_data.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
