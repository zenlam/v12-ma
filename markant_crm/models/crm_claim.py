from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CrmClaimType(models.Model):
    _name = 'crm.claim.type'
    _description = 'CRM Claim Type'

    name = fields.Char(string='Name', required=True)


class CrmClaim(models.Model):
    _inherit = "crm.claim"

    claim_line_ids = fields.One2many(comodel_name='crm.claim.line',
                                     inverse_name='crm_claim_id',
                                     string='Claim Products')
    trouble_responsible_id = fields.Many2one('trouble.responsible',
                                             string='Trouble Responsible',
                                             ondelete='restrict')
    Warranty = fields.Selection(selection=[('yes', 'Yes'), ('no', 'No')],
                                string='Warranty')
    claim_type_id = fields.Many2one('crm.claim.type', string='Claim Type',
                                    required=True)
    supplier_id = fields.Many2one('res.partner', string='Partner')
    supplier_phone = fields.Char(string='Phone')
    supplier_email = fields.Char(string='Email')

    @api.onchange('supplier_id')
    def onchange_supplier_id(self):
        if self.supplier_id:
            self.supplier_phone = self.supplier_id.phone
            self.supplier_email = self.supplier_id.email

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            self.partner_phone = self.partner_id.phone
            self.email_from = self.partner_id.email

    @api.multi
    def unlink(self):
        for claim in self:
            if claim.trouble_responsible_id and \
                    claim.trouble_responsible_id.active:
                raise ValidationError(
                    _("You cannot delete this claim while trouble "
                      "responsible is active"))
        return super(CrmClaim, self).unlink()
