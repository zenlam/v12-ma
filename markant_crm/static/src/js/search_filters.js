odoo.define('markant_crm.search_filters', function (require) {
    "use strict";

    var core = require('web.core');
    var datepicker = require('web.datepicker');
    var field_utils = require('web.field_utils');
    var Widget = require('web.Widget');

    var _t = core._t;
    var _lt = core._lt;

    var Field = Widget.extend({
        init: function (parent, field) {
            this._super(parent);
            this.field = field;
        },

        get_label: function (field, operator) {
            var format;
            switch (operator.value) {
            case '∃': case '∄': format = _t('%(field)s %(operator)s'); break;
            default: format = _t('%(field)s %(operator)s "%(value)s"'); break;
            }
            return this.format_label(format, field, operator);
        },

        format_label: function (format, field, operator) {
            return _.str.sprintf(format, {
                field: field.string,
                // According to spec, HTMLOptionElement#label should return
                // HTMLOptionElement#text when not defined/empty, but it does
                // not in older Webkit (between Safari 5.1.5 and Chrome 17) and
                // Gecko (pre Firefox 7) browsers, so we need a manual fallback
                // for those
                operator: operator.label || operator.text,
                value: this
            });
        },

        get_domain: function (field, operator) {
            switch (operator.value) {
            case '∃': return [[field.name, '!=', false]];
            case '∄': return [[field.name, '=', false]];
            default: return [[field.name, operator.value, this.get_value()]];
            }
        },

        show_inputs: function ($operator) {
            var $value = this.$el.parent();
            switch ($operator.val()) {
                case '∃':
                case '∄':
                    $value.hide();
                    break;
                default:
                    $value.show();
            }
        },
        /**
         * Returns a human-readable version of the value, in case the "logical"
         * and the "semantic" values of a field differ (as for selection fields,
         * for instance).
         *
         * The default implementation simply returns the value itself.
         *
         * @return {String} human-readable version of the value
         */
        toString: function () {
            return this.get_value();
        }
    });

    var DateTime = Field.extend({
        tagName: 'span',
        attributes: {
            type: 'datetime'
        },

        // add new option operator with date, datetime field (last, next 7 days ...)
        operators: [
            {value: "=", text: _lt("is equal to")},
            {value: "!=", text: _lt("is not equal to")},
            {value: ">=", text: _lt("is after")},
            {value: "<=", text: _lt("is before")},
            {value: "between", text: _lt("is between")},
            {value: "∃", text: _lt("is set")},
            {value: "∄", text: _lt("is not set")},
            {value: "last_7d", text: _lt("Last 7 Days")},
            {value: "next_7d", text: _lt("Next 7 Days")},
            {value: "last_14d", text: _lt("Last 14 Days")},
            {value: "next_14d", text: _lt("Next 14 Days")},
            {value: "last_1m", text: _lt("Last Month")},
            {value: "next_1m", text: _lt("Next Month")},
            {value: "last_3m", text: _lt("Last 1 Quarter")},
            {value: "next_3m", text: _lt("Next 1 Quarter")},
            {value: "last_6m", text: _lt("Last Half Year")},
            {value: "next_6m", text: _lt("Next Half Year")},
            {value: "last_12m", text: _lt("Last 1 Year")},
            {value: "next_12m", text: _lt("Next 1 Year")},
        ],

        get_value: function (index) {
            // retrieve the datepicker value
            var value = this["datewidget_" + (index || 0)].getValue();
            // convert to utc
            return value.add(-this.getSession().getTZOffset(value), 'minutes');
        },

        get_domain: function (field, operator) {
            // get domain for special search filter with date, datetime field (last 7 days, next 7 days ....)
            var now = moment();
            if (field.type == 'date') {
                now = now.format('YYYY/MM/DD');
            }
            switch (operator.value) {
            case '∃':
                return [[field.name, '!=', false]];
            case '∄':
                return [[field.name, '=', false]];
            case 'between':
                return [[field.name, '>=', this.get_value()], [field.name, '<=', this.get_value(1)]];
            case 'last_7d':
            case 'last_14d':
            case 'last_1m':
            case 'last_3m':
            case 'last_6m':
            case 'last_12m':
                if (field.type == 'datetime') {
                    now.set({hour:23,minute:59,second:59,milisecond:99});
                }
                return [[field.name, '>=', this.get_value()], [field.name, '<=', now]];
            case 'next_7d':
            case 'next_14d':
            case 'next_1m':
            case 'next_3m':
            case 'next_6m':
            case 'next_12m':
                if (field.type == 'datetime') {
                    now.set({hour:0,minute:0,second:0,milisecond:0});
                }
                return [[field.name, '>=', now], [field.name, '<=', this.get_value()]];
            default:
                return [[field.name, operator.value, this.get_value()]];
            }
        },

        show_inputs: function ($operator) {
            this._super.apply(this, arguments);

            // calculate value for special search filter (last 7 days, next 7 days....)
            let value_to_set = moment();
            if ($operator.val().includes('last') || $operator.val().includes('next')) {
                let res = $operator.val().split('_');
                if (res[1].includes('d')) {
                    let number_days = parseInt(res[1].replace('d', ''));
                    number_days = res[0] == 'last' ? -number_days : number_days;
                    value_to_set = value_to_set.add(number_days, "days");
                } else {
                    let number_months = parseInt(res[1].replace('m', ''));
                    number_months = res[0] == 'last' ? -number_months : number_months;
                    value_to_set = value_to_set.add(number_months, "months");
                }
            }
            if ($operator.val().includes('last')) {
                value_to_set = value_to_set.set({hour:0,minute:0,second:0})
            }
            if ($operator.val().includes('next')) {
                value_to_set = value_to_set.set({hour:23,minute:59,second:59})
            }

            // replace value of search text box
            this['datewidget_0'].setValue(value_to_set);

            if ($operator.val() === "between") {
                if (!this.datewidget_1) {
                    this._create_new_widget("datewidget_1");
                } else {
                    this.datewidget_1.do_show();
                }
            } else {
                if (this.datewidget_1) {
                    this.datewidget_1.do_hide();
                }
            }
        },

        toString: function () {
            var str = field_utils.format[this.attributes.type](this.get_value(), {type: this.attributes.type});
            var date_1_value = this.datewidget_1 && this.get_value(1);
            if (date_1_value) {
                str += _lt(" and ") + field_utils.format[this.attributes.type](date_1_value, {type: this.attributes.type});
            }
            return str;
        },

        start: function () {
            return $.when(
                this._super.apply(this, arguments),
                this._create_new_widget("datewidget_0")
            );
        },

        _create_new_widget: function (name) {
            this[name] = new (this._get_widget_class())(this);
            return this[name].appendTo(this.$el).then((function () {
                this[name].setValue(moment(new Date()));
            }).bind(this));
        },

        _get_widget_class: function () {
            return datepicker.DateTimeWidget;
        },
    });

    var Date = DateTime.extend({
        attributes: {
            type: 'date'
        },

        get_value: function (index) {
            // retrieve the datepicker value
            return this["datewidget_" + (index || 0)].getValue();
        },

        _get_widget_class: function () {
            return datepicker.DateWidget;
        },
    });

    core.search_filters_registry.map.datetime = DateTime;
    core.search_filters_registry.map.date = Date;

});
