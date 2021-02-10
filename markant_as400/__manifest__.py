{
    'name': 'Markant AS400',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant AS400 System
====================

Module used for importing datas from AS400 to Odoo.
    """,
    'website': 'https://on.net.my/',
    'depends': ['markant_purchase', 'markant_stock', 'account_accountant',
                'markant_min_max_rules'],
    'data': [
        'security/ir.model.access.csv',

        'views/as400_views.xml',
    ],
    'installable': True,
}
