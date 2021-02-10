from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MarkantSpecialStage(models.Model):
    _name = 'markant.special.stage'
    _description = 'Stages for Special Form'
    _rec_name = 'name'
    _order = 'sequence'

    name = fields.Char(string='Stage Name', required=True)
    sequence = fields.Integer(string='Sequence', default=1)
    assign_mail = fields.Boolean(string="Send Assignment Mail", default=False)
    approve_mail = fields.Boolean(string="Send Approval Mail", default=False)
    reject_mail = fields.Boolean(string="Send Reject Mail", default=False)

    @api.onchange('assign_mail', 'approve_mail', 'reject_mail')
    def check_valid_mail_action(self):
        mail_actions = [self.assign_mail, self.approve_mail, self.reject_mail]
        action_true_count = sum([1 for action in mail_actions if action])
        if action_true_count > 1:
            raise ValidationError("Only one mail action can be "
                                  "applied on one stage.")
