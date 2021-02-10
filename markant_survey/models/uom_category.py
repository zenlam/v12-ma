from odoo import api, fields, models


class UomCategory(models.Model):
    _inherit = 'uom.category'

    is_length = fields.Boolean('Length', default=False)
    is_weight = fields.Boolean('Weight', default=False)
    is_hight = fields.Boolean('Hight', default=False)
    is_depth = fields.Boolean('Depth', default=False)

    @api.multi
    def check_duplicate_type(self):
        for cate in self:
            if cate.is_length is False and cate.is_weight is False \
                    and cate.is_hight is False and cate.is_depth is False:
                return True
            domain = ('id', '!=', cate.id)
            length = False
            weight = False
            hight = False
            depth = False
            if cate.is_length:
                length = self.search([('is_length', '=', cate.is_length), domain], limit=1)
            if cate.is_weight:
                weight = self.search([('is_weight', '=', cate.is_weight), domain], limit=1)
            if cate.is_hight:
                hight = self.search([('is_hight', '=', cate.is_hight), domain], limit=1)
            if cate.is_depth:
                depth = self.search([('is_depth', '=', cate.is_depth), domain], limit=1)
            if length or weight or hight or depth:
                return False
        return True

    _constraints = [(check_duplicate_type, 'Product UOM category cannot have same type',
                     ['is_length', 'is_weight', 'is_hight', 'is_depth'])]
