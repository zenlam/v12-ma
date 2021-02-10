from odoo import api, fields, models, _


class VoipPhonecall(models.Model):
    _inherit = 'voip.phonecall'

    @api.model
    def _get_creation_group(self):
        if self.env.user.has_group('markant_crm.group_call_visit_director'):
            return self.env.ref('markant_crm.group_call_visit_director').id
        if self.env.user.has_group('markant_crm.group_call_visit_management'):
            return self.env.ref('markant_crm.group_call_visit_management').id
        if self.env.user.has_group('markant_crm.group_call_visit_purchase'):
            return self.env.ref('markant_crm.group_call_visit_purchase').id
        if self.env.user.has_group('markant_crm.group_call_visit_sales'):
            return self.env.ref('markant_crm.group_call_visit_sales').id
        return False

    @api.model
    def _get_real_group(self):
        if self.env.user.has_group('markant_crm.group_call_visit_director'):
            return [self.env.ref('markant_crm.group_call_visit_director').id]
        if self.env.user.has_group('markant_crm.group_call_visit_management'):
            return [self.env.ref('markant_crm.group_call_visit_management').id]
        if self.env.user.has_group('markant_crm.group_call_visit_purchase'):
            return [self.env.ref('markant_crm.group_call_visit_purchase').id]
        if self.env.user.has_group('markant_crm.group_call_visit_sales'):
            return [self.env.ref('markant_crm.group_call_visit_sales').id]
        return False

    @api.model
    def _get_domain(self):
        cate_group = self.env.ref(
            'markant_crm.module_category_call_visit_report').id

        creation_group = self._get_creation_group()

        director_group = self.env.ref(
            'markant_crm.group_call_visit_director').id
        management_group = self.env.ref(
            'markant_crm.group_call_visit_management').id
        purchase_group = self.env.ref(
            'markant_crm.group_call_visit_purchase').id

        groups = self.env['res.groups'].sudo().search([
            ('category_id', '=', cate_group)])

        if creation_group == director_group:
            groups = self.env['res.groups'].sudo().search([
                ('category_id', '=', cate_group),
                ('id', '!=', director_group)])

        if creation_group == management_group:
            groups = self.env['res.groups'].sudo().search([
                ('category_id', '=', cate_group),
                ('id', 'not in', [director_group, management_group])])

        if creation_group == purchase_group:
            groups = self.env['res.groups'].sudo().search([
                ('category_id', '=', cate_group),
                ('id', 'not in', [director_group,
                                  management_group,
                                  purchase_group])])
        return [('id', 'in', groups.ids)]

    display_creation_group = fields.Many2one(
        'res.groups', string='Creation Group', readonly=True,
        default=lambda self: self._get_creation_group())
    real_creation_group = fields.Many2many(
        'res.groups', relation='phonecall_real_group_res_group_rel',
        default=lambda self: self._get_real_group())
    group_to_release = fields.Many2many(
        'res.groups', relation='phonecall_group_release_res_group_rel',
        string='Group to Release', domain=_get_domain)
    set_from_action = fields.Boolean(stinrg='Default Values')

    @api.onchange('group_to_release', 'display_creation_group')
    def onchange_group_to_release(self):
        final_grp = self.group_to_release.ids + self.display_creation_group.ids
        self.real_creation_group = [(6, 0, final_grp)]

    @api.model
    def sync_old_report_category_to_new_field(self):
        for voip in self.search([]):
            if voip.report_category:
                if voip.report_category == 'incoming_phonecall':
                    voip.with_context(
                        already_gen_name=True).voip_report_cate_id = self.env.ref(
                        'markant_crm.incoming_phonecall').id or False
                elif voip.report_category == 'outgoing_phonecall':
                    voip.with_context(
                        already_gen_name=True).voip_report_cate_id = self.env.ref(
                        'markant_crm.outgoing_phonecall').id or False
                elif voip.report_category == 'complaint':
                    voip.with_context(
                        already_gen_name=True).voip_report_cate_id = self.env.ref(
                        'markant_crm.complaint').id or False
                elif voip.report_category == 'complaint_close':
                    voip.with_context(
                        already_gen_name=True).voip_report_cate_id = self.env.ref(
                        'markant_crm.complaint_close').id or False
                elif voip.report_category == 'showroom':
                    voip.with_context(
                        already_gen_name=True).voip_report_cate_id = self.env.ref(
                        'markant_crm.showroom').id or False
                elif voip.report_category == 'outbound_visit':
                    voip.with_context(
                        already_gen_name=True).voip_report_cate_id = self.env.ref(
                        'markant_crm.outbound_visit').id or False

    @api.onchange('partner_contact_ids')
    def onchange_partner_contact_ids(self):
        if self.env.context.get('phonecall_from_partner') and \
                not self.set_from_action:
            if self.partner_contact_ids and self.partner_contact_ids[0].parent_id:
                self.partner_ids = [
                    (6, 0, [self.partner_contact_ids[0].parent_id.id])]
            else:
                self.partner_ids = self.partner_contact_ids
                self.partner_contact_ids = False
            self.set_from_action = True
        return super(VoipPhonecall, self).onchange_partner_contact_ids()
