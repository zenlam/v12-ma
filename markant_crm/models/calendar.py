from odoo import api, fields, models


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    @api.multi
    def create_attendees(self):
        result = super(CalendarEvent, self).create_attendees()
        # meeting_attendees = result.get('new_attendees')
        current_user = self.env.user
        for record in self:
            meeting_attendees = result.get(record.id, {}).get('new_attendees')
            if meeting_attendees:
                to_notify = meeting_attendees.filtered(
                    lambda a: a.email == current_user.email)
                to_notify._send_mail_to_attendees(
                    'calendar.calendar_template_meeting_invitation')
        return result

    @api.model
    def default_get(self, fields):
        """
        To remove new event linking with calendar.event in Opportunity
        """
        if self.env.context.get('default_opportunity_id'):
            self = self.with_context(
                default_res_model_id=self.env.ref('crm.model_crm_lead').id,
                default_res_id=None,
                default_opportunity_id=None,
            )
        return super(CalendarEvent, self).default_get(fields)

    @api.model
    def create(self, vals):
        if vals.get('opportunity_id'):
            vals['opportunity_id'] = None
        return super(CalendarEvent, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('opportunity_id'):
            vals['opportunity_id'] = None
        return super(CalendarEvent, self).write(vals)

    def _sync_activities(self, values):
        # update activities
        if self.env.context.get('vp_event_write'):
            return
        return super(CalendarEvent, self)._sync_activities(values)
