from odoo.tests.common import TransactionCase


class TestMarkantProductSetup(TransactionCase):
    def setUp(self):
        super(TestMarkantProductSetup, self).setUp()

        self.product_max = self.env['product.template'].create({
            'name': 'Product MAX',
            'configurable_ok': True,
            'first_digit_article_code': 'MAX',
        })

        self._add_beamtype_attribute()  # Steel, Aluminium
        self._add_legtype_attribute()  # T-Leg, C-Leg
        self._add_legcolor_attribute()  # White, Grey, Driftwood
        self._add_worktopshape_attribute()  # 80*80, 120*120, 160*160
        self._add_worktoptype_attribute()  # Melamine 20mm, Melamine 25mm
        self._add_worktopcolor_attribute()  # White, Driftwood, Light Apple

    def _add_beamtype_attribute(self):
        self.beamtype_attribute = self.env[
            'product.attribute'].create({
                'name': 'Beam Type',
                'create_variant': 'dynamic',
                'sequence': 1
            })

        self.beamtype_steel = self.env[
            'product.attribute.value'].create({
                'name': 'Steel',
                'attribute_id': self.beamtype_attribute.id,
                'article_code': 'st',
                'sequence': 1,
            })
        self.beamtype_aluminium = self.env[
            'product.attribute.value'].create({
                'name': 'Aluminium',
                'attribute_id': self.beamtype_attribute.id,
                'article_code': 'al',
                'sequence': 2,
            })

        self._add_beamtype_attribute_line()

    def _add_beamtype_attribute_line(self):
        self.product_max_beamtype_attribute_lines = self.env[
            'product.template.attribute.line'].create({
                'sequence': 1,
                'product_tmpl_id': self.product_max.id,
                'attribute_id': self.beamtype_attribute.id,
                'value_ids': [(6, 0, [self.beamtype_steel.id,
                                      self.beamtype_aluminium.id])],
            })

        self.product_max_beamtype_attribute_lines.product_template_value_ids[
            0].price_extra = 100  # Extra price for Steel

    def _add_legtype_attribute(self):
        self.legtype_attribute = self.env[
            'product.attribute'].create({
                'name': 'Leg Type',
                'create_variant': 'dynamic',
                'sequence': 2
            })

        self.legtype_t = self.env[
            'product.attribute.value'].create({
                'name': 'T Leg',
                'attribute_id': self.legtype_attribute.id,
                'article_code': 'tl',
                'sequence': 1,
            })
        self.legtype_c = self.env[
            'product.attribute.value'].create({
                'name': 'C Leg',
                'attribute_id': self.legtype_attribute.id,
                'article_code': 'cl',
                'sequence': 2,
            })

        self._add_legtype_attribute_line()

    def _add_legtype_attribute_line(self):
        self.product_max_legtype_attribute_lines = self.env[
            'product.template.attribute.line'].create({
                'sequence': 2,
                'product_tmpl_id': self.product_max.id,
                'attribute_id': self.legtype_attribute.id,
                'value_ids': [(6, 0, [self.legtype_t.id,
                                      self.legtype_c.id])],
            })

    def _add_legcolor_attribute(self):
        self.legcolor_attribute = self.env[
            'product.attribute'].create({
                'name': 'Leg Color',
                'create_variant': 'dynamic',
                'sequence': 3
            })

        self.legcolor_white = self.env[
            'product.attribute.value'].create({
                'name': 'White',
                'attribute_id': self.legcolor_attribute.id,
                'article_code': 'w10',
                'sequence': 1,
            })
        self.legcolor_grey = self.env[
            'product.attribute.value'].create({
                'name': 'Grey',
                'attribute_id': self.legcolor_attribute.id,
                'article_code': 'g20',
                'sequence': 2,
            })
        self.legcolor_driftwood = self.env[
            'product.attribute.value'].create({
                'name': 'Drift Wood',
                'attribute_id': self.legcolor_attribute.id,
                'article_code': 'd30',
                'sequence': 3,
            })

        self._add_legcolor_attribute_line()

    def _add_legcolor_attribute_line(self):
        self.product_max_legcolor_attribute_lines = self.env[
            'product.template.attribute.line'].create({
                'sequence': 3,
                'product_tmpl_id': self.product_max.id,
                'attribute_id': self.legcolor_attribute.id,
                'value_ids': [(6, 0, [self.legcolor_white.id,
                                      self.legcolor_grey.id,
                                      self.legcolor_driftwood.id])],
            })

    def _add_worktopshape_attribute(self):
        self.worktopshape_attribute = self.env[
            'product.attribute'].create({
                'name': 'Worktop Shape',
                'create_variant': 'dynamic',
                'sequence': 4
            })

        self.worktopshape_80 = self.env[
            'product.attribute.value'].create({
                'name': '80 * 80',
                'attribute_id': self.worktopshape_attribute.id,
                'article_code': '80',
                'sequence': 1,
            })
        self.worktopshape_120 = self.env[
            'product.attribute.value'].create({
                'name': '120 * 120',
                'attribute_id': self.worktopshape_attribute.id,
                'article_code': '120',
                'sequence': 2,
            })
        self.worktopshape_160 = self.env[
            'product.attribute.value'].create({
                'name': '160 * 160',
                'attribute_id': self.worktopshape_attribute.id,
                'article_code': '160',
                'sequence': 3,
            })

        self._add_worktopshape_attribute_line()

    def _add_worktopshape_attribute_line(self):
        self.product_max_worktopshape_attribute_lines = self.env[
            'product.template.attribute.line'].create({
                'sequence': 4,
                'product_tmpl_id': self.product_max.id,
                'attribute_id': self.worktopshape_attribute.id,
                'value_ids': [(6, 0, [self.worktopshape_80.id,
                                      self.worktopshape_120.id,
                                      self.worktopshape_160.id])],
            })

        # Extra price for 120 * 120
        self.product_max_worktopshape_attribute_lines.\
            product_template_value_ids[1].price_extra = 25

        # Extra price for 160 * 160
        self.product_max_worktopshape_attribute_lines. \
            product_template_value_ids[2].price_extra = 50

    def _add_worktoptype_attribute(self):
        self.worktoptype_attribute = self.env[
            'product.attribute'].create({
                'name': 'Worktop Type',
                'create_variant': 'dynamic',
                'sequence': 5
            })

        self.worktoptype_20 = self.env[
            'product.attribute.value'].create({
                'name': 'Melamine 20mm',
                'attribute_id': self.worktoptype_attribute.id,
                'article_code': 'm20',
                'sequence': 1,
            })
        self.worktoptype_25 = self.env[
            'product.attribute.value'].create({
                'name': 'Melamine 25mm',
                'attribute_id': self.worktoptype_attribute.id,
                'article_code': 'm25',
                'sequence': 2,
            })

        self._add_worktoptype_attribute_line()

    def _add_worktoptype_attribute_line(self):
        self.product_max_worktoptype_attribute_lines = self.env[
            'product.template.attribute.line'].create({
                'sequence': 5,
                'product_tmpl_id': self.product_max.id,
                'attribute_id': self.worktoptype_attribute.id,
                'value_ids': [(6, 0, [self.worktoptype_20.id,
                                      self.worktoptype_25.id])],
                'include_inside_d': False,
            })

    def _add_worktopcolor_attribute(self):
        self.worktopcolor_attribute = self.env[
            'product.attribute'].create({
                'name': 'Worktop Color',
                'create_variant': 'dynamic',
                'sequence': 6
            })

        self.worktopcolor_white = self.env[
            'product.attribute.value'].create({
                'name': 'White',
                'attribute_id': self.worktopcolor_attribute.id,
                'article_code': '111',
                'sequence': 1,
            })
        self.worktopcolor_driftwood = self.env[
            'product.attribute.value'].create({
                'name': 'Driftwood',
                'attribute_id': self.worktopcolor_attribute.id,
                'article_code': '222',
                'sequence': 2,
            })
        self.worktopcolor_lightapple = self.env[
            'product.attribute.value'].create({
                'name': 'Light Apple',
                'attribute_id': self.worktopcolor_attribute.id,
                'article_code': '333',
                'sequence': 3,
            })

        self._add_worktopcolor_attribute_line()

    def _add_worktopcolor_attribute_line(self):
        self.product_max_worktopcolor_attribute_lines = self.env[
            'product.template.attribute.line'].create({
                'sequence': 6,
                'product_tmpl_id': self.product_max.id,
                'attribute_id': self.worktopcolor_attribute.id,
                'value_ids': [(6, 0, [self.worktopcolor_white.id,
                                      self.worktopcolor_driftwood.id,
                                      self.worktopcolor_lightapple.id])],
            })

    # Method copy from
    # odoo/addons/product/tests/test_product_attribute_value_config.py
    def _get_product_template_attribute_value(self, product_attribute_value,
                                              model=False):
        """
            Return the `product.template.attribute.value` matching
                `product_attribute_value` for self.

            :param: recordset of one product.attribute.value
            :return: recordset of one product.template.attribute.value if found
                else empty
        """
        if not model:
            model = self.product_max
        return model._get_valid_product_template_attribute_lines().filtered(
            lambda l: l.attribute_id == product_attribute_value.attribute_id
        ).product_template_value_ids.filtered(
            lambda v: v.product_attribute_value_id == product_attribute_value
        )
