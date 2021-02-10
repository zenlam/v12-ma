odoo.define('markant_hr.holiday_calendar', function (require) {
    "use strict";

    var CalendarModel = require('web.CalendarModel');
    var CalendarRenderer = require('web.CalendarRenderer');
//    var CalendarController = require('web.CalendarController');
//    var AbstractModel = require('web.AbstractModel');

    CalendarModel.include({
        /**
         * Transform fullcalendar event object to OpenERP Data object
         */
        calendarEventToRecord: function (event) {
            // Normalize event_end without changing fullcalendars event.
            var data = {'name': event.title};
            var start = event.start.clone();
            var end = event.end && event.end.clone();

            // Detects allDay events (86400000 = 1 day in ms)
            if (event.allDay || (end && end.diff(start) % 86400000 === 0)) {
                event.allDay = true;
            }

            if (this.modelName === 'hr.leave' && this.mode === 'month') {
                this.mapping.all_day = 'allday';
            }

            // Set end date if not existing
            if (!end || end.diff(start) < 0) { // undefined or invalid end date
                if (event.allDay) {
                    end = start.clone();
                } else {
                    // in week mode or day mode, convert allday event to event
                    end = start.clone().add(2, 'h');
                }
            } else if (event.allDay) {
                // For an "allDay", FullCalendar gives the end day as the
                // next day at midnight (instead of 23h59).
                end.add(-1, 'days');
            }

            // An "allDay" event without the "all_day" option is not considered
            // as a 24h day. It's just a part of the day (by default: 7h-19h).
            if (event.allDay) {
                if (!this.mapping.all_day) {
                    if (event.r_start) {
                        start.hours(event.r_start.hours())
                             .minutes(event.r_start.minutes())
                             .seconds(event.r_start.seconds())
                             .utc();
                        end.hours(event.r_end.hours())
                           .minutes(event.r_end.minutes())
                           .seconds(event.r_end.seconds())
                           .utc();
                    } else {
                        // default hours in the user's timezone
                        start.hours(7).add(-this.getSession().getTZOffset(start), 'minutes');
                        end.hours(19).add(-this.getSession().getTZOffset(end), 'minutes');
                    }
                }
            } else {
                start.add(-this.getSession().getTZOffset(start), 'minutes');
                end.add(-this.getSession().getTZOffset(end), 'minutes');
            }

            if (this.mapping.all_day) {
                if (event.record) {
                    data[this.mapping.all_day] =
                        (this.scale !== 'month' && event.allDay) ||
                        event.record[this.mapping.all_day] &&
                        end.diff(start) < 10 ||
                        false;
                } else {
                    data[this.mapping.all_day] = event.allDay;
                }
            }

            data[this.mapping.date_start] = start;
            if (this.mapping.date_stop) {
                data[this.mapping.date_stop] = end;
            }

            if (this.mapping.date_delay) {
                data[this.mapping.date_delay] = (end.diff(start) <= 0 ? end.endOf('day').diff(start) : end.diff(start)) / 1000 / 3600;
            }
            return data;
        },
    });

});
