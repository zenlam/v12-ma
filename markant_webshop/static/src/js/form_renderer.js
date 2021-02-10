odoo.define('markant_webshop.FormRenderer', function (require) {
    "use strict";

    var FormRenderer = require('web.FormRenderer')

    FormRenderer.include({
        /**
         * returns the active tab pages for each notebook
         *
         * @todo currently, this method is unused...
         *
         * @see setLocalState
         * @returns {Object} a map from notebook name to the active tab index
         */
        getLocalState: function () {
            var state = {};
            var new_index = [];
            this.$('div.o_notebook').each(function () {
                var $notebook = $(this);
                var name = $notebook.data('name');
                var index = -1;
                $notebook.find('.nav-link').each(function (i) {
                    if ($(this).hasClass('active')) {
                        index = i;
                        new_index.push(i);
                        return false;
                    }
                });
                state[name] = index;
            });
            state['new'] = new_index;
            console.log('new state ---------->', state['new']);
            return state;
        },

        /**
         * restore active tab pages for each notebook
         *
         * @todo make sure this method is called
         *
         * @param {Object} state the result from a getLocalState call
         */
        setLocalState: function (state) {
            this.$('div.o_notebook').each(function () {
                var $notebook = $(this);
                var name = $notebook.data('name');
                if (name in state) {
                    for (var i=0; i<state['new'].length; i++){
                        if (i === 0){
                            var $page = $notebook.find('> ul > li').eq(state['new'][i]);
                            if (!$page.hasClass('o_invisible_modifier')) {
                                $page.find('a[data-toggle="tab"]').click();
                            }
                        } else {
                            var $element = $notebook.find('.o_notebook > ul > li').eq(state['new'][i]);
                            if (!$element.hasClass('o_invisible_modifier')) {
                                $element.find('a[data-toggle="tab"]').click();
                            }
                        }
                    }
                    // var $page = $notebook.find('> ul > li').eq(state[name]);
                    // console.log('page ================>>', $page);
                    // if (!$page.hasClass('o_invisible_modifier')) {
                    //     $page.find('a[data-toggle="tab"]').click();
                    // }
                }
                return false;
            });
        },
    });
});
