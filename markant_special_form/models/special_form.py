import threading

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class MarkantSpecialForm(models.Model):
    _name = 'markant.special.form'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = 'Special Form'
    _rec_name = 'name'

    name = fields.Char(string='Form Name', default='New')
    description = fields.Char(string='Description', required=True)
    project_id = fields.Many2one('crm.lead', string='Project')
    end_user_id = fields.Many2one('res.partner', string='End User Name')
    dealer_id = fields.Many2one('res.partner', string='Dealer')
    product_manager_id = fields.Many2one('res.users', string='Product Manager')
    article_no = fields.Char(string='Article Number')
    assignee_id = fields.Many2one('res.users', string='Assigned to',
                                  required=True)
    product_line_id = fields.Many2one('product.category',
                                      string='Product Line', required=True)
    quantity = fields.Integer(string='Quantity', required=True)
    info = fields.Html(string='Info')
    measurement = fields.Html(string='Measurements')
    material = fields.Html(string='Material')
    color = fields.Html(string='Color')
    comments = fields.Html(string='Comment')
    purchase_comments = fields.Html(string='Purchase Comments')
    r_d_comments = fields.Html(string='R&amp;D Comments')
    conclusion = fields.Html(string='Conclusion')
    gross_sale_price = fields.Float(string='Gross Sales Price')
    stage_id = fields.Many2one('markant.special.stage', string='Stage',
                               track_visibility='onchange', copy=False,
                               default=lambda self: self.env.ref(
                                   'markant_special_form.special_form_draft'))

    @api.model
    def create(self, vals):
        vals['name'] = \
            self.env['ir.sequence'].next_by_code('markant.special.form') \
            or '/'
        res = super(MarkantSpecialForm, self).create(vals)
        if res.assignee_id:
            users = res.assignee_id - self.env.user
            if users:
                partners = users.partner_id.ids
                if res.product_manager_id:
                    partners.append(res.product_manager_id.partner_id.id)
                res.message_subscribe(partners)
        return res

    @api.multi
    def write(self, vals):
        if vals.get('assignee_id'):
            assignee_user = self.env['res.users'].browse(vals['assignee_id'])
            users = assignee_user - self.env.user
            if users:
                partners = users.partner_id.ids
                if vals.get('product_manager_id'):
                    user_manager = self.env['res.users'].browse(
                        vals['product_manager_id'])
                    partners.append(user_manager.partner_id.id)
                self.message_subscribe(partners)

        res = super(MarkantSpecialForm, self).write(vals)

        if vals.get('stage_id'):
            recipients = []
            if self.stage_id.assign_mail:
                stage_type = 'assignment'
                assignee_name = self.assignee_id.name
                recipients.append(self.assignee_id.partner_id.id)
                if self.product_manager_id:
                    recipients.append(self.product_manager_id.partner_id.id)
                if stage_type and recipients:
                    self.action_send_mail(
                        stage_type, assignee_name, recipients)

            if self.stage_id.approve_mail and \
                    self.create_uid.id != self.env.uid:
                stage_type = 'approval'
                assignee_name = self.assignee_id.name
                recipients.append(self.create_uid.partner_id.id)
                if stage_type and recipients:
                    self.action_send_mail(
                        stage_type, assignee_name, recipients)

            if self.stage_id.reject_mail and \
                    self.create_uid.id != self.env.uid:
                stage_type = 'reject'
                assignee_name = self.assignee_id.name
                recipients.append(self.create_uid.partner_id.id)
                if stage_type and recipients:
                    self.action_send_mail(
                        stage_type, assignee_name, recipients)
        return res

    @api.constrains('info')
    def check_info(self):
        empty_html = '<p><br></p>'
        if self.info == empty_html:
            raise ValidationError(_("Info should not be EMPTY."))

    @api.constrains('quantity')
    def check_qty(self):
        if self.quantity <= 0:
            raise ValidationError(_("Quantity should not less "
                                    "than or equal to ZERO."))

    @api.multi
    def action_send_mail(self, stage_type=None,
                         assignee_name=None, recipients=None):
        self.ensure_one()
        if stage_type == 'assignment':
            template = self.env.ref(
                'markant_special_form.email_template_special_assign')
        elif stage_type == 'approval':
            template = self.env.ref(
                'markant_special_form.email_template_special_approve')
        elif stage_type == 'reject':
            template = self.env.ref(
                'markant_special_form.email_template_special_reject')
        else:
            template = False
        if template and recipients:
            recipients_str = ','.join(str(e) for e in recipients)
            template.with_context(
                follower_name=assignee_name,
                follower_partner=recipients_str).send_mail(self.id,
                                                           force_send=True)
        return True
