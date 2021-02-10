# -*- coding: utf-8 -*-

from odoo import tools
from odoo.osv import osv, expression
from odoo import api, fields, models, SUPERUSER_ID


class ir_rule(models.Model):
    _inherit = 'ir.rule'

    @api.model
    @tools.ormcache('self._uid', 'model_name', 'mode')
    def _compute_domain(self, model_name, mode="read"):
        if mode not in self._MODES:
            raise ValueError('Invalid mode: %r' % (mode,))

        res = self.pool['res.users'].has_group(cr, uid, 'markant_hr_rights.group_hr_super_manager')

        if self._uid == SUPERUSER_ID or res:
            return None

        query = """ SELECT r.id FROM ir_rule r JOIN ir_model m ON (r.model_id=m.id)
                    WHERE m.model=%s AND r.active AND r.perm_{mode}
                    AND (r.id IN (SELECT rule_group_id FROM rule_group_rel rg
                                  JOIN res_groups_users_rel gu ON (rg.group_id=gu.gid)
                                  WHERE gu.uid=%s)
                         OR r.global)
                """.format(mode=mode)
        self._cr.execute(query, (model_name, self._uid))
        rule_ids = [row[0] for row in self._cr.fetchall()]
        if not rule_ids:
            return []

        # browse user and rules as SUPERUSER_ID to avoid access errors!
        eval_context = self._eval_context()
        user_groups = self.env.user.groups_id
        global_domains = []                     # list of domains
        group_domains = []                      # list of domains
        for rule in self.browse(rule_ids).sudo():
            # evaluate the domain for the current user
            dom = safe_eval(rule.domain_force, eval_context) if rule.domain_force else []
            dom = expression.normalize_domain(dom)
            if not rule.groups:
                global_domains.append(dom)
            elif rule.groups & user_groups:
                group_domains.append(dom)

        # combine global domains and group domains
        return expression.AND(global_domains + [expression.OR(group_domains)])
    
