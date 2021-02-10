{
    'name': 'Webshop',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Webshop
====================
    """,
    'website': 'https://on.net.my/',
    'depends': ['web', 'markant_stock', 'queue_job'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'data/webshop_data.xml',

        'views/webshop_attribute_views.xml',
        'views/regular_attribute_views.xml',
        'views/product_attribute_views.xml',
        'views/product_brand_views.xml',
        'views/webshop_product_tags_views.xml',
        'views/product_views.xml',
        'views/templates.xml',
        'views/file_extension_config_views.xml',
        'views/webshop_api_config.xml',
        'views/webshop_api_log.xml',
        'views/webshop_fail_notif.xml',
        'views/webshop_res_partner_views.xml',
        'views/webshop_delivery_service.xml',
        'views/pcf_max_qty_log_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
