{
    'name': 'Markant Reports',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Reports
===============
Module helps to use different header/footer based on Partner/User country.

No need to enable Multi-Company feature of Odoo, in which we can do the same.

But this is something different for organizations which are running their 
business in different countries without enabling Multi-Company.
    """,
    'website': 'https://on.net.my/',
    'depends': ['web', 'purchase', 'account_reports'],
    'data': [
        'security/ir.model.access.csv',
        'data/report_paperformat.xml',

        'views/res_company_views.xml',
        'views/report_templates.xml',
        'views/report_followup.xml'
    ],
    'qweb': [],
    'installable': True,
    'auto_install': False,
}
