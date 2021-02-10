{
    'name': 'Markant Mass Mail',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Mass Mail
=================
    """,
    'website': 'https://on.net.my/',
    'depends': ['mass_mailing', 'link_tracker'],
    'data': [
        'security/markant_mass_mailing.xml',
        'views/mass_mail_views.xml',
        'views/partner_views.xml',
        'views/snippets_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
