{
    'name': 'Markant CRM',
    'version': '12.0.1.0.0',
    'author': 'Onnet Consulting Sdn Bhd',
    'category': 'Hidden',
    'description': """
Markant CRM Customization
=========================
    """,
    'website': 'https://on.net.my/',
    'depends': ['calendar', 'bi_crm_claim', 'sale_crm',
                'purchase', 'markant_product', 'base_address_extended',
                'markant_phonecall', 'mass_mailing', 'account', 'partner_emails_history'],
    'data': [
        'security/markant_crm_security.xml',
        'security/ir.model.access.csv',

        'views/sale_markant_report.xml',
        'data/markant_data.xml',
        'data/post_object_function.xml',

        'wizard/opportunity_analysis_view.xml',
        'wizard/dealer_opportunity_info_create_wizard.xml',

        'views/templates.xml',
        'views/report_opportunity.xml',
        'views/report_sale_person_email_automation.xml',
        'views/markant_partner_view.xml',
        'views/markant_crm_view.xml',
        'views/sale_order_view.xml',
        'views/mail_activity_views.xml',
        'views/crm_claim_view.xml',
        'views/remove_default_filter.xml',
        'views/trouble_responsible_view.xml',
        'views/voip_phonecall_views.xml',
        'views/account_invoice_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
