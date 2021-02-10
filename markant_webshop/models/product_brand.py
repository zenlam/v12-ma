from odoo import api, fields, models, tools, _


class ProductBrand(models.Model):
    _name = "product.brand"
    _description = "Product Brand"
    _order = 'name asc'

    name = fields.Char(string='Name', copy=False,
                       translate=True, required=True)
    image = fields.Binary("Logo", attachment=True,
                          help="This field holds the image used as "
                               "logo for the brand, limited to 1024x1024px.")
    image_medium = fields.Binary("Medium-sized image", attachment=True,
                                 help="Medium-sized logo of the brand. "
                                      "It is automatically "
                                      "resized as a 128x128px image, "
                                      "with aspect ratio preserved. "
                                      "Use this field in form views or "
                                      "some kanban views.")
    image_small = fields.Binary("Small-sized image", attachment=True,
                                help="Small-sized logo of the brand. "
                                     "It is automatically "
                                     "resized as a 64x64px image, "
                                     "with aspect ratio preserved. "
                                     "Use this field anywhere a small "
                                     "image is required.")

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Brand name is already exist!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            tools.image_resize_images(vals)
        return super(ProductBrand, self).create(vals_list)

    @api.multi
    def write(self, vals):
        tools.image_resize_images(vals)
        return super(ProductBrand, self).write(vals)
