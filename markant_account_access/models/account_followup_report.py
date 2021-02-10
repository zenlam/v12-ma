from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountFollowupReport(models.AbstractModel):
    _inherit = "account.followup.report"

    @api.model
    def execute_followup(self, records):
        """
        Execute the actions to do with followups.
        """
        if not self.env.user.has_group(
                'markant_account_access.group_markant_account_access'):
            raise UserError(_('Sorry, You do not have access rights to '
                              'perform this action.'))
        return super(AccountFollowupReport, self).execute_followup(records)
