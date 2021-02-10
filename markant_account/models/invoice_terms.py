# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import Warning


class ProformaPaymentTerm(models.Model):
    _name = "proforma.account.term"
    _description = " Pro-forma Payment Terms"
    _order = 'active desc'

    name = fields.Char('Pro-forma Terms', required=True)
    note = fields.Text('Pro-forma Description', required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(required=True, default=10)

    @api.constrains('active')
    def unique_active_terms(self):
        for proforma in self:
            term_ids = self.search([('id', '!=', proforma.id),
                                    ('active', '=', True)])
            if term_ids:
                raise Warning(_('There is already an existing '
                                'Pro-forma Term (%s) that is active!')
                              % term_ids.name)


class CustomerInvoiceTerms(models.Model):
    _name = "customer.invoice.term"
    _description = " Customer Invoice Terms"
    _order = 'active desc'

    name = fields.Char('Customer Invoice Terms', required=True)
    note = fields.Text('Customer Invoice Terms Description', required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(required=True, default=10)

    @api.constrains('active')
    def unique_active_terms(self):
        for invoice in self:
            term_id = self.search([('id', '!=', invoice.id),
                                    ('active', '=', True)])
            if term_id:
                raise Warning(_('There is already an existing active '
                                'Customer Invoice Term (%s)!')
                              % term_id.name)


class VendorBillTerms(models.Model):
    _name = "vendor.bill.term"
    _description = " Vendor Bill Terms"
    _order = 'active desc'

    name = fields.Char('Vendor Bill Terms', required=True)
    note = fields.Text('Vendor Bill Terms Description', required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(required=True, default=10)

    @api.constrains('active')
    def unique_active_terms(self):
        for vendor in self:
            term_id = self.search([('id', '!=', vendor.id),
                                    ('active', '=', True)])
            if term_id:
                raise Warning(_('There is already an existing active '
                                'Vendor Bill Term (%s)!')
                              % term_id.name)
