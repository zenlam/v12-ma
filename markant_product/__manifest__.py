{
    'name': 'Markant Product',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant Product Customization
=============================
    """,
    'website': 'https://on.net.my/',
    'depends': ['website_sale', 'sale_management',
                'web_enterprise', 'mrp_bom_cost'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',

        'data/product_data.xml',

        'views/templates.xml',
        'views/product_attribute_views.xml',
        'views/product_views.xml',
        'views/product_config_steps_views.xml',
        'views/sale_product_configurator_views.xml',
        'views/sale_product_configurator_templates.xml',
        'views/res_company_views.xml',
        'views/mrp_bom_views.xml',
        'views/product_template_attribute_lines_view.xml',
        'views/configurable_bom_mapping_line_view.xml',
        'views/markant_report_mrporder.xml',
        'views/product_translate_views.xml',

        'views/pcf_lookup_views.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'auto_install': False,
}
