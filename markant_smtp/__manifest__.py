{
    'name': 'Markant SMTP',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant SMTP Customization
============================
    """,
    'website': 'https://on.net.my/',
    'depends': ['base', 'mail', 'account_reports'],
    'data': [
        'views/res_config_settings_views.xml',
        'data/data.xml'
    ],
    'installable': True,
    'auto_install': False,
}
