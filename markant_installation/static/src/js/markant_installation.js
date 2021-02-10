odoo.define('markant_installation.markant_installation', function (require) {
    "use strict";

    var FormRenderer = require('web.FormRenderer');

    FormRenderer.include({
        _updateView: function ($newContent) {
            if(this.mode === 'edit') {
                $($newContent[1]).find('.as400-tokenizer').select2({
                    tags: true,
                    multiple: true,
                    tokenSeparators: [' ', '/', '-'],
                    separator: ", ",
                    dropdownCssClass: 'as400-hide-search',
                });
                if ($($newContent[1]).find('.mi_top_lock')){
                    if ($($newContent[1]).find('.mi_top_lock').find('input').is(':checked')){
                        $($newContent[1]).find('.as400-tokenizer').attr('readonly', true);
                    }
                }
            }
            return this._super.apply(this, arguments);
        },
    });

});
