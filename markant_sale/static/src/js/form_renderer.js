odoo.define('markant_sale.FormRenderer', function (require) {
    "use strict";

    var FormRenderer = require('web.FormRenderer');
    var core = require('web.core');
    var session = require('web.session');
    var _t = core._t;

    FormRenderer.include({
        updateState: function (state, params) {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                if (self.state.model === 'sale.order') {
                    if (self.mode === 'readonly') {
                        return self._rpc({
                            model: 'sale.order',
                            method: 'check_so_obsolete_product',
                            args: [self.state.res_id]
                        }).then(function (result) {
                            var data = result;
                            if (data[0]) {
                                var msg = data[1];
                                alert(msg);
                            }
                        });
                    }
                }
            });
        },
    });
});