{
    'name': 'Markant Base Sync',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Base Sync
=================
    """,
    'website': 'https://on.net.my/',
    'depends': ['account', 'markant_crm', 'markant_mass_mail', 'voip'],
    'data': [
        'security/ir.model.access.csv',
        'data/markant_base_data.xml',
        'views/markant_base_views.xml',
        'views/res_config_views.xml',
        'views/markant_base_log_views.xml',
        'security/markant_base_sync_security.xml',
    ],
    'external_dependencies': {
        'python': [
            'basecrm',
        ],
    },
    'installable': True,
    'auto_install': False,
}
