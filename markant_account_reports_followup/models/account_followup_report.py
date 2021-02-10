from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import append_content_to_html


class MailMail(models.Model):
    _inherit = 'mail.mail'

    markant_followup_mail = fields.Boolean(string='Followup Email')


class AccountFollowupReport(models.AbstractModel):
    _inherit = "account.followup.report"

    @api.model
    def send_email(self, options):
        """
        Send by mail the followup to the customer
        """
        partner = self.env['res.partner'].browse(options.get('partner_id'))
        email = self.env['res.partner'].browse(partner.address_get(['invoice'])['invoice']).email
        options['keep_summary'] = True

        # Find the reply_to from system parameter
        reply_to = self.env["ir.config_parameter"].sudo().get_param(
            "followup_reply_to_email")
        email_from = self.env["ir.config_parameter"].sudo().get_param(
            "followup_email_from")

        if email and email.strip():
            # When printing we need te replace the \n of the summary by <br /> tags
            body_html = self.with_context(print_mode=True, mail=True, lang=partner.lang or self.env.user.lang).get_html(options)
            start_index = body_html.find(b'<span>', body_html.find(b'<div class="o_account_reports_summary">'))
            end_index = start_index > -1 and body_html.find(b'</span>', start_index) or -1
            if end_index > -1:
                replaced_msg = body_html[start_index:end_index].replace(b'\n', b'<br />')
                body_html = body_html[:start_index] + replaced_msg + body_html[end_index:]
            msg = _('Follow-up email sent to %s') % email

            # ** MARKANT ** Do not post whole mail in chatter
            #
            # Remove some classes to prevent interactions with messages
            # msg += '<br>' + body_html.decode('utf-8') \
            #     .replace('o_account_reports_summary', '') \
            #     .replace('o_account_reports_edit_summary_pencil', '') \
            #     .replace('fa-pencil', '')

            msg_id = partner.message_post(body=msg, message_type='email')
            email = self.env['mail.mail'].create({
                'mail_message_id': msg_id.id,
                'subject': _('%s Payment Reminder') % (self.env.user.company_id.name) + ' - ' + partner.name,
                'body_html': append_content_to_html(body_html, self.env.user.signature or '', plaintext=False),
                'email_from': email_from or self.env.user.email or '',
                'email_to': email,
                'body': msg,
                'markant_followup_mail': True,
                'reply_to': reply_to or '',
            })
            partner.message_subscribe([partner.id])
            return True
        raise UserError(_('Could not send mail to partner because it does not have any email address defined'))


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def followup_email_history(self):
        action = self.env.ref('mail.action_view_mail_mail')
        result = action.read()[0]
        result['domain'] = [('markant_followup_mail', '=', True),
                            '|', ('email_to', '=', self.email),
                            ('recipient_ids', 'in', self.id)]
        result['name'] = 'Followup Emails'
        result['display_name'] = 'Followup Emails'
        return result
