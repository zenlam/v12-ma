from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class FileExtensionConfig(models.Model):
    _name = "file.extension.config"
    _description = "File Extension"

    name = fields.Char(string='File Extension', required=True)
    main_picture = fields.Boolean(string='Main Picture')
    more_picture = fields.Boolean(string='More Picture')
    pdf_setting = fields.Boolean(string='PDF Setting')
    default_main_picture = fields.Boolean(string='Default - Main Picture')
    default_more_picture = fields.Boolean(string='Default - More Picture')
    default_pdf_setting = fields.Boolean(string='Default - PDF Setting')

    def check_default_cond(self):
        main_count = 0
        more_count = 0
        pdf_count = 0
        for rec in self.search([]):
            if rec.default_main_picture:
                main_count += 1
            if rec.default_more_picture:
                more_count += 1
            if rec.default_pdf_setting:
                pdf_count += 1

            if main_count > 1 or more_count > 1 or pdf_count > 1:
                raise UserError(_('Can not set multiple values as default.'))

    @api.model
    def create(self, vals):
        res = super(FileExtensionConfig, self).create(vals)
        self.check_default_cond()
        return res

    @api.multi
    def write(self, vals):
        res = super(FileExtensionConfig, self).write(vals)
        self.check_default_cond()
        return res
