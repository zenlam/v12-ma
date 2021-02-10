# -*- coding: utf-8 -*-

from odoo import models, api


class PostObjectMarkant(models.TransientModel):
    _name = 'post.object.markant'
    _description = 'Post Object Markant'

    @api.model
    def sync_partner_type_from_company(self):
        """
        sync partner type from company to all company contact
        :return:
        """
        print('=== begin sync partner type ===')
        ResPartner = self.env['res.partner']
        list_companies = ResPartner.search([('is_company', '=', True)])
        for company in list_companies:
            list_contacts = ResPartner.search([('parent_id', '=', company.id)])
            list_contacts.write({'customer': company.customer,
                                 'end_user': company.end_user,
                                 'influencer': company.influencer,
                                 'supplier': company.supplier})
        print('=== end sync partner type ===')
        return True
