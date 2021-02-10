odoo.define('markant_product.ProductConfiguratorFormController', function (require) {
    "use strict";

    var core = require('web.core');
    var _t = core._t;
    var FormController = require('web.FormController');
    var ProductConfiguratorFormController = require('sale.ProductConfiguratorFormController');
    var FieldManagerMixin = require('web.FieldManagerMixin');

    ProductConfiguratorFormController.include({
        /**
         * @override
         */
        _onFieldChanged: function (event) {
            this._super.apply(this, arguments);
            $('.o_control_panel').find('.o_cp_left').removeClass('d-none');
            if (this.$el.find('footer').attr('invisible') &&
                this.$el.find('footer').attr('invisible') ===
                "context.get('pcf_lookup', False)") {
                $('.o_control_panel').find('.o_cp_left').addClass('d-none');
            }
        },
    });
});
