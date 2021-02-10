# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
from decimal import Decimal
import math
from pytz import timezone, UTC
from six import string_types

from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo.addons.resource.models.resource import float_to_time
from odoo.tools.float_utils import float_round


class WeeklyHoursBasis(models.Model):
    _name = 'weekly.hours.basis'
    _description = 'Weekly Hours Basis'

    name = fields.Char('Name')
    hrs_basis_per_week = fields.Float('Total Hours Basis Per Week')


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    contract_calc = fields.Boolean(string="Contract Calculation")
    display_in_employee = fields.Boolean(string='Display in Employee form',
                                         default=True)

    @api.constrains('contract_calc')
    def _check_contract_calc(self):
        if self.contract_calc and self.search([
                ('contract_calc', '=', True),
                ('id', '!=', self.id)]):
            leave_type_id = self.search([('contract_calc', '=', True), ('id', '!=', self.id)])
            raise Warning(_('"%s" already has "Contract Calcuation" is ticked. \nOnly "ONE" leave type allow to have "Contract Calculation" \
                            ticked.') % leave_type_id.name)
        # if self.contract_calc:
        #     raise Warning(_('The leave type that is ticked as "Contract Calculation" must be "Allow to overwrite Limit" is "NOT" ticked'))
        return True


class hr_contract(models.Model):
    _inherit = 'hr.contract'

    weekly_hours_basis_id = fields.Many2one('weekly.hours.basis', string='Weekly Hours Basis')


class hr_holidays_public(models.Model):
    _name = 'hr.holidays.public'
    _description = 'Public Holidays'
    _rec_name = 'year'
    _order = 'year'

    name = fields.Char('Name')
    year = fields.Char(string="Calendar Year", required=True, default=date.today().year)
    line_ids = fields.One2many('hr.holidays.public.line', 'year_id', string='Holiday Dates')

    @api.model
    def get_holiday_dates(self):
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
        return employee.contract_id.resource_calendar_id.public_holiday_id.line_ids.read(['name', 'date'])

    @api.model
    def get_holidays_list(self, public_holiday):
        holidays_filter = [('name', '=', public_holiday.name)]
        public_holidays = self.search(holidays_filter)
        if not public_holidays:
            return []
        line_filter = [('year_id', 'in', public_holidays.ids)]
        hhplo = self.env['hr.holidays.public.line']
        holidays_lines = hhplo.search(line_filter)
        return holidays_lines

    @api.model
    def is_public_holiday(self, holiday_date, employee):
        if isinstance(holiday_date, string_types):
            holiday_date = fields.Date.from_string(holiday_date)
        contract = employee.contract_id
        public_holiday = False
        if contract:
            public_holiday = contract.resource_calendar_id.public_holiday_id or False
            if public_holiday:
                holidays_lines = self.get_holidays_list(public_holiday)
                hd_date = holiday_date.strftime('%Y-%m-%d')
                if holidays_lines and len(holidays_lines.filtered(
                        lambda x: x.date == fields.Date.from_string(hd_date))):
                    return True
        return False


class hr_holidays_public_line(models.Model):
    _name = 'hr.holidays.public.line'
    _description = 'Public Holidays Lines'
    _order = "date, name desc"

    name = fields.Char('Name', required=True)
    date = fields.Date('Date', required=True)
    year_id = fields.Many2one('hr.holidays.public', string='Calendar Year', required=True)

    # @api.constrains('date')
    # def _check_date_state(self):
    #     if int(fields.Date.from_string(self.date).year) != int(self.year_id.year):
    #         raise ValidationError(_('Dates of holidays should be the same year'))
    #     if self.search_count([('date', '=', self.date), ('year_id', '=', self.year_id.id)]) > 1:
    #         raise ValidationError(_('You can not create duplicate public holiday for date %s.')% self.date)
    #     return True


class resource_calendar(models.Model):
    _inherit = 'resource.calendar'

    @api.depends('attendance_ids')
    @api.one
    def _compute_working_hrs(self):
        for working_time in self:
            thours = 0.0
            # tdays = []
            for attendance in working_time.attendance_ids:
                thours += attendance.hour_to - attendance.hour_from
                # if attendance.dayofweek not in tdays:
                #     tdays.append(attendance.dayofweek)
            self.working_hrs_per_week = thours
            # if tdays:
            self.working_hrs_per_day = thours / 5
            self.working_hrs_per_day1 = thours / 5

    working_hrs_per_week = fields.Float(
                            compute='_compute_working_hrs',
                            string='Total Working Hours/week',
                            )
    working_hrs_per_day = fields.Float(
                            compute='_compute_working_hrs',
                            string='Total Working Hours/day',
                            )
    working_hrs_per_day1 = fields.Float(
                            compute='_compute_working_hrs',
                            string='Total Working Hours/day',
                            )
    public_holiday_id = fields.Many2one('hr.holidays.public', string='Public Holiday Calendar')


class resource_calendar_attendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    working_session_id = fields.Many2one('hr.holidays.shift', string='Working Session')

    @api.onchange('dayofweek')
    def onchange_dayofweek(self):
        days = {
            '0': 'Monday',
            '1': 'Tuesday',
            '2': 'Wednesday',
            '3': 'Thursday',
            '4': 'Friday',
            '5': 'Saturday',
            '6': 'Sunday'
        }
        self.name = days[self.dayofweek]

    @api.onchange('working_session_id')
    def on_change_working_session(self):
        self.hour_from = self.working_session_id.tfrom
        self.hour_to = self.working_session_id.tto


class hr_employee(models.Model):
    _inherit = 'hr.employee'

    resource_calendar_id = fields.Many2one(related="contract_id.resource_calendar_id")
    marital = fields.Selection([
                    ('single', 'Single'),
                    ('married', 'Married'),
                    ('widower', 'Widower'),
                    ('divorced', 'Divorced'),
                    ('livingtogether', 'Living Together')],
                    string='Marital Status')
    emergency_contact = fields.Selection([
                    ('father', 'Father'),
                    ('mother', 'Mother'),
                    ('spouse', 'Spouse'),
                    ('guardian', 'Guardian')],
                    string='Emergency contact')
    spouse_name = fields.Char('Spouse Name')
    spouse_working_status = fields.Char('Spouse Working Status')
    epf_number = fields.Char('EPF Number')
    date_joined = fields.Date(string="Date Joined")
    leave_brought_forward = fields.Float(string='Leaves brought forward',)
    allocation_leave = fields.Float('Allocation leave')
    emergency_contact_name = fields.Char('Emergency Contact Name')
    emergency_contact_number = fields.Char('Emergency Contact Number')
    leaves_count = fields.Float('Number of Leaves',
                                compute='_compute_leaves_count')
    remaining_leaves = fields.Float(
        compute='_compute_leaves_count', string='Remaining Legal Leaves',
        help='Total number of legal leaves allocated to this employee, change this value to create allocation/leave request. '
             'Total based on all the leave types without overriding limit.')

    @api.model
    def leaves_brought_forward(self):
        for employee in self.search([]):
            employee.write({'leave_brought_forward': employee.remaining_leaves})
        return True

    @api.multi
    def is_weekend_day(self, date_dt):
        if self.contract_id and self.contract_id.resource_calendar_id:
            domain = [('calendar_id', '=', self.resource_calendar_id.id)]
            attendances = self.env['resource.calendar.attendance'].search(domain, order='dayofweek, day_period DESC')

            # find first attendance coming after first_day
            attendance_from = next((att for att in attendances if int(att.dayofweek) >= date_dt.weekday()), attendances[0])
            # find last attendance coming before last_day
            attendance_to = next((att for att in reversed(attendances) if int(att.dayofweek) <= date_dt.weekday()), attendances[-1])

            hour_from = float_to_time(attendance_from.hour_from)
            hour_to = float_to_time(attendance_to.hour_to)

            user_tz = self.env.user.tz or 'UTC'

            date_from = timezone(user_tz).localize(datetime.combine(fields.Date.from_string(date_dt.strftime('%Y-%m-%d')), hour_from)).astimezone(UTC).replace(tzinfo=None)
            date_to = timezone(user_tz).localize(datetime.combine(fields.Date.from_string(date_dt.strftime('%Y-%m-%d')), hour_to)).astimezone(UTC).replace(tzinfo=None)

            hours = self.contract_id.resource_calendar_id.get_work_hours_count(
                date_from, date_to)
            if not hours:
                return False
        elif not self.contract_id or (
                self.contract_id and not self.contract_id.resource_calendar_id):
            if date_dt.weekday() in (5, 6):
                return False
        return True

    @api.model
    def work_scheduled_on_day(self, date_dt):
        self.ensure_one()
        self.is_weekend_day(date_dt)
        if self.env['hr.holidays.public'].is_public_holiday(date_dt, self) \
                or not self.is_weekend_day(date_dt):
            return False
        return True

    @api.multi
    def _compute_leaves_count(self):
        all_leaves = self.env['hr.leave.report'].read_group([
            ('employee_id', 'in', self.ids),
            ('holiday_status_id.allocation_type', '!=', 'no'),
            ('state', '=', 'validate'),
            ('holiday_status_id.display_in_employee', '=', True)
        ], fields=['number_of_days', 'employee_id'], groupby=['employee_id'])
        mapping = dict(
            [(leave['employee_id'][0], leave['number_of_days']) for leave in
             all_leaves])
        for employee in self:
            employee.leaves_count = float_round(mapping.get(employee.id, 0),
                                                precision_digits=2)
            employee.remaining_leaves = float_round(
                mapping.get(employee.id, 0), precision_digits=2)


class HrLeaveTodoTask(models.Model):
    _name = 'hr.leave.todo.task'

    name = fields.Char('Description')
    state = fields.Selection([
                    ('done', 'Done'),
                    ('not_done', 'Not Done')], string="Status",
                    default='not_done')
    date_done = fields.Date('Date Done')
    hr_holiday_id = fields.Many2one('hr.leave', string='Holidays')


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def check_manager(self):
        if self.env.user.has_group('base.group_hr_manager'):
            return True
        return False

    # date_from = fields.Date(default=lambda self: self._context.get('date', fields.Date.context_today(self)))
    # date_to = fields.Date(default=lambda self: self._context.get('date', fields.Date.context_today(self)))
    select_all_fullday = fields.Boolean('Select All Fullday', default=True)
    auto_allocate_days = fields.Boolean('Auto Allocate Days ?')
    number_of_days_temp1 = fields.Float(
                            compute='_compute_number_of_holiday_days',
                            string='None',  # name of these field same as number of days due to change name
                            store=True)
    hr_leave_todo_task_ids = fields.One2many(
                            'hr.leave.todo.task',
                            'hr_holiday_id',
                            string='Todo Tasks')
    c_manager = fields.Boolean(string='Manager?', default=check_manager)
    holiday_hours_ids = fields.One2many(
                        'hr.holidays.hours',
                        'holiday_id',
                        string='Holiday Schedule',
                        readonly=True,
                        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    # employee_manager_id=fields.Many2one('hr.employee','Manager',readonly=True)
    contract_calc = fields.Boolean('Contract Calcaulation')

    @api.multi
    def _check_date(self):
        return True

    @api.constrains('employee_id')
    def check_employee_calendar(self):
        if not self.employee_id.resource_calendar_id:
            raise Warning(_('Please set resource calendar (Working Schedule) in employee contract.'))

    @api.onchange('select_all_fullday')
    def onchange_select_all_fullday(self):
        select = False
        if self.select_all_fullday:
            select = True
        for line in self.holiday_hours_ids:
            line.is_fullday = select
            line.on_change_shift()

    _constraints = [
        (_check_date, 'You can not have 2 leaves that overlaps on same day!', ['date_from', 'date_to']),
    ]

    @api.depends('holiday_hours_ids')
    def _compute_number_of_holiday_days(self):
        for hol in self:
            days = 0.0
            for line in hol.holiday_hours_ids:
                days += line.nod
            hol.number_of_days_temp1 = days
            hol.number_of_days = days

    @api.multi
    @api.depends('holiday_hours_ids', 'select_all_fullday')
    def _compute_number_of_days_display(self):
        for hol in self:
            days = 0.0
            for line in hol.holiday_hours_ids:
                days += line.nod
            hol.number_of_days_temp1 = days
            hol.number_of_days = days
            hol.number_of_days_display = days

    @api.model
    def _auto_init(self):
        res = super(HrLeave, self)._auto_init()
        for i, (fun, msg, names) in enumerate(self._constraints):
            if fun.__name__ == '_check_date':
                del self._constraints[i]
        return res

    @api.model
    def _check_date_helper(self, employee_id, date):
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            if (not employee.work_scheduled_on_day(fields.Date.from_string(date))):
                return False
        return True

    def _get_number_of_days(self, date_from, date_to, employee_id):
        """ Returns a float equals to the timedelta between two dates given as string."""
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            if not employee.resource_calendar_id:
                raise Warning(_('Please set resource calendar in employee `%s`.') % (employee.name))
            return employee.get_work_days_data(date_from, date_to, calendar=employee.resource_calendar_id)['days']

        time_delta = date_to - date_from
        return math.ceil(time_delta.days + float(time_delta.seconds) / 86400)

    @api.onchange('employee_id')
    def _onchange_employee(self):
        self.department_id = False
        self.holiday_status_id = False
        # self.number_of_days_temp = 0.0
        self.holiday_hours_ids = False
        if self.employee_id:
            # self.department_id = self.employee_id.department_id
            res = self._onchange_date_to()
            if self.env.context.get('v_show_warning'):
                return res

    @api.onchange('date_from')
    def _onchange_date_from(self):
        """ If there are no date set for date_to, automatically set one 8 hours later than
            the date_from. Also update the number_of_days.
        """
        if not self.date_to:
            return

        # Compute and update the number of days
        if (self.date_to and self.date_from) and (self.date_from <= self.date_to):
            self.number_of_days = self._get_number_of_days(self.date_from, self.date_to, self.employee_id.id)
        else:
            self.number_of_days = 0

        if (self.date_from and self.date_to) and (self.date_from > self.date_to):
            return {'warning': {
                'title': _('Validation Warning!'),
                'message': _('The start date must be anterior to the end date.'),
            }}
        res = self._onchange_date_to()
        if self.env.context.get('v_show_warning'):
            return res

    @api.onchange('date_to')
    def _onchange_date_to(self):
        """ Update the number_of_days. """
        if not self.employee_id:
            # not leave request then return
            return
        dt_from = self.date_from  # fields.Date.from_string(self.date_from)
        dt_to = self.date_to  # fields.Date.from_string(self.date_to)
        # h_hours = HolidayHours = self.env['hr.holidays.hours']
        holidays_hours = []

        ResourceCalendar = self.env['resource.calendar.attendance']

        if not self.employee_id.contract_id:
            raise Warning(_('Sorry, There is not active contract '
                            'for current Employee.'))
        if not self.employee_id.contract_id.resource_calendar_id:
            raise Warning(_('Sorry There is no working schedule '
                            'for active contract.'))
        calendar_id = self.employee_id.contract_id.resource_calendar_id
        user_tz = self.env.user.tz or 'UTC'
        res = {}
        if (dt_to and dt_from) and (dt_from <= dt_to):
            diff_day = self._get_number_of_days(self.date_from,
                                                self.date_to, False)
            _warning_dates = []
            for d in range(int(diff_day)):
                dfrom = dt_from + timedelta(days=d)

                dfrom = timezone('UTC').localize(
                    dfrom).astimezone(timezone(user_tz)).replace(tzinfo=None)

                if self.employee_id.work_scheduled_on_day(dfrom):
                    vals = {
                        'date_from': dfrom.strftime('%Y-%m-%d'),
                        'dayofweek': str(dfrom.weekday()),
                        'is_fullday': self.select_all_fullday,
                    }
                    hour_from = []
                    hour_to = []
                    for line in ResourceCalendar.search(
                            [('calendar_id', '=', calendar_id.id),
                             ('dayofweek', '=', dfrom.weekday())]):
                        hour_from.append(line.hour_from)
                        hour_to.append(line.hour_to)
                    vals['hour_from'] = min(hour_from)
                    vals['hour_to'] = max(hour_to)
                    vals['noh'] = max(hour_to) - min(hour_from)
                    if self.select_all_fullday:
                        vals['nod'] = 1
                    holidays_hours.append(vals)
                else:
                    _warning_dates.append(dfrom.strftime('%d-%m-%Y'))

            if _warning_dates:
                _is = len(_warning_dates) > 1 and 'are' or 'is'
                res['warning'] = {
                    'title': _('Warning!'),
                    'message': _('You are not allowed to proceed '
                                 'as by default %s %s holiday.' %
                                 (', '.join(_warning_dates), _is)),
                }
            self.holiday_hours_ids = False
            self.holiday_hours_ids = holidays_hours  # [(6, 0, h_hours.ids)]
        else:
            self.number_of_days = 0
        return res

    @api.multi
    def holidays_confirm(self):
        for record in self.sudo():
            if record.employee_id and record.employee_id.parent_id \
                    and record.employee_id.parent_id.user_id:
                record.message_subscribe(
                    user_ids=record.employee_id.parent_id.user_id.partner_id.ids
                )
        return self.write({'state': 'confirm'})

    @api.multi
    def write(self, vals):
        if vals.get('number_of_days_temp1'):
            vals['number_of_days'] = vals['number_of_days_temp1']
        res = super(HrLeave, self).write(vals)
        # Check leaves are perfect or not.
        if vals.get('holiday_hours_ids') is None:
            for record in self:
                holiday_hours = record.holiday_hours_ids
                if holiday_hours:
                    holiday_hours._check_date()
        return res


class hr_holidays_shif(models.Model):
    _name = 'hr.holidays.shift'

    name = fields.Char('Shift')
    dtype = fields.Selection([
                ('fullday', 'Fullday'),
                ('halfday', 'Halfday')
            ],
           string="DType",
           required=True,
           default='fullday')
    stype = fields.Selection([('morning', 'Morning'),
                              ('evening', 'Evening')], string="Shift")
    tfrom = fields.Float("From", required=True, default=10.00)
    tto = fields.Float("To", required=True, default=19.00)
    nod = fields.Float("No of days", required=True)
    leave_day_calc = fields.Float("Leave Day For Calculation", required=True)

    @api.multi
    def write(self, vals):
        hhh = self.env['hr.holidays.hours'].search([('holidays_shift_id', 'in', self.ids)], limit=1)
        if not hhh.holiday_id:
            attendances = self.env['resource.calendar.attendance'].search([('working_session_id', 'in', self.ids)])
            for attendance in attendances:
                if vals.get('tfrom'):
                    attendances.write({'hour_from': vals.get('tfrom')})
                if vals.get('tto'):
                    attendances.write({'hour_to': vals.get('tto')})
        else:
            raise Warning(_('You can not change wroking session hours which is linked with any leave request.'))
        return super(hr_holidays_shif, self).write(vals)

    @api.onchange('dtype')
    def _onchange_dtype(self):
        if self.dtype == 'fullday':
            self.nod = 1.0
        elif self.dtype == 'halfday':
            self.nod = 0.5

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        HrEmployee = self.env['hr.employee']
        recs = self.browse()
        if self._context.get('employee_id') and self._context.get('dayofweek'):
            # domain = []
            employee = HrEmployee.browse(self._context['employee_id'])
            if employee.contract_id and employee.contract_id.resource_calendar_id:
                attendances = employee.contract_id.resource_calendar_id.attendance_ids
                sessions = attendances.filtered(lambda r: r.dayofweek == self._context['dayofweek']).mapped('working_session_id')
                recs |= sessions
        else:
            recs = self.search(args, limit=limit)
        return recs.name_get()


class hr_holidays_hours(models.Model):
    _name = 'hr.holidays.hours'

    dayofweek = fields.Selection([
                        ('0', 'Monday'),
                        ('1', 'Tuesday'),
                        ('2', 'Wednesday'),
                        ('3', 'Thursday'),
                        ('4', 'Friday'),
                        ('5', 'Saturday'),
                        ('6', 'Sunday')], string='Day of Week', required=True)
    date_from = fields.Date('Starting Date')
    hour_from = fields.Float('Work from', required=True)
    hour_to = fields.Float("Work to", required=True)
    holiday_id = fields.Many2one('hr.leave', string='Holiday')
    holidays_shift_id = fields.Many2one('hr.holidays.shift', string='Session')
    nod = fields.Float('Leave Days', required=True)
    noh = fields.Float('Leave Hours', required=True)
    is_fullday = fields.Boolean(string='Fullday?')

    @api.multi
    @api.constrains('is_fullday', 'holidays_shift_id')
    def _check_reconcile(self):
        for rec in self:
            if not rec.is_fullday and not rec.holidays_shift_id:
                raise Warning(_('You have to select either Full day or Session.'))

    @api.constrains('date_from', 'holidays_shift_id', 'is_fullday')
    def _check_date(self):
        for hour in self:
            # message = ''
            domain = [
                ('date_from', '=', hour.date_from),
                ('id', '!=', hour.id),
                ('holiday_id', '!=', hour.holiday_id.id),
                ('holiday_id.employee_id', '=', hour.holiday_id.employee_id.id),
                ('holiday_id.state', 'not in', ['cancel', 'refuse'])
            ]
            if hour.is_fullday:
                domain.append('|')
                domain.append(('holidays_shift_id', '!=', False))
                domain.append(('is_fullday', '=', True))
            elif hour.holidays_shift_id:
                domain.append('|')
                domain.append(('holidays_shift_id', '=', hour.holidays_shift_id.id))
                domain.append(('is_fullday', '=', True))
            else:
                continue
            nhours = self.search(domain)
            if nhours:
                raise Warning(_('You can not have 2 leaves that overlaps on same day!'))

    @api.onchange('holidays_shift_id', 'is_fullday')
    def on_change_shift(self):
        contract = self.holiday_id.employee_id.contract_id
        hour_from, hour_to, noh, nod = 0.0, 0.0, 0.0, 0.0
        hrs_frm, hrs_to = [], []
        if contract:
            if self.is_fullday:
                for working_time in contract.resource_calendar_id.attendance_ids:
                    if working_time.dayofweek == self.dayofweek:
                        hrs_frm.append(working_time.hour_from)
                        hrs_to.append(working_time.hour_to)
                        # hour_from += working_time.hour_from
                        # hour_to += working_time.hour_to
                        noh += working_time.hour_to - working_time.hour_from
                        nod += working_time.working_session_id.leave_day_calc
                hour_from = min(hrs_frm)
                hour_to = max(hrs_to)
                self.holidays_shift_id = False
            else:
                hour_from = self.holidays_shift_id.tfrom
                hour_to = self.holidays_shift_id.tto
                noh = self.holidays_shift_id.tto - self.holidays_shift_id.tfrom
                nod = self.holidays_shift_id.leave_day_calc

            self.hour_from = hour_from
            self.hour_to = hour_to
            self.name = self.holidays_shift_id.name
            self.noh = noh
            self.nod = nod

    @api.multi
    def write(self, vals):
        res = super(hr_holidays_hours, self).write(vals)
        for line in self:
            if not line.is_fullday:
                self.holiday_id.select_all_fullday = False
        return res


class LeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    def check_manager(self):
        if self.env.user.has_group('base.group_hr_manager'):
            return True
        return False

    auto_allocate_days = fields.Boolean('Auto Allocate Days ?')
    contract_calc = fields.Boolean(string="Contract Calcaulation")

    @api.onchange('holiday_status_id')
    def on_change_holiday_status_id(self):
        self.contract_calc = self.holiday_status_id.contract_calc
        self.auto_allocate_days = False

    @api.onchange('auto_allocate_days')
    def onchange_auto_allocate_days(self):
        if self.auto_allocate_days:
            contract = self.employee_id.contract_id
            working_hrs_per_week = contract.resource_calendar_id.working_hrs_per_week
            hrs_basis_per_week = contract.weekly_hours_basis_id.hrs_basis_per_week
            allocation_leave = self.employee_id.allocation_leave or False
            msg = False
            if not working_hrs_per_week and working_hrs_per_week <= 0.0:
                self.auto_allocate_days = False
                msg = _("The value of 'Total Working Hours/week' NOT VALID in\
                    the Working Time configured in Employee Form of %s." % (self.employee_id.name))
            elif not hrs_basis_per_week and hrs_basis_per_week <= 0.0:
                self.auto_allocate_days = False
                msg = _('You have to configure "Weekly Hours Basis of %s in the Contract Form' % (self.employee_id.name))
            elif not allocation_leave and allocation_leave <= 0.0:
                self.auto_allocate_days = False
                msg = _('You have to configure Allocation Leave in Employee.')

            if msg:
                return {'warning': {'title': 'Validation Error', 'message': msg}}

            if working_hrs_per_week and hrs_basis_per_week and allocation_leave:
                number_of_days = (working_hrs_per_week / hrs_basis_per_week) * allocation_leave
                digit = int(number_of_days)
                precision = Decimal(str(number_of_days - digit).split('.')[1][0]) / Decimal(10)

                final_precision = 0.0
                precision = float(precision)
                if precision > 0.0 and precision < 0.3:
                    final_precision = 0.0
                if precision >= 0.3 and precision < 0.8:
                    final_precision = 0.5
                if precision >= 0.8 and precision < 1.0:
                    final_precision = 1.0

                self.number_of_days = digit + final_precision
