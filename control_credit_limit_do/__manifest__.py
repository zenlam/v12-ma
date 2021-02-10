{
    'name': "Control Transfer by Credit Limit",
    'summary': "Allows a credit limit to be set for "
               "partners to control Delivery orders",
    'description': """
    Approve Transfer Based on customers pre-set credit limit
    """, 
    'images': ['images/odoo-control-credit-limit.png'],
    'author': "Onnet Consulting Sdn Bhd",
    'website': "https://on.net.my/",
    'category': 'Delivery', 
    'version': '12.0.1.0',
    'depends': ['control_credit_limit', 'stock', 'markant_stock'],
    'data': [
        'security/credit_limit_security.xml',
        'views/stock_picking_views.xml',
        'views/res_partner_views.xml',
        'views/sale_views.xml',
        'data/data.xml',
    ],
    'installable': True,
    'application': True,   
    'auto_install': False,
}
