# -*- coding: utf-8 -*-

import base64
import re

from odoo import _, api, fields, models, SUPERUSER_ID, tools
from odoo.tools import pycompat
from odoo.tools.safe_eval import safe_eval
from odoo.tools import append_content_to_html
from odoo.exceptions import UserError

# main mako-like expression pattern
EXPRESSION_PATTERN = re.compile('(\$\{.+?\})')


class MailComposer(models.TransientModel):
   
    _inherit = 'mail.compose.message'


    @api.multi
    def get_mail_values(self, res_ids):
        res = super(MailComposer, self).get_mail_values(res_ids)
        if self.template_id and self.template_id.reply_to:
            for key, value in res.items():
                if not value.get('reply_to', False):
                    res[key]['reply_to'] = self.template_id.reply_to
        return res

class AccountFollowupReport(models.AbstractModel):
    _inherit = "account.followup.report"

    # Overide method to add reply_to inside the mail
    @api.model
    def send_email(self, options):
        """
        Send by mail the followup to the customer
        """
        partner = self.env['res.partner'].browse(options.get('partner_id'))
        email = self.env['res.partner'].browse(partner.address_get(['invoice'])['invoice']).email
        options['keep_summary'] = True

        # Find the reply_to from system parameter
        reply_to = self.env["ir.config_parameter"].sudo().get_param("followup_reply_to_email")
        email_from = self.env["ir.config_parameter"].sudo().get_param(
            "followup_email_from")
        # end
        if email and email.strip():
            # When printing we need te replace the \n of the summary by <br /> tags
            body_html = self.with_context(print_mode=True, mail=True, lang=partner.lang or self.env.user.lang).get_html(options)
            start_index = body_html.find(b'<span>', body_html.find(b'<div class="o_account_reports_summary">'))
            end_index = start_index > -1 and body_html.find(b'</span>', start_index) or -1
            if end_index > -1:
                replaced_msg = body_html[start_index:end_index].replace(b'\n', b'<br />')
                body_html = body_html[:start_index] + replaced_msg + body_html[end_index:]
            msg = _('Follow-up email sent to %s') % email
            # Remove some classes to prevent interactions with messages
            msg += '<br>' + body_html.decode('utf-8')\
                .replace('o_account_reports_summary', '')\
                .replace('o_account_reports_edit_summary_pencil', '')\
                .replace('fa-pencil', '')
            msg_id = partner.message_post(body=msg, message_type='email')

            # custom code to add reply_to email
            vals = {
                'mail_message_id': msg_id.id,
                'subject': _('%s Payment Reminder') % (self.env.user.company_id.name) + ' - ' + partner.name,
                'body_html': append_content_to_html(body_html, self.env.user.signature or '', plaintext=False),
                'email_from': email_from or self.env.user.email or '',
                'email_to': email,
                'body': msg,
            }
            if reply_to:
                vals['reply_to'] = reply_to
            email = self.env['mail.mail'].create(vals)
            # custom code end

            partner.message_subscribe([partner.id])
            return True
        raise UserError(_('Could not send mail to partner because it does not have any email address defined'))
