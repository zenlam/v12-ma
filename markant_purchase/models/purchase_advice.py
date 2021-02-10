from odoo import api, fields, models, tools, _
from odoo.tools.sql import drop_view_if_exists


class PurchaseAdviceLog(models.Model):
    _name = "purchase.advice.log"
    _description = "Purchase Advice"
    _rec_name = 'date'

    date = fields.Datetime('Create Date')
    user_id = fields.Many2one('res.users', 'User')
    log_item_ids = fields.One2many('purchase.advice.log.item', 'purchase_log',
                                   'Items')


class PurchaseAdviceLogItem(models.Model):
    _name = "purchase.advice.log.item"
    _description = "Purchase Advice Log Item"

    purchase_log = fields.Many2one('purchase.advice.log', 'Purchase Log')
    origin = fields.Char('Origin')
    partner_id = fields.Many2one('res.partner', 'Vendor')
    po_id = fields.Many2one('purchase.order', 'Purchase Order')
    product_id = fields.Many2one('product.product', 'Product')
    qty = fields.Float('Qty')
    uom_id = fields.Many2one('uom.uom', 'Product UoM')


class PurchaseAdviceSqlView(models.Model):
    _name = "purchase.advice.sql.view"
    _description = "Purchase Advice SQL View"
    _auto = False

    def _get_minimal_qty(self):
        for rec in self:
            if rec.partner_id and rec.product_id:
                company_id = self.env['res.company']._company_default_get(
                    'procurement.group')
                suppliers = rec.product_id.seller_ids \
                    .filtered(lambda r: (not r.company_id or r.company_id ==
                                         company_id) and
                                        (not r.product_id or
                                         r.product_id == rec.product_id))
                if suppliers:
                    supplier = suppliers[0]
                    rec.moq = supplier.min_qty

    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint',
                                    'Orderpoint')
    warehouse_id = fields.Many2one(related='orderpoint_id.warehouse_id',
                                   string='Warehouse')
    location_id = fields.Many2one(related='orderpoint_id.location_id',
                                  string='Location')
    partner_id = fields.Many2one('res.partner', 'Creditor')
    user_id = fields.Many2one(
        related='partner_id.purchase_user_id',
        string='Purchaser')
    product_id = fields.Many2one('product.product', string='Product')
    product_uom = fields.Many2one(string='Product Unit of Measure',
                                  related='orderpoint_id.product_uom')
    default_code = fields.Char('Article')
    description = fields.Char('Description')
    product_attr_ids = fields.Many2many(
        related='product_id.attribute_value_ids', string='Attributes')
    eerstedatum = fields.Char('Date Necessary')
    vrd = fields.Float('Vrd')
    sales = fields.Float('Sls')
    res = fields.Float('Res')
    ink = fields.Float('Ink')
    backorder = fields.Float('Bo')
    ecvrd = fields.Float('Ec vrd')
    vrij = fields.Float('Vrij')
    min = fields.Float('Min')
    max = fields.Float('Max')
    pu = fields.Float('Pu')
    moq = fields.Float(compute='_get_minimal_qty',
                       string='MOQ')
    advies = fields.Float('Adv (Wrong)')
    hulp = fields.Float('Adv')

    @api.model_cr
    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            create or replace view purchase_advice_sql_view as (
                WITH RECURSIVE qty_on_hand AS (
                    SELECT
                        sq.product_id AS product_id,
                        SUM ( quantity ) AS qty_on_hand
                    FROM
                        stock_quant sq
                        JOIN stock_location sl ON sq.location_id = sl.ID
                    WHERE
                        sl.USAGE = 'internal'
                    GROUP BY
                        sq.product_id
                    ),
                    inbound AS ( SELECT product_id, SUM ( product_qty ) AS inbound_qty FROM stock_move WHERE location_dest_id = 15 AND STATE <> 'done' AND STATE <> 'cancel' GROUP BY product_id ),
                    reserved AS ( SELECT product_id, SUM ( reserved_quantity ) AS reserved_qty FROM stock_quant GROUP BY product_id ),
                    reordeing AS ( SELECT id, product_id, product_min_qty, product_max_qty, CASE WHEN qty_multiple = 0 THEN 1 ELSE qty_multiple END FROM stock_warehouse_orderpoint ),
                    stockmove AS ( SELECT product_id, SUM ( product_qty ) AS outb, min(date_expected) as firstdate FROM stock_move WHERE location_dest_id = 9 AND STATE <> 'cancel' AND STATE <> 'done' GROUP BY product_id ),
                    supplier AS ( SELECT product_id, price, NAME AS suppliername FROM product_supplierinfo ),
                    po_line_reserve AS ( SELECT product_id, SUM ( product_qty ) AS po_line_reserved_qty FROM stock_move_line WHERE stock_move_line.done_move = 'false' AND stock_move_line.location_dest_id = 7 GROUP BY product_id ) SELECT
                    row_number() over () as id,
                    product_product.ID AS product_id,
                    product_product.default_code,
                    product_template.NAME AS description,
                    case when firstdate is null then null else concat(date_part('day',   firstdate), '/', date_part('month',   firstdate),'/',date_part('year',   firstdate)) end   as eerstedatum,
                CASE
                    WHEN qty_on_hand IS NULL THEN
                    0 ELSE CAST ( qty_on_hand as double precision )
                END AS "vrd",
                CASE
                    WHEN reserved_qty IS NULL THEN
                    0 ELSE CAST ( reserved_qty as double precision )
                END
                --+
                 --CASE
                --
                -- WHEN po_line_reserved_qty IS NULL THEN
                -- 0 ELSE CAST ( po_line_reserved_qty as double precision )
                --END
                AS "res",
                CASE
                    WHEN inbound_qty IS NULL THEN
                    0 ELSE CAST ( inbound_qty as double precision )
                END AS "ink",
                CASE
                    WHEN product_min_qty IS NULL THEN
                    0 ELSE CAST ( product_min_qty as double precision )
                END AS "min",
                CASE
                    WHEN product_max_qty IS NULL THEN
                    0 ELSE CAST ( product_max_qty as double precision )
                END AS "max",
                CASE
                    WHEN qty_multiple IS NULL THEN
                    1 ELSE CAST ( qty_multiple as double precision )
                END AS "pu",
                CASE
                    WHEN outb IS NULL THEN
                    0 ELSE CAST ( outb as double precision )
                    END AS "sales",
                    CASE WHEN
                    CASE WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                    CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END  <= 0 THEN 0
                    ELSE
                    CASE WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                    CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END
                END AS "backorder",
                --
                -- berekening econimische voorraad
                --
                CASE WHEN qty_on_hand IS NULL THEN 0 ELSE CAST ( qty_on_hand as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END  -
                CASE WHEN
                CASE WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END  <= 0 THEN 0
                ELSE
                CASE WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END
                END  +
                CASE WHEN inbound_qty IS NULL THEN 0 ELSE CAST ( inbound_qty as double precision ) END
                AS ecvrd,
                --
                -- berekening vrije voorraad
                --
                CASE WHEN qty_on_hand IS NULL THEN 0 ELSE CAST ( qty_on_hand as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END  -
                CASE WHEN
                CASE WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END <= 0 THEN 0 ELSE
                CASE
                WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END
                END AS "vrij",
                CASE
                    WHEN string_agg ( product_attribute_value.NAME, ',' ) IS NULL THEN
                    '' ELSE string_agg ( product_attribute_value.NAME, ',' )
                END AS omschrijving,
                CASE
                    WHEN res_partner.NAME IS NULL THEN
                    '' ELSE res_partner.NAME
                END AS crediteur,
                --
                -- hulpkolom
                --
                CASE WHEN
                CASE WHEN qty_on_hand IS NULL THEN 0 ELSE CAST ( qty_on_hand as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN
                CASE WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN po_line_reserved_qty IS NULL THEN 0 ELSE CAST ( po_line_reserved_qty as double precision ) END <= 0 THEN 0
                ELSE
                CASE WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN po_line_reserved_qty IS NULL THEN 0 ELSE CAST ( po_line_reserved_qty as double precision ) END
                END  +
                CASE WHEN inbound_qty IS NULL THEN 0 ELSE CAST ( inbound_qty as double precision ) END < case WHEN product_min_qty IS NULL THEN
                0 ELSE CAST ( product_min_qty as double precision )
                END
                then
                ceil((
                case WHEN product_max_qty IS NULL THEN
                0 ELSE CAST ( product_max_qty as double precision )
                END *-1
                +
                CASE WHEN qty_on_hand IS NULL THEN 0 ELSE CAST ( qty_on_hand as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN po_line_reserved_qty IS NULL THEN 0 ELSE CAST ( po_line_reserved_qty as double precision ) END -
                CASE WHEN
                CASE WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN po_line_reserved_qty IS NULL THEN 0 ELSE CAST ( po_line_reserved_qty as double precision ) END <= 0 THEN 0
                ELSE
                CASE WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN po_line_reserved_qty IS NULL THEN 0 ELSE CAST ( po_line_reserved_qty as double precision ) END
                END  +
                CASE WHEN inbound_qty IS NULL THEN 0 ELSE CAST ( inbound_qty as double precision ) END  )*-1 / CASE WHEN qty_multiple IS NULL THEN 1.0 ELSE  qty_multiple  END)* CASE WHEN qty_multiple IS NULL THEN 1.0 ELSE  qty_multiple  END
                end
                AS hulp,
                --
                -- advies
                --
                case when product_max_qty = 0.000 then
                case when
                CEIL(
                 (CASE WHEN qty_on_hand IS NULL THEN 0.0 ELSE CAST ( qty_on_hand as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0.0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN po_line_reserved_qty IS NULL THEN 0.0 ELSE CAST ( po_line_reserved_qty as double precision ) END -
                CASE WHEN
                CASE WHEN outb IS NULL THEN 0.0 ELSE CAST ( outb as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0.0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN po_line_reserved_qty IS NULL THEN 0.0 ELSE CAST ( po_line_reserved_qty as double precision ) END <= 0 THEN 0.000
                ELSE
                CASE WHEN outb IS NULL THEN 0.0 ELSE CAST ( outb as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0.0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN po_line_reserved_qty IS NULL THEN 0.0 ELSE CAST ( po_line_reserved_qty as double precision ) END
                END  +
                CASE WHEN inbound_qty IS NULL THEN 0.0 ELSE CAST ( inbound_qty as double precision ) END )*-1 /
                CASE WHEN qty_multiple IS NULL THEN 1.0 ELSE  qty_multiple  END ) * CASE WHEN qty_multiple IS NULL THEN 1.0 ELSE  qty_multiple  END < 0 then 0 ELSE
                CEIL(
                 (CASE WHEN qty_on_hand IS NULL THEN 0.0 ELSE CAST ( qty_on_hand as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0.0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN po_line_reserved_qty IS NULL THEN 0.0 ELSE CAST ( po_line_reserved_qty as double precision ) END -
                CASE WHEN
                CASE WHEN outb IS NULL THEN 0.0 ELSE CAST ( outb as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0.0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN po_line_reserved_qty IS NULL THEN 0.0 ELSE CAST ( po_line_reserved_qty as double precision ) END <= 0 THEN 0.000
                ELSE
                CASE WHEN outb IS NULL THEN 0.0 ELSE CAST ( outb as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0.0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN po_line_reserved_qty IS NULL THEN 0.0 ELSE CAST ( po_line_reserved_qty as double precision ) END
                END  +
                CASE WHEN inbound_qty IS NULL THEN 0.0 ELSE CAST ( inbound_qty as double precision ) END )*-1 /
                CASE WHEN qty_multiple IS NULL THEN 1.0 ELSE  qty_multiple  END ) * CASE WHEN qty_multiple IS NULL THEN 1.0 ELSE  qty_multiple  END end
                ELSE
                case when
                product_min_qty - (CASE WHEN qty_on_hand IS NULL THEN 0 ELSE CAST ( qty_on_hand as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN po_line_reserved_qty IS NULL THEN 0 ELSE CAST ( po_line_reserved_qty as double precision ) END -
                CASE WHEN
                CASE WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN po_line_reserved_qty IS NULL THEN 0 ELSE CAST ( po_line_reserved_qty as double precision ) END <= 0 THEN 0.000
                ELSE
                CASE WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN po_line_reserved_qty IS NULL THEN 0 ELSE CAST ( po_line_reserved_qty as double precision ) END
                END  +
                CASE WHEN inbound_qty IS NULL THEN 0 ELSE CAST ( inbound_qty as double precision ) END ) < 0 then 0 else
                ceil(
                product_max_qty - (CASE WHEN qty_on_hand IS NULL THEN 0 ELSE CAST ( qty_on_hand as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN po_line_reserved_qty IS NULL THEN 0 ELSE CAST ( po_line_reserved_qty as double precision ) END -
                CASE WHEN
                CASE WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN po_line_reserved_qty IS NULL THEN 0 ELSE CAST ( po_line_reserved_qty as double precision ) END <= 0 THEN 0.000
                ELSE
                CASE WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                CASE WHEN po_line_reserved_qty IS NULL THEN 0 ELSE CAST ( po_line_reserved_qty as double precision ) END
                END  +
                CASE WHEN inbound_qty IS NULL THEN 0 ELSE CAST ( inbound_qty as double precision ) END ) /
                CASE WHEN qty_multiple IS NULL THEN 1.0 ELSE  qty_multiple  END ) * CASE WHEN qty_multiple IS NULL THEN 1.0 ELSE  qty_multiple  END
                end
                END
                as advies,
                reo.id as orderpoint_id,
                res_partner.id as partner_id
                FROM
                    product_product
                    LEFT JOIN qty_on_hand qoh ON product_product.ID = qoh.product_id
                    LEFT JOIN reserved res ON product_product.ID = res.product_id
                    LEFT JOIN inbound ink ON product_product.ID = ink.product_id
                    LEFT JOIN reordeing reo ON product_product.ID = reo.product_id
                    LEFT JOIN supplier sup ON product_product.ID = sup.product_id
                    LEFT JOIN product_attribute_value_product_product_rel ON product_product.ID = product_attribute_value_product_product_rel.product_product_id
                    INNER JOIN product_template ON product_product.product_tmpl_id = product_template.
                    ID LEFT JOIN product_attribute_value ON product_attribute_value_product_product_rel.product_attribute_value_id = product_attribute_value.
                    ID LEFT JOIN stockmove smv ON product_product.ID = smv.product_id
                    LEFT JOIN po_line_reserve prod ON product_product.ID = prod.product_id
                    LEFT JOIN res_partner ON sup.suppliername = res_partner.ID
                WHERE
                    product_template.purchase_ok = TRUE
                    AND product_product.active = TRUE
                    AND
                    CASE WHEN
                    CASE WHEN qty_on_hand IS NULL THEN 0 ELSE CAST ( qty_on_hand as double precision ) END -
                    CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                    CASE WHEN po_line_reserved_qty IS NULL THEN 0 ELSE CAST ( po_line_reserved_qty as double precision ) END -
                    CASE WHEN
                    CASE WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                    CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                    CASE WHEN po_line_reserved_qty IS NULL THEN 0 ELSE CAST ( po_line_reserved_qty as double precision ) END <= 0 THEN 0
                    ELSE
                    CASE WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                    CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                    CASE WHEN po_line_reserved_qty IS NULL THEN 0 ELSE CAST ( po_line_reserved_qty as double precision ) END
                    END  +
                    CASE WHEN inbound_qty IS NULL THEN 0 ELSE CAST ( inbound_qty as double precision ) END < case WHEN product_min_qty IS NULL THEN
                    0 ELSE CAST ( product_min_qty as double precision )
                    END
                    then
                    ceil((
                    case WHEN product_max_qty IS NULL THEN
                    0 ELSE CAST ( product_max_qty as double precision )
                    END *-1
                    +
                    CASE WHEN qty_on_hand IS NULL THEN 0 ELSE CAST ( qty_on_hand as double precision ) END -
                    CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                    CASE WHEN po_line_reserved_qty IS NULL THEN 0 ELSE CAST ( po_line_reserved_qty as double precision ) END -
                    CASE WHEN
                    CASE WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                    CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                    CASE WHEN po_line_reserved_qty IS NULL THEN 0 ELSE CAST ( po_line_reserved_qty as double precision ) END <= 0 THEN 0
                    ELSE
                    CASE WHEN outb IS NULL THEN 0 ELSE CAST ( outb as double precision ) END -
                    CASE WHEN reserved_qty IS NULL THEN 0 ELSE CAST ( reserved_qty as double precision ) END -
                    CASE WHEN po_line_reserved_qty IS NULL THEN 0 ELSE CAST ( po_line_reserved_qty as double precision ) END
                    END  +
                    CASE WHEN inbound_qty IS NULL THEN 0 ELSE CAST ( inbound_qty as double precision ) END  )*-1 / CASE WHEN qty_multiple IS NULL THEN 1.0 ELSE  qty_multiple  END)* CASE WHEN qty_multiple IS NULL THEN 1.0 ELSE  qty_multiple  END
                    end <> 0
                GROUP BY
                    suppliername,
                    product_product.ID,
                    product_product.default_code,
                    product_template.NAME,
                    qty_on_hand,
                    reserved_qty,
                    inbound_qty,
                    product_min_qty,
                    product_max_qty,
                    qty_multiple,
                    product_attribute_value_product_product_rel.product_product_id,
                    outb,
                    po_line_reserved_qty,
                    res_partner.NAME ,
                    firstdate,
                    reo.id,
                    res_partner.id
                ORDER BY
                    Suppliername,product_product.default_code ASC
            )
        """)

    @api.multi
    def action_create_po_from_advice(self):
        log_items = []
        for rec in self:
            values = rec.orderpoint_id._prepare_procurement_values(rec.hulp)
            item = self.env['stock.rule']._run_buy_advice(
                rec.product_id, rec.hulp,
                rec.product_uom, rec.location_id,
                rec.orderpoint_id.name, rec.orderpoint_id.name,
                values)
            log_items.append(item)
        if log_items:
            advice_log = self.env['purchase.advice.log'].create({
                'date': fields.Datetime.now(),
                'user_id': self.env.user.id,
                'log_item_ids': log_items
            })
            # Confirm All Purchase Order
            for item in advice_log.log_item_ids:
                if item.po_id.state == 'draft':
                    item.po_id.button_confirm()
