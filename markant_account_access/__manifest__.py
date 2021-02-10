{
    'name': 'Markant Account Access',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Account Access
======================
    """,
    'website': 'https://on.net.my/',
    'depends': ['payment', 'markant_account_reports_followup',
                'markant_account', 'markant_sale'],
    'data': [
        'security/base_security.xml',

        'views/account_menuitem.xml',
        'views/partner_view.xml',
        'views/sale_views.xml',
    ],
    'installable': True,
}
