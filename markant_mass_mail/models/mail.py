from odoo import fields, models


class EmailTemplate(models.Model):
    _inherit = "mail.template"

    link_ids = fields.One2many('link.tracker', 'template_id', string='Links')
    tmp_add = fields.Char('Temp Field')


class LinkTracker(models.Model):
    _inherit = "link.tracker"

    template_id = fields.Many2one('mail.template', string='Template ID')
    last_clicked_date = fields.Date(related='link_click_ids.click_date',
                                    string='Last Date Clicked')
