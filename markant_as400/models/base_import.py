# -----------------------------------------------------------------------------
# Not advisable to do this type of development because,
# it's affect base import code.
# But it's done due to special request.
#
# **NOTE**: Remove/Uninstall this module ASAP,
# as from requirements we already know that this module is just
# created for limited time when we achieve the excepted result then
# no need of this module anymore and it's good to uninstall it.
# -----------------------------------------------------------------------------
from odoo import api, fields, models, _
from odoo.exceptions import Warning


class Import(models.TransientModel):
    _inherit = 'base_import.import'

    @api.model
    def _convert_import_data(self, fields, options):

        data, import_fields = super(Import, self)._convert_import_data(
            fields, options)
        if self.res_model == 'as400.product':
            currency_index = import_fields.index('currency')
            all_currency = [d[currency_index] for d in data]
            currency_set = list(set(all_currency))
            currency_obj = self.env['res.currency'].sudo().search(
                [('name', 'in', currency_set)])
            if len(currency_set) != len(currency_obj):
                raise Warning(_('User try to import currencies which does '
                                'not exists or active inside the system.'))
        return data, import_fields
