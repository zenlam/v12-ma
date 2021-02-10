# -*- coding: utf-8 -*-

{
    'name': 'Markant HR Rights',
    'version': '12.0.1.0.0',
    'author': 'Onnet Solution SDN BHD',
    'website': 'http://www.onnet.my',
    'depends': ['markant_hr', 'hr_org_chart', 'hr_expense'],
    'description': '''
    ''',
    'data': [
        'security/hr_security.xml',
        'security/ir.model.access.csv',
        'data/hr_data.xml',
        'views/markant_hr_rights_views.xml',
        'views/hr_views.xml',
    ],
    'installable': True,
}
