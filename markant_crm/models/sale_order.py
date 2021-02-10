from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # partner_id = fields.Many2one(required=False)
    # partner_invoice_id = fields.Many2one(required=False)
    # partner_shipping_id = fields.Many2one(required=False)
    # pricelist_id = fields.Many2one(required=False)
    # currency_id = fields.Many2one(required=False)

    # for partner creation required field
    partner_name = fields.Char(string='Customer Name')
    contact_name = fields.Char(string='Contact Name')
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    zip = fields.Char(string='Zip')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country')
    phone = fields.Char(string='Phone')
    fax = fields.Char(string='Fax')
    mobile = fields.Char(string='Mobile')
    function = fields.Char(string='Function')
    title = fields.Many2one('res.partner.title', string='Title')
    description = fields.Text(string='Description')
    email_from = fields.Char(string='Email')

    influencer_ids = fields.Many2many('res.partner', domain=[('influencer', '=', True)])

    @api.multi
    def _lead_create_contact(self):
        self.ensure_one()
        Partner = self.env['res.partner']
        parnter_vals = {
            'name': self.partner_name,
            'user_id': self.user_id.id,
            'comment': self.description,
            'section_id': self.section_id.id,
            'phone': self.phone,
            'mobile': self.mobile,
            'email': self.email_from,
            'fax': self.fax,
            'title': self.title.id,
            'function': self.function,
            'street': self.street,
            'street2': self.street2,
            'zip': self.zip,
            'city': self.city,
            'country_id': self.country_id.id,
            'state_id': self.state_id.id,
            'is_company': True,
            'type': 'contact'
        }
        partner = Partner.create(parnter_vals)

        if self.contact_name:
            contact_vals = {
                'name': self.partner_name,
                'user_id': self.user_id.id,
                'comment': self.description,
                'section_id': self.section_id.id,
                'phone': self.phone,
                'mobile': self.mobile,
                'email': self.email_from,
                'fax': self.fax,
                'title': self.title.id,
                'function': self.function,
                'street': self.street,
                'street2': self.street2,
                'zip': self.zip,
                'city': self.city,
                'country_id': self.country_id.id,
                'state_id': self.state_id.id,
                'is_company': False,
                'type': 'contact',
                'parent_id': partner.id,
            }
            Partner.create(contact_vals)
        self.write({
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'pricelist_id': partner.property_product_pricelist.id,
        })
        return partner

    @api.multi
    def action_create_partner(self):
        if not self.partner_name:
            raise ValidationError(
                _('Warning!\nPlease fill up Customer Name first.'))
        self._lead_create_contact()

    @api.multi
    def onchange_state(self, state_id):
        if state_id:
            country_id = self.env['res.country.state'].browse(
                state_id).country_id.id
            return {'value': {'country_id': country_id}}
        return {}

    @api.multi
    def action_button_confirm(self):
        assert len(self.ids) == 1
        if not self.partner_id:
            raise ValidationError(
                _('Warning!\nPartner not assign. First create partner first.'))

        if not self.partner_id.credit_limit or \
                not self.partner_id.property_payment_term:
            raise ValidationError(
                _('Warning!\nFirst set Credit Limit and '
                  'Payment Term for this partner.'))
        return super(SaleOrder, self).action_button_confirm()

    @api.model
    def create(self, vals):
        record = super(SaleOrder, self).create(vals)
        if vals.get('opportunity_id'):
            stage = self.env['crm.stage'].search([
                ('quotation_stage', '=', True)], limit=1)
            if stage:
                record.opportunity_id.write({'stage_id': stage.id})
        return record
