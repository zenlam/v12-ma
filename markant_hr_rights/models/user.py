# -*- coding: utf-8 -*-

from odoo import api, models


class User(models.Model):
    _inherit = 'res.users'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=500):
        """
            Show users in dropdown who has given groups
            pass context
            eg.
            context = {
                'check_groups': ['base.groupA', 'base.groupB']
            }
        """
        groups = self.env.context.get('check_groups')
        if groups:
            user_ids = []
            for user in self.search([]):
                if all(user.has_group(grp.strip()) for grp in groups) or user.has_group('markant_hr_rights.group_hr_super_manager'):
                    user_ids.append(user.id)
            args += [('id', 'in', user_ids)]
        return super(User, self).name_search(name, args=args, operator=operator, limit=limit)
