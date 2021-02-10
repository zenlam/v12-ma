{
    'name': 'Markant Negative PO/SO',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Negative PO/SO
======================
    """,
    'website': 'https://on.net.my/',
    'depends': ['purchase', 'purchase_requisition', 'sale'],
    'data': [
        'views/purchase_order.xml',
        'views/sale_order.xml',
        'views/stock_return_picking.xml',
        'data/data.xml',
    ],
    'installable': True,
    'auto_install': False,
}
