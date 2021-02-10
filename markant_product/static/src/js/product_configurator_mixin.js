odoo.define('markant_product.ProductConfiguratorMixin', function (require) {
    'use strict';

    var core = require('web.core');
    var utils = require('web.utils');
    var ajax = require('web.ajax');
    var rpc = require('web.rpc');
    var framework = require('web.framework');
    var QWeb = core.qweb;
    var _t = core._t;
    var ProductConfiguratorMixin = require('sale.ProductConfiguratorMixin');
    var ProductConfiguratorFormRenderer = require('sale.ProductConfiguratorFormRenderer');

    ProductConfiguratorFormRenderer.include({
        events: {
            'click .css_attribute_color input': '_onChangeColorAttribute',
            'change .main_product:not(.in_cart) input.js_quantity': 'onChangeAddQuantity',
            'click button.js_add_cart_json': 'onClickAddCartJSON',
            'change [data-attribute_exclusions]': 'onChangeVariant',
            'click a.configuration_step': '_onChangeConfigureStep',
            'click button.open_pcf_lookup_report_button': '_openPCFLookup',
            'click .o_mrp_bom_unfoldable': '_onClickUnfold',
            'click .o_mrp_bom_foldable': '_onClickFold',
            'click button.compute_max_produce_qty': '_computeMaxProduceQty',
        },

        /**
         * When a variant is changed, this will check:
         * - If the selected combination is available or not
         * - The extra price if applicable
         * - The display name of the product ("Customizable desk (White, Steel)")
         * - The new total price
         * - The need of adding a "custom value" input
         *
         * @param {MouseEvent} ev
         */
        onChangeVariant: function (ev) {
            var self = this;

            var $component;
            if ($(ev.currentTarget).closest('form').length > 0){
                $component = $(ev.currentTarget).closest('form');
            } else if ($(ev.currentTarget).closest('.oe_optional_products_modal').length > 0){
                $component = $(ev.currentTarget).closest('.oe_optional_products_modal');
            } else if ($(ev.currentTarget).closest('.o_product_configurator').length > 0) {
                $component = $(ev.currentTarget).closest('.o_product_configurator');
            } else {
                $component = $(ev.currentTarget);
            }
            var qty = $component.find('input[name="add_qty"]').val();

            var $parent = $(ev.target).closest('.js_product');
            var combination = this.getSelectedVariantValues($parent);

            if ($parent.find('div.selected_values_on_each_steps').length > 0) {

                // Product list price display on start then switch back to odoo's logic
                $parent.find('h2.configurator_steps_price_dummy').remove();
                $parent.find('h2.configurator_steps_price').removeClass('d-none');

                var current_step_number = $parent.find('div.carousel-item.active').index();
                var current_step = 'values_from_step_id_' + current_step_number;

                // Remove div if there is any for active step
                $parent.find('div.selected_values_on_each_steps div.' + current_step).remove();

                // Remove all other div which is coming after the active step if any
                var all_processed_steps = $('div[class^="values_from_step_id_"]');
                _.each(all_processed_steps, function(processed_step) {
                    var step_count = $(processed_step).attr('class').split("values_from_step_id_").pop();
                    if (parseInt(step_count) > parseInt(current_step_number)) {
                        $(processed_step).remove();
                    }
                });

                var variantsValuesSelectors = [
                    'input.js_variant_change:checked',
                    'select.js_variant_change'
                ];

                _.each($parent.find(variantsValuesSelectors.join(', ')), function (el) {
                    var value, data_value_id, data_value_name,
                        data_attribute_name, data_is_custom,
                        data_display_currency_symbol, data_price_extra;
                    if ($(el).is('input')) {
                        value = $(el).attr('value'),
                        data_value_id = $(el).attr('data-value_id'),
                        data_value_name = $(el).attr('data-value_name'),
                        data_attribute_name = $(el).attr('data-attribute_name'),
                        data_is_custom = $(el).attr('data-is_custom'),
                        data_display_currency_symbol = $(el).attr('data-display_currency_symbol'),
                        data_price_extra = $(el).parent().find('span.variant_price_extra .oe_currency_value').html();
                    }
                    if ($(el).is('select')) {
                        value = $(el).val(),
                        data_value_id = $(el).find('option:selected').attr('data-value_id'),
                        data_value_name = $(el).find('option:selected').attr('data-value_name'),
                        data_attribute_name = $(el).find('option:selected').attr('data-attribute_name'),
                        data_is_custom = $(el).find('option:selected').attr('data-is_custom'),
                        data_price_extra = $(el).find('option:selected').html().trim().split('&nbsp;')[1],
                        data_display_currency_symbol = $(el).find('option:selected').attr('data-display_currency_symbol');
                    }
                    if (data_is_custom) {
                        var data_custom_value = $('input.variant_custom_value[data-attribute_value_id=' + data_value_id + ']').val();
                    }

                    if (!data_price_extra) {
                        data_price_extra = '0.0'
                    }

                    if (value) {
                        var env, stepDetailsHtml;
                        if ($(el).parent().is('label')) {
                            /* @todo >> @bud-e <<
                             *      ** Minor Fix (If still occurs) **
                             *      Use Case for color attribute (left & right side)
                             *      Left side color but right side its become image
                             *      It should be color on both side...
                             */
                            var image_url = "/website/image/product.attribute.value/" + data_value_id + "/image/90x90";
                            env = {
                                data_is_custom: data_is_custom,
                                current_step: current_step,
                                image_url: image_url,
                                value: value,
                                data_value_id: data_value_id,
                                data_value_name: data_value_name,
                                data_attribute_name: data_attribute_name,
                                data_price_extra: parseFloat(data_price_extra.replace(/,/g,'')).toFixed(2),
                                data_display_currency_symbol: data_display_currency_symbol,
                                data_custom_value: data_custom_value,
                            };
                            stepDetailsHtml = QWeb.render('display_selected_values_on_each_steps_with_image', env);
                        } else {
                            env = {
                                data_is_custom: data_is_custom,
                                current_step: current_step,
                                value: value,
                                data_value_id: data_value_id,
                                data_value_name: data_value_name,
                                data_attribute_name: data_attribute_name,
                                data_price_extra: parseFloat(data_price_extra.replace(/,/g,'')).toFixed(2),
                                data_display_currency_symbol: data_display_currency_symbol,
                                data_custom_value: data_custom_value,
                            };
                            stepDetailsHtml = QWeb.render('display_selected_values_on_each_steps_without_image', env);
                        }
                        $(stepDetailsHtml).appendTo($parent.find('div.selected_values_on_each_steps'));
                    }
                });

                var steps_combination = [];
                _.each($parent.find('div.selected_values_on_each_steps div[class^="values_from_step_id_"]'), function(processed_step) {
                    var selected_step = $(processed_step).find('input').val();
                    steps_combination.push(parseInt(selected_step));
                });
                combination = steps_combination;
            }

            self._checkExclusions($parent, combination);

            ajax.jsonRpc(this._getUri('/product_configurator/get_combination_info'), 'call', {
                product_template_id: parseInt($parent.find('.product_template_id').val()),
                product_id: this._getProductId($parent),
                combination: combination,
                add_qty: parseInt(qty),
                pricelist_id: self.pricelistId || false,
            }).then(function (combinationData) {
                self._onChangeCombination(ev, $parent, combinationData);

                // Disable the Add button, only enable when its last/preview step
                $parent.parents('.modal').find('.o_sale_product_configurator_add').addClass('disabled');
                $parent.parents('.o_product_configurator').find('.open_pcf_lookup_report_button_container').addClass('d-none');

                if ($('div.preview_img_from_media_bank').length > 0) {
                    $parent.parents('.modal').find('.o_sale_product_configurator_add').removeClass('disabled');
                    if ($parent.parents('.o_product_configurator').find('footer').attr('invisible') &&
                        $parent.parents('.o_product_configurator').find('footer').attr('invisible') ===
                        "context.get('pcf_lookup', False)") {
                        $parent.parents('.o_product_configurator').find('.open_pcf_lookup_report_button_container').removeClass('d-none');
                    }
                }
            });
        },

        /**
         * Triggers the price computation and other variant specific changes
         *
         * @param {$.Element} $container
         */
        triggerVariantChange: function ($container) {
            this._super.apply(this, arguments);
            if ($container.find('input.all_configure_steps').val() === '1') {
                var step_id = $container.find('div.carousel-item.active').attr('data-step-id');
                // Init first step by default while selecting product in configurator wizard
                if (step_id !== 'preview_step') {
                    this.firstConfigureStep($container);
                }
            }
        },

        /**
         * Will return a deferred:
         *
         * - If the product already exists, immediately resolves it with the product_id
         * - If the product does not exist yet ("dynamic" variant creation), this method will
         *   create the product first and then resolve the deferred with the created product's id
         *
         * @param {$.Element} $container the container to look into
         * @param {integer} productId the product id
         * @param {integer} productTemplateId the corresponding product template id
         * @param {boolean} useAjax wether the rpc call should be done using ajax.jsonRpc or using _rpc
         * @returns {$.Deferred} the deferred that will be resolved with a {integer} productId
         */
        selectOrCreateProduct: function ($container, productId, productTemplateId, useAjax) {
            var self = this;
            productId = parseInt(productId);
            productTemplateId = parseInt(productTemplateId);
            var productReady = $.Deferred();

            var step_id = $container.find('div.carousel-item.active').attr('data-step-id');
            var final_combination = [];
            var params, route;
            if (step_id === 'preview_step') {
                var all_processed_steps = $('div[class^="values_from_step_id_"]');
                _.each(all_processed_steps, function(processed_step) {
                    var selected_step = $(processed_step).find('input').val();
                    final_combination.push(parseInt(selected_step));
                });

                params = {
                    product_template_id: productTemplateId,
                    product_template_attribute_value_ids:
                        JSON.stringify(final_combination),
                };

                // Note about 12.0 compatibility: this route will not exist if
                // updating the code but not restarting the server. (404)
                // We don't handle that compatibility because the previous code was
                // not working either: it was making an RPC that failed with any
                // non-admin user anyway. To use this feature, restart the server.
                route = '/product_configurator/create_product_variant';
                if (useAjax) {
                    productReady = ajax.jsonRpc(route, 'call', params);
                } else {
                    productReady = this._rpc({route: route, params: params});
                }

            } else {
                if (productId) {
                    productReady.resolve(productId);
                } else {
                    params = {
                        product_template_id: productTemplateId,
                        product_template_attribute_value_ids:
                            JSON.stringify(self.getSelectedVariantValues($container)),
                    };

                    // Note about 12.0 compatibility: this route will not exist if
                    // updating the code but not restarting the server. (404)
                    // We don't handle that compatibility because the previous code was
                    // not working either: it was making an RPC that failed with any
                    // non-admin user anyway. To use this feature, restart the server.
                    route = '/product_configurator/create_product_variant';
                    if (useAjax) {
                        productReady = ajax.jsonRpc(route, 'call', params);
                    } else {
                        productReady = this._rpc({route: route, params: params});
                    }
                }
            }
            return productReady;
        },

        /**
         * Copy of ``selectOrCreateProduct`` but only used in PCF Lookup
         * @param $container
         * @param productId
         * @param productTemplateId
         * @param useAjax
         * @returns {Promise}
         */
        selectOrCreateProductPcfLookup: function ($container, productId, productTemplateId, useAjax) {
            var self = this;
            productId = parseInt(productId);
            productTemplateId = parseInt(productTemplateId);
            var productReady = $.Deferred();

            var step_id = $container.find('div.carousel-item.active').attr('data-step-id');
            var final_combination = [];
            var params, route;
            if (step_id === 'preview_step') {
                var all_processed_steps = $('div[class^="values_from_step_id_"]');
                _.each(all_processed_steps, function(processed_step) {
                    var selected_step = $(processed_step).find('input').val();
                    final_combination.push(parseInt(selected_step));
                });

                params = {
                    product_template_id: productTemplateId,
                    product_template_attribute_value_ids:
                        JSON.stringify(final_combination),
                };

                // Note about 12.0 compatibility: this route will not exist if
                // updating the code but not restarting the server. (404)
                // We don't handle that compatibility because the previous code was
                // not working either: it was making an RPC that failed with any
                // non-admin user anyway. To use this feature, restart the server.
                route = '/product_configurator/create_product_variant_pcf_lookup';
                if (useAjax) {
                    productReady = ajax.jsonRpc(route, 'call', params);
                } else {
                    productReady = this._rpc({route: route, params: params});
                }

            } else {
                if (productId) {
                    productReady.resolve(productId);
                } else {
                    params = {
                        product_template_id: productTemplateId,
                        product_template_attribute_value_ids:
                            JSON.stringify(self.getSelectedVariantValues($container)),
                    };

                    // Note about 12.0 compatibility: this route will not exist if
                    // updating the code but not restarting the server. (404)
                    // We don't handle that compatibility because the previous code was
                    // not working either: it was making an RPC that failed with any
                    // non-admin user anyway. To use this feature, restart the server.
                    route = '/product_configurator/create_product_variant_pcf_lookup';
                    if (useAjax) {
                        productReady = ajax.jsonRpc(route, 'call', params);
                    } else {
                        productReady = this._rpc({route: route, params: params});
                    }
                }
            }
            return productReady;
        },

        /**
         * While selecting configurable product in configuration wizard,
         * first step is auto loaded
         *
         * @param {$.Element} $container
         */
        firstConfigureStep: function ($container) {
            var self = this;
            var product_template_id = $container.find('input.product_template_id').val();
            var step_id = $container.find('div.carousel-item.active').attr('data-step-id');
            this._rpc({
                route: '/product_configurator/configure/steps',
                params: {
                    product_template_id: product_template_id,
                    pricelist_id: self.pricelistId || false,
                    step_id: step_id,
                    final_combination: [],
                }
            }).then(function (configuratorStepHtml) {
                var $configuratorStepContainer = self.$('div.configuration_step_content');
                $configuratorStepContainer.empty();
                var $configuratorStepHtml = $(configuratorStepHtml);
                $configuratorStepHtml.appendTo($configuratorStepContainer);
            });

            // Disable the Add button, only enable when its last/preview step
            $('.modal').find('.o_sale_product_configurator_add').addClass('disabled');
            $('.o_product_configurator').find('.open_pcf_lookup_report_button_container').addClass('d-none');

            if ($('div.preview_img_from_media_bank').length > 0) {
                $('.modal').find('.o_sale_product_configurator_add').removeClass('disabled');
                if ($('.o_product_configurator').find('footer').attr('invisible') &&
                    $('.o_product_configurator').find('footer').attr('invisible') ===
                    "context.get('pcf_lookup', False)") {
                    $('.o_product_configurator').find('.open_pcf_lookup_report_button_container').removeClass('d-none');
                }
            }
        },

        /**
         * Load next/previous step for configurable product
         *
         * @param {MouseEvent} ev
         */
        _onChangeConfigureStep: function (ev) {
            ev.preventDefault();

            var self = this;
            var $container = $(ev.target).closest('.js_product');

            // Do not go further if any options not selected in current step
            if ($(ev.target).closest('a.configuration_step').attr('data-slide') === 'next') {
                var variantsValuesSelectors = [
                    'input.js_variant_change',
                    'select.js_variant_change'
                ];
                var all_answered = true;
                _.each($container.find(variantsValuesSelectors.join(', ')), function (el) {
                    var name = $(el).attr("name");
                    if($(el).is('input') && $("input:radio[name="+name+"]:checked").length === 0) {
                        all_answered = false;
                    }
                    if($(el).is('select') && !$(el).val()) {
                        all_answered = false;
                    }
                });

                if (!all_answered) {
                    self.do_warn(_t("Please, Choose option(s) first to move forward."));
                    return false;
                }
            }

            var product_template_id = $(ev.target).closest('.js_product').find('input.product_template_id').val();

            /**
             * Have 2 options with pros/cons...
             * slide.bs.carousel --> This event fires immediately when the slide instance method is invoked.
             * slid.bs.carousel  -->  This event is fired when the carousel has completed its slide transition.
             *
             * Using `off()` to detach multiple slide/slid calls
             */
            $('#carouselStepsControls').off().on('slide.bs.carousel', function (ev) {
                var step_id = $(ev.relatedTarget).attr('data-step-id');
                var final_combination = []
                if (step_id === 'preview_step') {
                    var all_processed_steps = $('div[class^="values_from_step_id_"]');
                    _.each(all_processed_steps, function(processed_step) {
                        var selected_step = $(processed_step).find('input').val();
                        final_combination.push(parseInt(selected_step));
                    });
                    // show +/- quantity buttons only at preview step
                    $('div.css_quantity').removeClass('d-none');
                } else {
                    // hide +/- quantity buttons if current step is not preview step
                    $('div.css_quantity').addClass('d-none');
                }

                self._rpc({
                    route: '/product_configurator/configure/steps',
                    params: {
                        product_template_id: product_template_id,
                        pricelist_id: self.pricelistId || false,
                        step_id: step_id,
                        final_combination: final_combination,
                    }
                }).then(function (configuratorStepHtml) {
                    var $configuratorStepContainer = self.$('div.configuration_step_content');
                    $configuratorStepContainer.empty();
                    var $configuratorStepHtml = $(configuratorStepHtml);
                    $configuratorStepHtml.appendTo($configuratorStepContainer);

                    var attribute_exclusions = JSON.parse($('ul.js_add_cart_variants').attr('data-attribute_exclusions'));
                    var all_processed_steps = $('div[class^="values_from_step_id_"]');

                    // Hide the exclusion option instead of disabled it in Steps
                    _.each(all_processed_steps, function(processed_step) {
                        var selected_step = $(processed_step).find('input').val();
                        _.each(attribute_exclusions['exclusions'][selected_step], function(step) {
                            if ($configuratorStepHtml.find('input[value=' + step + ']').length > 0) {
                                $configuratorStepHtml.find('input[value=' + step + ']').closest('li').addClass('d-none');
                            }
                            if ($configuratorStepHtml.find('option[value=' + step + ']').length > 0) {
                                $configuratorStepHtml.find('option[value=' + step + ']').addClass('d-none');
                            }
                        });
                    });

                    // Disable the Add button, only enable when its last/preview step
                    $('.modal').find('.o_sale_product_configurator_add').addClass('disabled');
                    $('.o_product_configurator').find('.open_pcf_lookup_report_button_container').addClass('d-none');

                    if ($('div.preview_img_from_media_bank').length > 0) {
                        $('.modal').find('.o_sale_product_configurator_add').removeClass('disabled');
                        if ($('.o_product_configurator').find('footer').attr('invisible') &&
                            $('.o_product_configurator').find('footer').attr('invisible') ===
                            "context.get('pcf_lookup', False)") {
                            $('.o_product_configurator').find('.open_pcf_lookup_report_button_container').removeClass('d-none');
                            $('.o_product_configurator').find('.open_pcf_lookup_report_button_container .pcf_lookup_report_details').empty();
                            $('.o_product_configurator').find('.open_pcf_lookup_report_button_container .compute_max_produce_qty').addClass('d-none');
                            $('.o_product_configurator').find('.open_pcf_lookup_report_button_container .result-max-produce-qty').empty();
                        }
                    }
                });
            });
        },

        _openPCFLookup: function (ev) {
            ev.preventDefault();
            var self = this;
            var productTemplateSelector = [
                'input[type="hidden"][class="product_template_id"]',
            ];
            var productSelector = [
                'input[type="hidden"][name="product_id"]',
                'input[type="radio"][name="product_id"]:checked'
            ];
            var quantitySelector = [
                'input[type="text"][name="add_qty"]',
            ];
            var productTemplateId = parseInt(self.$el.find(productTemplateSelector.join(', ')).first().val(), 10);
            var quantity = parseInt(self.$el.find(quantitySelector.join(', ')).first().val(), 10);
            var productId = parseInt(self.$el.find(productSelector.join(', ')).first().val(), 10);
            var productReady = self.selectOrCreateProductPcfLookup(
                self.$el,
                productId,
                productTemplateId,
                false
            );

            productReady.done(function (productId) {
                self.$el.find(productSelector.join(', ')).val(productId);
                if ((!productId || productId === 0) || (!productTemplateId || productTemplateId === 0)) {
                    self.do_warn(_t("Something is wrong!"), _t("Product is missing."));
                } else {
                    var args = [
                        productTemplateId,
                        productId,
                        quantity || 1,
                    ];
                    return self._rpc({
                        model: 'pcf.lookup',
                        method: 'get_html',
                        args: args,
                        context: this.given_context,
                    }).then(function (result) {
                        framework.blockUI();
                        self.$('.pcf_lookup_report_details').empty();
                        self.$('.pcf_lookup_report_details').append(result['lines']);
                        // Remove the link from each action,
                        // due to limitation of the current code structure
                        $('a[class="o_mrp_bom_action"]').contents().unwrap();

                        // Enable the button which calculate the Max Producible Qty
                        self.$('.compute_max_produce_qty').removeClass('d-none');
                        framework.unblockUI();
                    });
                }
            });
        },

        render_html: function(event, $el, result){
            if (result.indexOf('mrp.document') > 0) {
                if (this.$('.o_mrp_has_attachments').length === 0) {
                    var column = $('<th/>', {
                        class: 'o_mrp_has_attachments',
                        title: 'Files attached to the product Attachments',
                        text: 'Attachments',
                    });
                    this.$('table thead th:last-child').after(column);
                }
            }
            $el.after(result);
            $(event.currentTarget).toggleClass('o_mrp_bom_foldable o_mrp_bom_unfoldable fa-caret-right fa-caret-down');
            // Remove the link from each action,
            // due to limitation of the current code structure
            $('a[class="o_mrp_bom_action"]').contents().unwrap();
        },
        get_bom: function(event) {
            var self = this;
            var $parent = $(event.currentTarget).closest('tr');
            var activeID = $parent.data('id');
            var productID = $parent.data('product_id');
            var lineID = $parent.data('line');
            var qty = $parent.data('qty');
            var level = $parent.data('level') || 0;
            return this._rpc({
                model: 'pcf.lookup',
                method: 'get_bom',
                args: [
                    activeID,
                    productID,
                    parseFloat(qty),
                    lineID,
                    level + 1,
                ]
            }).then(function (result) {
                self.render_html(event, $parent, result);
            });
        },
        _onClickUnfold: function (ev) {
            var redirect_function = $(ev.currentTarget).data('function');
            this[redirect_function](ev);
        },
        _onClickFold: function (ev) {
            this._removeLines($(ev.currentTarget).closest('tr'));
            $(ev.currentTarget).toggleClass('o_mrp_bom_foldable o_mrp_bom_unfoldable fa-caret-right fa-caret-down');
        },
        _removeLines: function ($el) {
            var self = this;
            var activeID = $el.data('id');
            _.each(this.$('tr[parent_id='+ activeID +']'), function (parent) {
                var $parent = self.$(parent);
                var $el = self.$('tr[parent_id='+ $parent.data('id') +']');
                if ($el.length) {
                    self._removeLines($parent);
                }
                $parent.remove();
            });
        },

        _computeMaxProduceQty: function () {
            framework.blockUI();
            var self = this;
            var productTemplateSelector = [
                'input[type="hidden"][class="product_template_id"]',
            ];
            var productSelector = [
                'input[type="hidden"][name="product_id"]',
                'input[type="radio"][name="product_id"]:checked'
            ];
            var quantitySelector = [
                'input[type="text"][name="add_qty"]',
            ];
            var productTemplateId = parseInt(self.$el.find(productTemplateSelector.join(', ')).first().val(), 10);
            var quantity = parseInt(self.$el.find(quantitySelector.join(', ')).first().val(), 10);
            var productId = parseInt(self.$el.find(productSelector.join(', ')).first().val(), 10);

            var args = [
                productTemplateId,
                productId,
                quantity || 1,
            ];
            return self._rpc({
                model: 'pcf.lookup',
                method: 'get_all_lines',
                args: args,
                context: self.given_context,
            }).then(function (result) {
                self.$('.result-max-produce-qty').append(result);
                framework.unblockUI();
            });
        },

    });

});
