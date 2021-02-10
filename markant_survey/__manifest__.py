{
    'name': 'Markant Survey',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Survey Customization
============================
    """,
    'website': 'https://on.net.my/',
    'depends': ['markant_product', 'web_widget_color'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'data/survey_data.xml',

        'views/templates.xml',
        'views/survey_view.xml',
        'views/carrier_view.xml',
        'views/survey_report_view.xml',
        'views/uom_category_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
