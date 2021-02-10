{
    'name': 'Installation',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Installation
====================
    """,
    'website': 'https://on.net.my/',
    'depends': ['base_address_extended', 'portal',
                'markant_survey', 'markant_crm'],
    'data': [
        'security/base_security.xml',
        'security/ir.model.access.csv',

        'views/installation_report.xml',
        'data/installation_data.xml',
        'views/templates.xml',
        'views/installation_config_view.xml',
        'views/installation_view.xml',
        'views/website_installation_view.xml',
        'views/installation_report_dutch.xml',
    ],
    'installable': True,
    'auto_install': False,
}
