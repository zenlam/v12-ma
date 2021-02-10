# -*- coding: utf-8 -*-

import werkzeug

from odoo import exceptions, fields, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class WebsiteInstallation(CustomerPortal):

    @http.route("/installation/<int:installation_id>",
                type='http', auth='public', website=True)
    def view(self, installation_id, report_type=None,
             access_token=None, download=False, **post):
        try:
            installation_sudo = self._document_check_access(
                'markant.installation.form', installation_id,
                access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('html', 'pdf', 'text'):
            if post.get('language') and post['language'] == 'EN':
                return self._show_report(
                    model=installation_sudo, report_type=report_type,
                    report_ref=
                    'markant_installation.action_report_installation',
                    download=download)
            if post.get('language') and post['language'] == 'NL':
                return self._show_report(
                    model=installation_sudo, report_type=report_type,
                    report_ref=
                    'markant_installation.action_report_installation_dutch',
                    download=download)

        if installation_sudo.send_signature_mail and \
                installation_sudo.send_signature_mail == 'force_send':
            installation_sudo.send_signature_email()
            installation_sudo.write({
                'send_signature_mail': 'sent'
            })

        values = {
            'installation': installation_sudo,
            'action': request.env.ref(
                'markant_installation.action_markant_installation_form').id,
            'session_user': request.session.uid,
            'no_breadcrumbs': True,
            'report_type': 'html',
        }
        return request.render('markant_installation.installation_preview',
                              values)

    @http.route(['/installation/accept/customer'], type='json',
                auth='public', website=True)
    def portal_installation_accept_customer(self, res_id, access_token=None,
                                            partner_name=None, signature=None):
        if not signature:
            return {'error': _('Signature is missing.')}

        try:
            installation_sudo = self._document_check_access(
                'markant.installation.form', res_id,
                access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        installation_sudo.write({
            'name_customer': partner_name,
            'signature_customer': signature
        })

        if installation_sudo.signature_customer and \
                installation_sudo.signature_mechanic:
            installation_sudo.write({
                'send_signature_mail': 'force_send'
            })

        return {
            'success': _('Installation Form Signed Successfully by Customer.'),
            'force_refresh': True,
            'redirect_url': installation_sudo.get_portal_url(),
        }

    @http.route(['/installation/accept/mechanic'], type='json',
                auth='public', website=True)
    def portal_installation_accept_mechanic(self, res_id, access_token=None,
                                            partner_name=None, signature=None):
        if not signature:
            return {'error': _('Signature is missing.')}

        try:
            installation_sudo = self._document_check_access(
                'markant.installation.form', res_id,
                access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        installation_sudo.write({
            'name_mechanic': partner_name,
            'signature_mechanic': signature
        })

        if installation_sudo.signature_customer and \
                installation_sudo.signature_mechanic:
            installation_sudo.write({
                'send_signature_mail': 'force_send'
            })

        return {
            'success': _('Installation Form Signed Successfully by '
                         'Head of Installation Team.'),
            'force_refresh': True,
            'redirect_url': installation_sudo.get_portal_url(),
        }

    @http.route(['/installation/pdf/<int:installation_id>/<access_token>'],
                type='http', auth="public", website=True)
    def portal_installation_report(self, installation_id,
                                   access_token=None, **kw):

        if access_token:
            Installation = request.env[
                'markant.installation.form'].sudo().search(
                [('id', '=', installation_id),
                 ('access_token', '=', access_token)])
        else:
            Installation = request.env['markant.installation.form'].search(
                [('id', '=', installation_id)])

        # print report as sudo
        pdf = request.env.ref(
            'markant_installation.action_report_installation'
        ).sudo().render_qweb_pdf([Installation.id])[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
