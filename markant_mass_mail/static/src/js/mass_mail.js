odoo.define('markant_mass_mail.snippets.options', function (require) {
'use strict';


var options = require('web_editor.snippets.options');
console.log('___ options : ', options);

var core = require('web.core');
var Dialog = require('web.Dialog');
var Widget = require('web.Widget');
var weContext = require('web_editor.context');
var widget = require('web_editor.widget');

var qweb = core.qweb;
var _t = core._t;

options.registry.field_selection = options.Class.extend({
    events: _.extend({}, options.Class.events || {}, {
        'click .v_paste_value': '_onPasteButtonClick',
    }),

    _onPasteButtonClick: function(event) {
        event.preventDefault();
        var v_copy_value = parent.document.getElementsByClassName('v_copy_value');
        if (!v_copy_value) {
            return;
        }
        var selection = document.getSelection();
        var cursorPos = selection.anchorOffset;
        var oldContent = selection.anchorNode.nodeValue;
        var toInsert = v_copy_value.copyvalue.value;
        var newContent = oldContent.substring(0, cursorPos) + toInsert + oldContent.substring(cursorPos);
        selection.anchorNode.nodeValue = newContent;
    },
});

});
