{
    'name': 'Markant Purchase',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Sale
=================
    """,
    'website': 'https://on.net.my/',
    'depends': ['base', 'purchase_requisition', 'markant_generic',
                'markant_crm', 'markant_stock'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'data/data.xml',
        'views/purchase_views.xml',
        'views/purchase_report_template.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/purchase_advice_views.xml',
        'wizard/po_line_schedule_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
