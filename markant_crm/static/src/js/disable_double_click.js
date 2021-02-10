odoo.define('markant_crm.FormRenderer', function (require) {
    "use strict";

    var FormRenderer = require('web.FormRenderer');

    // check button have class 'dis_double_click' will disable so that they can't be clicked anymore
    FormRenderer.include({
        disableButtons: function () {
            this.$('.o_statusbar_buttons button, .oe_button_box button, .dis_double_click')
                .attr('disabled', true);
            },
    });
});
