{
    'name': 'Markant Phone Call',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Phone Call Customization
================================
    """,
    'website': 'https://on.net.my/',
    'depends': ['voip', 'sms', 'crm'],
    'data': [
        'security/ir.model.access.csv',

        'data/data.xml',

        'views/templates.xml',
        'views/voip_phonecall_config_views.xml',
        'views/voip_phonecall_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
