# -*- coding: utf-8 -*-
import logging
from odoo import api, models, fields


class PostObjectData(models.TransientModel):
    _name = "post.object.data"

    @api.model
    def deactive_ir_rule(self):
        logging.info('==== START: Deactive ir rule account_analytic_line_rule_billing_user====')
        try:
            rule_acc_line = self.env.ref('sale_timesheet.account_analytic_line_rule_billing_user')
            if rule_acc_line:
                rule_acc_line.active = False
                logging.info('==== END: Deactive ir rule account_analytic_line_rule_billing_user====')
        except:
            pass
