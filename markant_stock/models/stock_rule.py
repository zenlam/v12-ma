from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom,
                               location_id, name, origin, values, group_id):
        move_values = super(StockRule, self)._get_stock_move_values(
            product_id, product_qty, product_uom, location_id,
            name, origin, values, group_id)
        article_description = False
        article_description_move = False
        if values.get('sale_line_id'):
            so_line = self.env['sale.order.line'].browse(values.get('sale_line_id'))
            article_description = so_line.section_name
            article_description_move = so_line.section_name
            if not article_description:
                article_description = 'No Order Point'
                article_description_move = 'No Order Point'
            move_values['allow_partial'] = so_line.allow_partial
            if so_line.delivery_date:
                move_values['date_expected'] = so_line.delivery_date
        move_values['article_description'] = article_description
        move_values['article_description_move'] = article_description_move
        return move_values

    def _run_pull(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        if not self.location_src_id:
            msg = _('No source location defined on stock rule: %s!') % (
                self.name, )
            raise UserError(msg)

        bom = self._get_matching_bom(product_id, values)
        final_attribute_list = product_id.attribute_value_ids.ids

        self.check_for_multi_bom_scenario(product_id, bom,
                                          final_attribute_list)

        return super(StockRule, self)._run_pull(
            product_id, product_qty, product_uom, location_id,
            name, origin, values)
