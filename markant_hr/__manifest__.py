# -*- coding: utf-8 -*-

{
    'name': 'Markant HR',
    'version': '12.0.1.0.0',
    'author': 'Onnet Solution SDN BHD',
    'website': 'http://www.onnet.my',
    'depends': ['hr_holidays', 'hr_contract'],
    'description': '''
    ''',
    'data': [
        'data/markant_hr_data.xml',
        'security/ir.model.access.csv',

        'views/markant_hr_templates.xml',
        'views/markant_hr_view.xml',
    ],
    'installable': True,
}
