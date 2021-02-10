{
    'name': 'Special Form',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Special Form
====================
    """,
    'website': 'https://on.net.my/',
    'depends': ['portal', 'markant_crm'],
    'data': [
        'security/base_security.xml',
        'security/ir.model.access.csv',

        'data/special_form_data.xml',

        'views/special_form_config_view.xml',
        'views/special_form_view.xml',
        'views/special_report.xml',
    ],
    'installable': True,
    'auto_install': False,
}
