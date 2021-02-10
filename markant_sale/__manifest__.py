{
    'name': 'Markant Sale',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Sale
=================
    """,
    'website': 'https://on.net.my/',
    'depends': ['base', 'sale', 'sale_margin', 'markant_generic',
                'markant_product', 'markant_survey', 'markant_crm', 'sale_timesheet',
                'markant_installation'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/markant_sale_views.xml',
        'views/markant_sale_templates.xml',
        'views/order_cycle_view.xml',
        'views/res_company_view.xml',
        'report/markant_sale_report.xml',
        'data/markant_data.xml',
        'views/markant_account_invoice_views.xml',
        'wizard/markant_project_create_sale_order_views.xml',
        'static/src/xml/base.xml',
    ],
    'installable': True,
    'auto_install': False,
}
