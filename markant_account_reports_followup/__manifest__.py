{
    'name': 'Markant Account Reports Followup',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Account Reports Followup
================================
    """,
    'website': 'https://on.net.my/',
    'depends': ['account_reports_followup', 'markant_crm', 'markant_smtp'],
    'data': [
        'views/account_followup_views.xml',
    ],
    'installable': True,
}
