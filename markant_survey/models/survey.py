from odoo import api, fields, models, _


class Survey(models.Model):
    _name = 'survey'
    _description = 'Markant Survey'

    # header fields
    name = fields.Char(string='Name', readonly=True, copy=False,
                       track_visibility='always',
                       default=lambda self: _('New'))
    creation_date = fields.Date(string='Creation Date',
                                default=lambda self: fields.date.today())
    so_number = fields.Char(string='AS400 SO Number')
    created_by = fields.Many2one('res.users', string='Created By',
                                 default=lambda self: self.env.user.id)

    # main info tab fields
    # dealer group
    dealer_partner_id = fields.Many2one('res.partner', string='Company')
    dealer_street = fields.Char()
    dealer_street2 = fields.Char()
    dealer_zip = fields.Char(change_default=True)
    dealer_city = fields.Char()
    dealer_state_id = fields.Many2one("res.country.state", string='State',
                                      ondelete='restrict')
    dealer_country_id = fields.Many2one('res.country', string='Country',
                                        ondelete='restrict')
    dealer_contact_person = fields.Many2one('res.partner',
                                            string='Contact person')
    dealer_email = fields.Char(string='Email')
    dealer_phone = fields.Char(string='Phone')

    # end user group
    end_user_partner_id = fields.Many2one('res.partner', string='Company')
    end_user_street = fields.Char()
    end_user_street2 = fields.Char()
    end_user_zip = fields.Char(change_default=True)
    end_user_city = fields.Char()
    end_user_state_id = fields.Many2one("res.country.state", string='State',
                                        ondelete='restrict')
    end_user_country_id = fields.Many2one('res.country', string='Country',
                                          ondelete='restrict')
    end_user_contact_person = fields.Many2one('res.partner', string='Contact person')
    end_user_email = fields.Char(string='Email')
    end_user_phone = fields.Char(string='Phone')
    google_map_url = fields.Char(string='Google Map URL')

    # planning group
    mechanic = fields.Char(string='Mechanic')
    google_drive = fields.Char(string='Google Drive')

    # survey of site tab fields
    # licenses group
    vca_certification = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                         string='VCA-certification')
    # vehicle / equipment group
    accessibility_transport = fields.Selection([('good', 'Good'),
                                                ('moderate', 'Moderate'),
                                                ('bad', 'Bad')],
                                               string='Accessibility')
    trailer = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                               string='Trailer')
    trailer_load_value = fields.Integer(string='Trailer Load Value (kg)')
    trailer_with_tailgate = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                             string='Trailer with Tailgate')
    small_truck = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                   string='Small Truck')
    truck = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                             string='Truck')
    coach = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                             string='Coach')
    # loading site survey group
    distance_place_unloading = fields.Integer(string='Distance to Place '
                                                     'of Unloading')
    distance_uom = fields.Many2one('uom.uom')
    distance_load_dock = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                          string='Load/ Unload Dock')
    photo_site = fields.Char(string='Photo\'s Site')
    photo_description = fields.Text(string='Photo Description')
    video = fields.Char(string='Video')
    obstacle = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                string='Obstacle')
    obstacle_description = fields.Text(string='Obstacle Description')
    # entry object information
    entry_object_length = fields.Integer(string='Entry Object (Length)')
    entry_object_with = fields.Integer(string='Entry Object (Width)')
    entry_object_height = fields.Integer(string='Entry Object (Height)')
    # time constraints
    tuning_loading_time_from = fields.Float(string='From')
    tuning_loading_time_to = fields.Float(string='To')
    available_working_hours = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                               string='Available Working'
                                                      ' Hours')
    available_working_hours_from = fields.Float(string='From')
    available_working_hours_to = fields.Float(string='To')
    difference_available_time = fields.Char(string='Difference Available Time',
                                            compute='_get_color')
    # buffer zone
    any_buffer_zone = fields.Selection(selection=[('yes', 'Yes'), ('no', 'No')],
                                       string='Any Buffer Zone')
    buffer_zone_length = fields.Integer(string='Buffer Zone (Length)')
    buffer_zone_width = fields.Integer(string='Buffer Zone (Width)')
    buffer_zone_height = fields.Integer(string='Buffer Zone (Height)')
    distance_buffer_zone = fields.Integer(string='Distance Buffer Zone to Site')
    distance_buffer_zone_uom = fields.Many2one('uom.uom')
    photo_buffer_zone = fields.Char(string='Photo\'s Buffer Zone')
    waste_buffer_zone = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                         string='Waste Disposal Area '
                                                'Buffer Zone')
    # lift condition group
    lift_available = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                      string='Lift Available')
    size_lift_length = fields.Float(string='Size of Lift (Length)')
    size_lift_length_uom = fields.Many2one('uom.uom')
    size_lift_depth = fields.Float(string='Size of Lift (Depth)')
    size_lift_depth_uom = fields.Many2one('uom.uom')
    size_lift_height = fields.Float(string='Size of Lift (Height)')
    size_lift_height_uom = fields.Many2one('uom.uom')
    lift_qty_lift = fields.Integer(string='Lift Qty')
    lift_load_capacity = fields.Integer(string='Lift Load Capacity (kg)')
    lift_load_capacity_uom = fields.Many2one('uom.uom')
    lift_opening_length = fields.Integer(string='Lift Opening (Length)')
    lift_opening_length_uom = fields.Many2one('uom.uom')
    lift_opening_height = fields.Integer(string='Lift Opening (Height)')
    lift_opening_height_uom = fields.Many2one('uom.uom')

    moving_lift_available = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                             string='Moving Lift Available')
    lift_qty_moving = fields.Integer(string='Lift Qty')
    size_moving_lift_length = fields.Integer(string='Size of Moving '
                                                    'Lift (Length)')
    size_moving_lift_length_uom = fields.Many2one('uom.uom')
    size_moving_lift_depth = fields.Integer(string='Size of Moving '
                                                   'Lift (Depth)')
    size_moving_lift_depth_uom = fields.Many2one('uom.uom')
    size_moving_lift_height = fields.Integer(string='Size of Moving '
                                                    'Lift (Height)')
    size_moving_lift_height_uom = fields.Many2one('uom.uom')

    moving_lift_load_capacity = fields.Integer(string='Moving Lift Load '
                                                      'Capacity (kg)')
    moving_lift_load_capacity_uom = fields.Many2one('uom.uom')
    moving_lift_opening_length = fields.Integer(string='Moving Lift '
                                                       'Opening (Length)')
    moving_lift_opening_length_uom = fields.Many2one('uom.uom')
    moving_lift_opening_height = fields.Integer(string='Moving Lift '
                                                       'Opening (Height)')
    moving_lift_opening_height_uom = fields.Many2one('uom.uom')

    lift_protection = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                       string='Lift Protection')
    staircase_available = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                           string='Staircase Available')
    type_staircase = fields.Binary(string='Type of Staircase')
    number_staircase = fields.Integer(string='Number of Staircase')
    # installation space survey
    installation_on_multiple = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                                string='Installation on '
                                                       'Multiple Floors')
    total_number_floors = fields.Integer(string='Total Number of Floors')
    number_floors = fields.Integer(string='Number Of Floor where work takes place')
    # necessary means of transport (internal use)
    dog = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Dog?')
    dog_qty = fields.Integer(string='Dog Qty')
    rolling_containers = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                          string='Rolling Containers')
    rolling_container_qty = fields.Integer(string='Rolling Container Qty')
    pickup_truck = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                    string='Pickup Truck')
    pickup_truck_qty = fields.Integer(string='Pickup Truck Qty')
    pump_truck = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                  string='Pump Truck')
    pump_truck_qty = fields.Integer(string='Pump Truck Qty')
    threshold_plate = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                       string='Threshold Plate')
    truck_qty = fields.Integer(string='Truck Qty')
    # protective device for housing
    stool = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Stool')
    stool_size = fields.Integer(string='Stool Size')
    stool_size_uom = fields.Many2one('uom.uom')
    carpenter_cover = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                       string='Carpenter Cover')
    carpenter_size = fields.Integer(string='Carpenter Size')
    carpenter_size_uom = fields.Many2one('uom.uom')
    board_plates = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                    string='Board Plates')
    board_plates_size = fields.Integer(string='Board Plates Size')
    board_plates_size_uom = fields.Many2one('uom.uom')
    blankets = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                string='Blankets')
    blankets_size = fields.Integer(string='Blankets Size')
    blankets_size_uom = fields.Many2one('uom.uom')
    # employee information
    number_mechanics = fields.Integer(string='Number of Mechanics')
    number_assistant = fields.Integer(string='Number of Assistant Mechanics')
    other_detail_info = fields.Text(string='Other Detail Information')
    # before installation project checklist tab fields
    project = fields.Char(string='Project')
    survey_planned_date = fields.Date(string='Survey Planned Date')
    survey_finished_date = fields.Date(string='Survey Form Finished Date')
    planning_production_order = fields.Date(string='Planning Production Order')
    delivery_date = fields.Date(string='Delivery Date')
    planned_transport_date = fields.Date(string='Planned Transport Date')
    carrier = fields.Many2one('carrier', string='Carrier')
    planned_installation_date = fields.Date(string='Planned Installation Date')
    contact_person = fields.Many2one('res.users', string='Contact Person Internal Sales')
    project_manager = fields.Char(string='Project Manager at Site')
    project_drawing_available = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Project Drawing Available')
    project_image_url = fields.Char(string='Project Image URL link')

    @api.onchange('dealer_partner_id')
    def onchange_dealer_partner_id(self):
        if self.dealer_partner_id:
            self.dealer_street = self.dealer_partner_id.street
            self.dealer_street2 = self.dealer_partner_id.street2
            self.dealer_zip = self.dealer_partner_id.zip
            self.dealer_city = self.dealer_partner_id.city
            self.dealer_state_id = self.dealer_partner_id.state_id
            self.dealer_country_id = self.dealer_partner_id.country_id
            self.dealer_email = self.dealer_partner_id.email
            self.dealer_phone = self.dealer_partner_id.phone

    @api.onchange('end_user_partner_id')
    def onchange_end_user_partner_id(self):
        if self.end_user_partner_id:
            self.end_user_street = self.end_user_partner_id.street
            self.end_user_street2 = self.end_user_partner_id.street2
            self.end_user_zip = self.end_user_partner_id.zip
            self.end_user_city = self.end_user_partner_id.city
            self.end_user_state_id = self.end_user_partner_id.state_id
            self.end_user_country_id = self.end_user_partner_id.country_id
            self.end_user_email = self.end_user_partner_id.email
            self.end_user_phone = self.end_user_partner_id.phone

    @api.depends('tuning_loading_time_from', 'available_working_hours_from',
                 'tuning_loading_time_to', 'available_working_hours_to')
    def _get_color(self):
        for survey in self:
            if survey.tuning_loading_time_from != \
                    survey.available_working_hours_from \
                    or survey.tuning_loading_time_to != \
                    survey.available_working_hours_to:
                survey.difference_available_time = '#FF0000'  # Red Color
            else:
                survey.difference_available_time = ''

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('seq.survey')
        return super(Survey, self).create(vals)
