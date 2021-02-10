{
    'name': 'Markant Generic',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Generic
=================
    """,
    'website': 'https://on.net.my/',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/order_cycle_view.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
