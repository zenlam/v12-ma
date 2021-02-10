# -*- coding: utf-8 -*-

{
    'name': 'Markant Landed Cost',
    'version': '12.0.1.0.0',
    'author': 'Onnet Solution SDN BHD',
    'website': 'http://www.onnet.my',
    'depends': ['stock_landed_costs', 'landed_cost_average_price_product_app',
                'markant_purchase'],
    'description': """
Markant Landed Cost
===================    
    """,
    'data': [
        'data/stock_landed_cost.xml',

        'views/purchase_order.xml',
        'views/res_config_settings.xml',
        'views/res_partner.xml',
        'views/stock_landed_cost.xml',
        'views/stock_picking.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
