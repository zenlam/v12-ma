import base64
import requests
from io import BytesIO

from odoo import http, fields
from odoo.http import request
from odoo.addons.sale.controllers.product_configurator import ProductConfiguratorController


class MarkantProductConfiguratorController(ProductConfiguratorController):
    @http.route(['/product_configurator/configure/steps'],
                type='json', auth="user", methods=['POST'])
    def configure_steps(self, product_template_id, pricelist_id, step_id, final_combination, **kw):
        product_template = request.env['product.template'].browse(
            int(product_template_id))
        to_currency = product_template.currency_id
        pricelist = self._get_pricelist(pricelist_id)

        if pricelist:
            product_template = product_template.with_context(pricelist=pricelist.id, partner=request.env.user.partner_id)
            to_currency = pricelist.currency_id

        if step_id != 'preview_step':
            config_step = request.env['product.config.steps.attr'].search(
                [('product_tmpl_id', '=', int(product_template_id)),
                 ('step_id', '=', int(step_id))])
            config_step_attrs = config_step.attribute_ids
            attribute_lines = request.env[
                'product.template.attribute.line'].search(
                [('attribute_id', 'in', config_step_attrs.ids),
                 ('product_tmpl_id', '=', int(product_template_id))])
            values = {
                'product': product_template,
                # get_attribute_exclusions deprecated, use product method
                'get_attribute_exclusions': self._get_attribute_exclusions,
                'steps': product_template.product_config_steps_ids,
                'attribute_lines': attribute_lines,
                'to_currency': to_currency,
                'pricelist': pricelist
            }
        else:
            final_combination = request.env[
                'product.template.attribute.value'].browse(final_combination)

            attribute_values = final_combination.mapped(
                'product_attribute_value_id')._without_no_variant_attributes()

            default_code = product_template.d_number_generator(
                attribute_values)

            media_bank_start_url = \
                request.env.user.company_id.media_bank_start_url
            media_bank_end_url = \
                request.env.user.company_id.media_bank_end_url

            if default_code and len(default_code) > 4:
                image_url = '%s/%s/%s/%s/%s/%s.%s' % (
                    media_bank_start_url, default_code[0],
                    default_code[1], default_code[2],
                    default_code[3], default_code, media_bank_end_url)
                if requests.get(image_url).status_code == 200:
                    buffered = BytesIO(requests.get(image_url).content)
                    base64_str = base64.b64encode(buffered.getvalue())
                else:
                    base64_str = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC" \
                                 "1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAA" \
                                 "AASUVORK5CYII="
            else:
                base64_str = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC" \
                             "1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAA" \
                             "AASUVORK5CYII="

            values = {
                'product': product_template,
                # get_attribute_exclusions deprecated, use product method
                'get_attribute_exclusions': self._get_attribute_exclusions,
                'steps': product_template.product_config_steps_ids,
                'preview_step': True,
                'base64_str': base64_str,
                'd_number': default_code,
                'to_currency': to_currency,
                'pricelist': pricelist
            }
        return request.env['ir.ui.view'].render_template(
            'sale.variants', values)

    @http.route(['/product_configurator/configure'],
                type='json', auth="user", methods=['POST'])
    def configure(self, product_id, pricelist_id, **kw):
        add_qty = int(kw.get('add_qty', 1))
        product_template = request.env['product.template'].browse(
            int(product_id))
        to_currency = product_template.currency_id
        pricelist = self._get_pricelist(pricelist_id)

        if pricelist:
            product_template = product_template.with_context(
                pricelist=pricelist.id, partner=request.env.user.partner_id)
            to_currency = pricelist.currency_id

        all_sorted_steps = False
        first_step = False
        all_next_steps = False
        no_steps_available = False

        if product_template.product_config_steps_ids:
            all_sorted_steps = product_template.product_config_steps_ids.sorted(
                key=lambda r: r['sequence'])
            first_step = all_sorted_steps[0]
            all_next_steps = all_sorted_steps - first_step
        else:
            no_steps_available = True

        return request.env['ir.ui.view'].render_template(
            "sale.product_configurator_configure", {
                'product': product_template,
                # to_currency deprecated, get it from the pricelist or product directly
                'to_currency': to_currency,
                'pricelist': pricelist,
                'add_qty': add_qty,
                # get_attribute_exclusions deprecated, use product method
                'get_attribute_exclusions': self._get_attribute_exclusions,
                'steps': all_sorted_steps,
                'first_step': first_step,
                'all_next_steps': all_next_steps,
                'no_steps_available': no_steps_available
            })

    @http.route(['/product_configurator/create_product_variant_pcf_lookup'],
                type='json', auth="user", methods=['POST'])
    def create_product_variant_pcf_lookup(
            self, product_template_id,
            product_template_attribute_value_ids, **kwargs):
        return request.env['product.template'].browse(
            int(product_template_id)).create_product_variant_pcf_lookup(
            product_template_attribute_value_ids)
