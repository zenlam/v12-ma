from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import ValidationError, Warning


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    configurator_line_ids = fields.One2many('mrp.bom.conf.line',
                                            'bom_id', 'BoM Conf Lines',
                                            copy=True)

    @api.constrains('product_id', 'product_tmpl_id',
                    'bom_line_ids', 'configurator_line_ids')
    def _check_product_recursion(self):
        for bom in self:
            if bom.product_id:
                if bom.bom_line_ids.filtered(
                        lambda x: x.product_id == bom.product_id):
                    raise ValidationError(_(
                        'BoM line product %s should not be same '
                        'as BoM product.') % bom.display_name)
            else:
                if bom.bom_line_ids.filtered(
                        lambda x: x.product_id.product_tmpl_id == bom.product_tmpl_id):
                    raise ValidationError(_(
                        'BoM line product %s should not be same '
                        'as BoM product.') % bom.display_name)

            # Also check for Configurable Products
            if bom.configurator_line_ids.filtered(
                    lambda x: x.product_tmpl_id == bom.product_tmpl_id):
                raise ValidationError(_(
                    'BoM configurable line product %s should not be '
                    'same as BoM product.') % bom.display_name)


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'
    _order = 'sequence, id'

    @api.multi
    def get_sequence_number(self):
        for rec in self:
            rec.sequence_no = rec.bom_id.bom_line_ids.ids.index(rec.id) + 1

    auto_create = fields.Boolean(string='Auto Created')
    sequence_no = fields.Integer(string='No', readonly=True,
                                 compute=get_sequence_number)


class MrpBomConfLine(models.Model):
    _name = 'mrp.bom.conf.line'
    _description = 'BOM Configuration Product Line'
    _order = 'sequence, id'
    _rec_name = 'product_tmpl_id'

    def _get_default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id').id

    @api.multi
    def get_sequence_number(self):
        for rec in self:
            rec.sequence_no = rec.bom_id.configurator_line_ids.ids\
                                  .index(rec.id) + 1

    bom_id = fields.Many2one('mrp.bom', string='Parent BoM',
                             index=True, ondelete='cascade', required=True)
    bom_id_product_tmpl_id = fields.Many2one(related='bom_id.product_tmpl_id',
                                             store=True)
    product_tmpl_id = fields.Many2one('product.template', required=True,
                                      string='Configurable Product',
                                      domain=[('configurable_ok', '=', True)])
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        default=_get_default_product_uom_id,
        oldname='product_uom', required=True,
        help="Unit of Measure (Unit of Measure) is the unit of "
             "measurement for the inventory control")
    sequence = fields.Integer('Sequence', default=1,
                              help="Gives the sequence order when displaying.")
    bom_ref_id = fields.Many2one('mrp.bom', string='Child BoM')
    product_qty = fields.Float('Quantity', default=1.0,
                               digits=dp.get_precision('Unit of Measure'),
                               required=True)
    attribute_mapping_ids = fields.One2many(
        'mrp.bom.attr.mapping', 'attr_mapping_id',
        stinrg='Attribute Mapping')
    attribute_value_mapping_ids = fields.One2many(
        'mrp.bom.attr.value.mapping', 'value_mapping_id',
        stinrg='Attribute Value Mapping')
    auto_map_done = fields.Boolean(string='Auto Mapping Done', readonly=True)
    sequence_no = fields.Integer(string='No', readonly=True,
                                 compute=get_sequence_number)
    config_selected_attr_ids = fields.Many2many(
        'product.attribute', 'config_product_selected_attr_rel',
        'col1', 'col2', string='Config Attrs')
    manuf_selected_attr_ids = fields.Many2many(
        'product.attribute', 'mauf_product_selected_attr_rel',
        'col1', 'col2', string='Manuf Attrs')
    config_prod_related_value_ids = fields.Many2many(
        'product.attribute.value', 'config_product_values_rel',
        'col1', 'col2', string='Config Related Values',
        compute='_compute_config_prod_value_ids')
    manuf_prod_related_value_ids = fields.Many2many(
        'product.attribute.value', 'manuf_product_values_rel',
        'col1', 'col2', string='Manuf Related Values',
        compute='_compute_manuf_prod_value_ids')

    @api.depends('bom_id.product_tmpl_id')
    def _compute_manuf_prod_value_ids(self):
        if self.bom_id.product_tmpl_id:
            self.manuf_prod_related_value_ids = False
            self.manuf_prod_related_value_ids = \
                [(4, value.id) for line in
                 self.bom_id.product_tmpl_id.attribute_line_ids
                 for value in line.value_ids]

    @api.depends('product_tmpl_id')
    def _compute_config_prod_value_ids(self):
        if self.product_tmpl_id:
            self.config_prod_related_value_ids = False
            self.config_prod_related_value_ids = \
                [(4, value.id) for line in
                 self.product_tmpl_id.attribute_line_ids
                 for value in line.value_ids]

    @api.onchange('attribute_mapping_ids')
    def onchange_attribute_mapping_ids(self):
        if self.attribute_mapping_ids:
            self.config_selected_attr_ids = False
            self.manuf_selected_attr_ids = False
            for line in self.attribute_mapping_ids:
                self.config_selected_attr_ids = \
                    [(4, line.config_prod_attr_id.id)]
                for manuf_attr in line.manuf_prod_attr_ids:
                    self.manuf_selected_attr_ids = \
                        [(4, manuf_attr.id)]
        if not self.attribute_mapping_ids:
            self.config_selected_attr_ids = False
            self.manuf_selected_attr_ids = False

    # Remove default value from context which is came from
    # previous active model.
    #
    # This is default Odoo behavior that `default_field_name` carry-forward
    # into next model if we switch screen through breadcrumbs
    @api.model
    def default_get(self, fields):
        if self._context and self._context.get(
                'default_product_tmpl_id'):
            context = dict(self._context)
            context.pop('default_product_tmpl_id')
            self = self.with_context(context)
        return super(MrpBomConfLine, self).default_get(fields)

    @api.model
    def create(self, vals):
        res = super(MrpBomConfLine, self).create(vals)

        auto_map_check = []

        attr_mapping = []
        attr_value_mapping = []

        selected_attr_mapping = []
        context = self.env.context or {}

        available_attributes = []

        sub_product_attr = [line.attribute_id for line in
                            res.product_tmpl_id.attribute_line_ids]
        main_product_attr = [line.attribute_id for line in
                             res.bom_id.product_tmpl_id.attribute_line_ids]

        sub_product_attr_vals = [value for line in
                                 res.product_tmpl_id.attribute_line_ids
                                 for value in line.value_ids]
        main_product_attr_vals = [value for line in
                                  res.bom_id.product_tmpl_id.attribute_line_ids
                                  for value in line.value_ids]

        if not context.get('import_file'):
            for val in sub_product_attr_vals:
                if val in main_product_attr_vals:
                    attr_value_mapping.append((0, 0, {
                        'config_prod_attr_val_id': val.id,
                        'manuf_prod_attr_val_ids': [(4, val.id)]}))
                    available_attributes.append(val.attribute_id)
                    auto_map_check.append(True)
                else:
                    auto_map_check.append(False)

        available_attributes = list(set(available_attributes))

        if not context.get('import_file'):
            for attr in sub_product_attr:
                if attr in main_product_attr and attr in available_attributes:
                    attr_mapping.append((0, 0, {
                        'config_prod_attr_id': attr.id,
                        'manuf_prod_attr_ids': [(4, attr.id)]}))
                    selected_attr_mapping.append((4, attr.id))
                    auto_map_check.append(True)
                else:
                    auto_map_check.append(False)

        # Attr Values Mapping
        res.attribute_value_mapping_ids = attr_value_mapping

        # Attr Mapping
        res.attribute_mapping_ids = attr_mapping

        # Attr Selected Mapping for Filtering
        res.config_selected_attr_ids = selected_attr_mapping
        res.manuf_selected_attr_ids = selected_attr_mapping

        if not auto_map_check or False in auto_map_check:
            res.auto_map_done = False
        else:
            res.auto_map_done = True
        return res

    @api.multi
    def write(self, vals):
        res = super(MrpBomConfLine, self).write(vals)
        for line in self:
            config_attr = [attr_line.config_prod_attr_id.id
                           for attr_line in line.attribute_mapping_ids]
            config_vals_of_attr = [
                attr_line.config_prod_attr_val_id.attribute_id.id
                for attr_line in line.attribute_value_mapping_ids]
            if not all(elem in config_vals_of_attr for elem in config_attr):
                raise Warning(_('Inside %s (Sequence No: %s) there is '
                                'Attribute Mapping have '
                                'some attribute but related values of '
                                'that attribute does not exist '
                                'inside Attribute Value Mapping.') %
                              (line.product_tmpl_id.name, line.sequence_no))
        return res

    @api.multi
    def open_attribute_and_value_mapping(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'title',
            'res_model': 'mrp.bom.conf.line',
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref(
                'markant_product.mrp_bom_conf_line_form').id,
            'context': {},
        }

    @api.multi
    def open_reference_bom_view(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'title',
            'res_model': 'mrp.bom',
            'res_id': self.bom_ref_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref(
                'mrp.mrp_bom_form_view').id,
            'context': {},
        }

    @api.multi
    def copy_bom_config_line(self):
        self.ensure_one()
        att_map_lst = []
        att_val_map_lst = []
        for att_line in self.attribute_mapping_ids:
            att_map_lst.append(att_line.copy().id)
        for att_val_line in self.attribute_value_mapping_ids:
            att_val_map_lst.append(att_val_line.copy().id)

        new_line = self.with_context({'import_file': True}).copy({
            'attribute_mapping_ids': [(6, 0, att_map_lst)],
            'attribute_value_mapping_ids': [
                (6, 0, att_val_map_lst)]
        })
        new_line.auto_map_done = self.auto_map_done
        return self.bom_id.write({
            'configurator_line_ids': [(4, new_line.id)]
        })

    @api.onchange('product_uom_id')
    def onchange_product_uom_id(self):
        res = {}
        if not self.product_uom_id or not self.product_tmpl_id:
            return res
        if self.product_uom_id.category_id != \
                self.product_tmpl_id.uom_id.category_id:
            self.product_uom_id = self.product_tmpl_id.uom_id.id
            res['warning'] = {'title': _('Warning'), 'message': _(
                'The Product Unit of Measure you chose has a different '
                'category than in the product form.')}
        return res

    @api.onchange('product_tmpl_id')
    def onchange_product_tmpl_id(self):
        if self.product_tmpl_id:
            self.product_uom_id = self.product_tmpl_id.uom_id.id
            reference_bom = self.env['mrp.bom'].search(
                [('product_tmpl_id', '=', self.product_tmpl_id.id),
                 ('product_id', '=', False)], limit=1)
            if reference_bom:
                self.bom_ref_id = reference_bom.id
            else:
                self.bom_ref_id = False
        else:
            self.bom_ref_id = False


class MrpBomAttrMapping(models.Model):
    _name = 'mrp.bom.attr.mapping'
    _description = 'MRP BoM Attr Mapping'

    attr_mapping_id = fields.Many2one('mrp.bom.conf.line',
                                      string='Attr Mapping')
    config_prod_attr_id = fields.Many2one(
        'product.attribute', required=True,
        string='Configurable Product Attribute')
    manuf_prod_attr_ids = fields.Many2many(
        'product.attribute', 'mrp_bom_attr_mapping_rel',
        'col1', 'col2', required=True,
        string='Manufacturing Product Attribute')


class MrpBomAttrValueMapping(models.Model):
    _name = 'mrp.bom.attr.value.mapping'
    _description = 'MRP BoM Attr Value Mapping'

    value_mapping_id = fields.Many2one('mrp.bom.conf.line',
                                       string='Value Mapping')
    config_prod_attr_val_id = fields.Many2one(
        'product.attribute.value', required=True,
        string='Configurable Product Attribute Value')
    manuf_prod_attr_val_ids = fields.Many2many(
        'product.attribute.value', 'mrp_bom_attr_value_mapping_rel',
        'col1', 'col2', required=True,
        string='Manufacturing Product Attribute Value')
