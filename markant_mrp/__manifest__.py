{
    'name': 'Markant Manufacturing',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Manufacturing Customization
===================================
    """,
    'website': 'https://on.net.my/',
    'depends': ['markant_stock', 'markant_landed_cost'],
    'data': [
        'reports/mrp_production_templates.xml',
        'reports/mrp_stock_to_pre_movement.xml',

        'views/mrp_production_views.xml',
        'views/product_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
