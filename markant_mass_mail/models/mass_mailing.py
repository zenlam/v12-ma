from odoo import api, fields, models


class MassMailing(models.Model):
    _inherit = 'mail.mass_mailing'

    mail_template_id = fields.Many2one('mail.template', 'Email Template',
                                       readonly=True)
    link_ids = fields.One2many(related='mail_template_id.link_ids',
                               string='Links')

    # Fake Fields
    model_object_field = fields.Many2one('ir.model.fields', string="Field",
                                         help="Select target field from the "
                                              "related document model.\n"
                                              "If it is a relationship field "
                                              "you will be able to select "
                                              "a target field at the "
                                              "destination of the "
                                              "relationship.")
    sub_object = fields.Many2one('ir.model', 'Sub-model', readonly=True,
                                 help="When a relationship field is selected "
                                      "as first field, "
                                      "this field shows the document model "
                                      "the relationship goes to.")
    sub_model_object_field = fields.Many2one('ir.model.fields', 'Sub-field',
                                             help="When a relationship "
                                                  "field is selected as "
                                                  "first field, "
                                                  "this field lets you select "
                                                  "the target field "
                                                  "within the "
                                                  "destination document "
                                                  "model (sub-model).")
    null_value = fields.Char('Default Value',
                             help="Optional value to use if "
                                  "the target field is empty")
    copyvalue = fields.Char('Placeholder Expression',
                            help="Final placeholder expression, "
                                 "to be copy-pasted in the desired "
                                 "template field.")

    @api.onchange('model_object_field', 'sub_model_object_field', 'null_value')
    def onchange_sub_model_object_value_field(self):
        if self.model_object_field:
            if self.model_object_field.ttype in ['many2one',
                                                 'one2many', 'many2many']:
                model = self.env['ir.model']._get(
                    self.model_object_field.relation)
                if model:
                    self.sub_object = model.id
                    _field_name = self.sub_model_object_field and \
                                  self.sub_model_object_field.name or False
                    self.copyvalue = self.build_expression(
                        self.model_object_field.name, _field_name,
                        self.null_value or False)
            else:
                self.sub_object = False
                self.sub_model_object_field = False
                self.copyvalue = self.build_expression(
                    self.model_object_field.name, False,
                    self.null_value or False)
        else:
            self.sub_object = False
            self.copyvalue = False
            self.sub_model_object_field = False
            self.null_value = False

    def build_expression(self, field_name, sub_field_name, null_value):
        """Returns a placeholder expression for use in a template field,
        based on the values provided in the placeholder assistant.

        :param field_name: main field name
        :param sub_field_name: sub field name (M2O)
        :param null_value: default value if the target value is empty
        :return: final placeholder expression """
        expression = ''
        if field_name:
            expression = "${object." + field_name
            if sub_field_name:
                expression += "." + sub_field_name
            if null_value:
                expression += " or '''%s'''" % null_value
            expression += "}"
        return expression


class Statistics(models.Model):
    _inherit = "mail.mail.statistics"

    mail_template_id = fields.Many2one(
        related="mass_mailing_id.mail_template_id", readonly=True, store=True)
    opened_count = fields.Integer(related='mass_mailing_id.opened',
                                  string='Opened')
    opened = fields.Datetime('Last Opened')
    link_ids = fields.One2many(related="mail_template_id.link_ids",
                               string='Links',
                               context="{'email_to': email_to}")

    email_to = fields.Char('Email To')
    partner_id = fields.Many2one('res.partner', 'Partner')
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    title_id = fields.Many2one('res.partner.title', string='Title')
    company_name = fields.Char('Company Name')
    ref = fields.Char('Reference')

    @api.model
    def get_email_to_list(self, mail):
        email_list = []
        if mail.email_to:
            email_list += mail.send_get_mail_to(mail)
        for partner in mail.recipient_ids:
            email_list += mail.send_get_mail_to(mail, partner=partner)
        return email_list

    @api.model
    def create(self, vals):
        mail = self.mail_mail_id.browse(vals.get('mail_mail_id', 0))
        if mail:
            partner = False
            if mail.email_to:
                partner = self.partner_id.search(
                    [('email', '=', mail.email_to)], limit=1)
            elif mail.partner_ids:
                partner = mail.partner_ids[0]
            elif mail.recipient_ids:
                partner = mail.recipient_ids[0]

            if partner:
                email_list = [partner.email]
                if not partner.email:
                    email_list = self.get_email_to_list(mail)
                vals.update({
                    'email_to': ', '.join(email_list),
                    'partner_id': partner.id,
                    'first_name': partner.first_name,
                    'last_name': partner.last_name,
                    'ref': partner.ref,
                    'title_id': partner.title.id,
                    'company_name': partner.company_id.name,
                })
            elif vals.get('model') == 'mail.mass_mailing.contact':
                contact = self.env[vals['model']].browse(vals['res_id'])
                vals.update({
                    'email_to': contact.email,
                    'first_name': contact.name,
                    'last_name': contact.last_name,
                    'ref': contact.ref,
                    'title_id': contact.title_id.id,
                    'company_name': contact.company_name,
                })
        return super(Statistics, self).create(vals)


class Contact(models.Model):
    _inherit = "mail.mass_mailing.contact"
    _rec_name = 'full_name'

    name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    full_name = fields.Char('Full Name', compute="_compute_full_name")
    title_id = fields.Many2one('res.partner.title', string='Title')
    company_name = fields.Char('Company Name')
    ref = fields.Char('Reference')

    @api.depends('name', 'last_name')
    def _compute_full_name(self):
        for rec in self:
            nm = []
            if rec.title_id.name:
                nm.append(rec.title_id.name)
            if rec.name:
                nm.append(rec.name)
            if rec.last_name:
                nm.append(rec.last_name)
            rec.full_name = ' '.join(nm)
