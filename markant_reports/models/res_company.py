from odoo import api, fields, models, _
from odoo.exceptions import Warning


class CountryReportFormats(models.Model):
    _name = 'country.report.formats'
    _description = 'Country Report Formats'

    company_id = fields.Many2one('res.company', string='Company')
    set_as_global = fields.Boolean(string='Used as Global')
    country_id = fields.Many2one('res.country', string='Country',
                                 required=True)
    header_info = fields.Html(string='Header Content')
    footer_info = fields.Html(string='Footer Content')


class Company(models.Model):
    _inherit = 'res.company'

    allow_report_format = fields.Boolean(string='Custom Report Format',
                                         help='For Developer: Only works for '
                                              'reports which '
                                              'using `external_layout` while '
                                              'developing any report '
                                              'for any module.')
    report_header_img = fields.Binary(string='Header Background Image',
                                      attachment=True, required=True)
    report_footer_img = fields.Binary(string='Footer Background Image',
                                      attachment=True, required=True)
    country_report_ids = fields.One2many('country.report.formats',
                                         'company_id', string='Report Formats')
    hide_tax_column = fields.Boolean(string='Hide Tax Column', default=False)

    @api.multi
    def write(self, vals):
        res = super(Company, self).write(vals)
        for rec in self:
            if rec.allow_report_format:
                if not rec.country_report_ids:
                    raise Warning(_('Please, Define Report Formats!'))
                check_for_global = []
                for country_report in rec.country_report_ids:
                    check_for_global.append(country_report.set_as_global)
                if True not in check_for_global:
                    raise Warning(_('You did not define Global Report '
                                    'format. \n'
                                    'Please, Assign Used as Global to any of '
                                    'existing report format.'))
                if check_for_global.count(True) > 1:
                    raise Warning(_('You can not assign Used as Global to '
                                    'more than one report format.'))
        return res
