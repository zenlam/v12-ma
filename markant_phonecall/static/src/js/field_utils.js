odoo.define('markant_phonecall.field_utils', function (require) {
"use strict";

var ultils = require('web.field_utils');

function formatFloatTimeInherit(value, field, options) {
    /* if widget float_time have options ignore_default, don't display 00:00, return '' */
    if (options['ignore_default'] == true && value === 0) {
        return '';
    }
    var pattern = '%02d:%02d';
    if (value < 0) {
        value = Math.abs(value);
        pattern = '-' + pattern;
    }
    var hour = Math.floor(value);
    var min = Math.round((value % 1) * 60);
    if (min === 60){
        min = 0;
        hour = hour + 1;
    }
    return _.str.sprintf(pattern, hour, min);
}

ultils.format['float_time'] = formatFloatTimeInherit;

});
