from odoo import api, fields, models


class BaseSyncLog(models.Model):
    _name = "base.sync.log"
    _order = "create_date desc"

    name = fields.Char(string="ID in Base")
    fields_updated = fields.Text()
    log_type = fields.Selection([('lead', 'Lead'), ('note', 'Note'), ('task', 'Task')])
    status = fields.Selection([('success', 'Success'), ('duplicate', 'Duplicate'), ('failed', 'Failed')])
    description = fields.Text()
    base_sync_id = fields.Many2one('base.synchronization', string="Base Sync")
    odoo_contact_id = fields.Many2one('res.partner')
    odoo_call_visit_id = fields.Many2one('voip.phonecall')


class BaseSyncTodo(models.Model):
    _name = "base.sync.todo"
    _order = "create_date desc"

    name = fields.Char(string="Todo")
    state = fields.Selection([('todo', 'Todo'), ('done', 'Done')], index=True)
    todo_type = fields.Selection([('lead', 'Lead'), ('note', 'Note'), ('task', 'Task'), ('other', 'Other')])
    description = fields.Text()
