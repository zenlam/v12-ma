from odoo.addons.markant_product.tests.test_markant_product_setup import TestMarkantProductSetup


class TestProductDNumberGenerator(TestMarkantProductSetup):

    def test_product_variant_dnumber_creation(self):
        # For this first need to pass the combination of different values,
        # and generate the d number for the same
        max_beamtype_steel = self._get_product_template_attribute_value(
            self.beamtype_steel)
        max_beamtype_aluminium = self._get_product_template_attribute_value(
            self.beamtype_aluminium)

        max_legtype_t = self._get_product_template_attribute_value(
            self.legtype_t)
        max_legtype_c = self._get_product_template_attribute_value(
            self.legtype_c)

        max_legcolor_white = self._get_product_template_attribute_value(
            self.legcolor_white)
        max_legcolor_grey = self._get_product_template_attribute_value(
            self.legcolor_grey)
        max_legcolor_driftwood = self._get_product_template_attribute_value(
            self.legcolor_driftwood)

        max_worktopshape_80 = self._get_product_template_attribute_value(
            self.worktopshape_80)
        max_worktopshape_120 = self._get_product_template_attribute_value(
            self.worktopshape_120)
        max_worktopshape_160 = self._get_product_template_attribute_value(
            self.worktopshape_160)

        max_worktoptype_20 = self._get_product_template_attribute_value(
            self.worktoptype_20)
        max_worktoptype_25 = self._get_product_template_attribute_value(
            self.worktoptype_25)

        max_worktopcolor_white = self._get_product_template_attribute_value(
            self.worktopcolor_white)
        max_worktopcolor_driftwood = \
            self._get_product_template_attribute_value(
                self.worktopcolor_driftwood)
        max_worktopcolor_lightapple = \
            self._get_product_template_attribute_value(
                self.worktopcolor_lightapple)

        # D-Number -- Test #01
        # ====================
        #
        # Check that combination is possible or not
        self.assertTrue(self.product_max._is_combination_possible(
            max_beamtype_steel + max_legtype_t + max_legcolor_white +
            max_worktopshape_80 + max_worktoptype_20 + max_worktopcolor_white))

        # For above combination below is the d-number
        # Steel + T Leg + White + 80 * 80 + Melamine 20mm + White
        # st    + tl    + w10   + 80      + m20           + 111
        #
        # Also our First Digit Article Code is: MAX
        #
        # D Number: MAXsttlw1080m20111
        #
        # But from above `Melamine 20mm (Worktop Type)` is not
        # consider inside d-number generator
        #
        # D Number: MAXsttlw1080111
        combination = self.beamtype_steel + self.legtype_t + \
            self.legcolor_white + self.worktopshape_80 + \
            self.worktoptype_20 + self.worktopcolor_white
        dnumber = self.product_max.d_number_generator(combination)
        self.assertEqual(dnumber, 'MAXsttlw1080111')
        print("\n\n**********************************************************")
        print("D-Number -- Test #01 was successful!!")
        print("**********************************************************\n\n")

        # D-Number -- Test #02
        # ====================
        #
        # Check that combination is possible or not
        self.assertTrue(self.product_max._is_combination_possible(
            max_beamtype_aluminium + max_legtype_c + max_worktoptype_25 +
            max_worktopcolor_driftwood + max_worktopshape_160 +
            max_legcolor_grey))

        # For above combination below is the d-number
        # Aluminium + C Leg + Melamine 25mm + Driftwood + 160 * 160 + Grey
        #
        # Apply sequence on above combination...
        # Aluminium + C Leg + Grey + 160 * 160 + Melamine 25mm + Driftwood
        # al        + cl    + g20  + 160       + m25           + 222
        #
        # Also our First Digit Article Code is: MAX
        #
        # D Number: MAXalclg20160m25222
        #
        # But from above `Melamine 25mm (Worktop Type)` is not
        # consider inside d-number generator
        #
        # D Number: MAXalclg20160222
        combination = self.beamtype_aluminium + self.legtype_c + \
            self.worktoptype_25 + self.worktopcolor_driftwood + \
            self.worktopshape_160 + self.legcolor_grey
        dnumber = self.product_max.d_number_generator(combination)
        self.assertEqual(dnumber, 'MAXalclg20160222')
        print("\n\n**********************************************************")
        print("D-Number -- Test #02 was successful!!")
        print("**********************************************************\n\n")
