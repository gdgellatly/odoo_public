# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP / Odoo, Open Source Management Solution - module extension
#    Copyright (C) 2014- O4SB (<http://openforsmallbusiness.co.nz>).
#    Author Graeme Gellatly <g@o4sb.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import orm, fields


class ProductSupplierinfo(orm.Model):
    """Product Supplierinfo"""
    _inherit = 'product.supplierinfo'

    def _compute_unit_price(self, cr, uid, ids, fields, arg, context=None):
        if context is None:
            context = {}
        dim_values = None
        result = {}

        if (context.get('parent_model','') == 'product.product'
            and 'parent_model_id' in context):
            pvdv_obj = self.pool['product.variant.dimension.value']
            dim_values = pvdv_obj.search(
                cr, uid, [('product_ids', 'in', [context['parent_model_id']])])

        for supplier in self.browse(cr, uid, ids, context=context):
            res = []
            for price in supplier.pricelist_ids:
                key = price.min_quantity
                if (price.price * 100) % 1:
                    text = "$%.5f" % price.price
                else:
                    text = "$%.2f" % price.price
                if key > 0.0:
                    text += " Qty:>%d" % (int(key))
                if price.required_value_ids:
                    if dim_values is not None and not all([x.id in dim_values for x in price.required_value_ids]):
                        continue
                    text += ' Req:' + ','.join(
                        [x.option_id.name for x in price.required_value_ids])
                if price.excluded_value_ids:
                    if dim_values is not None and any([x.id in dim_values for x in price.excluded_value_ids]):
                        continue
                    text += ' Exc:' + ','.join(
                        [x.option_id.name for x in price.excluded_value_ids])
                res.append((key, text))
            res.sort()
            result[supplier.id] = '\n'.join([x[1] for x in res])
        return result

    _columns = {
        'prices': fields.function(
            _compute_unit_price, string="Prices", type="text"),
        'default': fields.boolean(string='Default Price'),
        'warehouse_ids': fields.many2many('stock.warehouse',
            string='Warehouses')
    }

    def _get_product_id(self, cr, uid, context=None):
        if context and 'parent_model' in context:
            obj = self.pool[context['parent_model']].browse(cr, uid, context['parent_model_id'])
            if context['parent_model'] == 'product.product':
                return obj.product_tmpl_id.id
            else:
                return obj.id
        return False

    _defaults = {'default': False,
                 'product_id': _get_product_id}

    def get_suppliers(self, cr, uid, tmpl_id, partner):
        where = []
        if partner:
            where = [('name', '=', partner)]
        sinfo = self.search(cr, uid, [('product_id', '=', tmpl_id),
                                      ('pricelist_ids', '!=', False)] + where)
        if not sinfo and partner:
            p = self.pool['res.partner'].browse(cr, uid, partner)
            if p.commercial_partner_id:
                sinfo = self.search(cr, uid,
                                    [('product_id', '=', tmpl_id),
                                     ('name', '=', p.commercial_partner_id.id),
                                     ('pricelist_ids', '!=', False)])
        if not sinfo:
            sinfo = self.search(cr, uid, [('product_id', '=', tmpl_id),
                                          ('default', '=', True)])
        if not sinfo:
            sinfo = self.search(cr, uid, [('product_id', '=', tmpl_id)])
        return sinfo

    def price_query(self, cr, uid, ids, quantity, product_id):
        price_info_obj = self.pool['pricelist.partnerinfo']
        pvdv_obj = self.pool['product.variant.dimension.value']
        # If a dimension_value is present in include the product must have that
        # If a dimension_value is present in exclude the product must not have it
        dim_values = pvdv_obj.search(cr, uid, [('product_ids', 'in', [product_id])])
        for pk in ids:
            price_records = price_info_obj.search(
                cr, uid,[('min_quantity', '<=', quantity),
                         ('suppinfo_id', '=', pk)],
                order='min_quantity desc')
            for price_record in price_info_obj.browse(cr, uid, price_records):
                if not all([v.id in dim_values for v
                            in price_record.required_value_ids]):
                    continue
                if any([v.id in dim_values for v
                        in price_record.excluded_value_ids]):
                    continue
                return price_record.price
        return 0.00


class PricelistPartnerinfo(orm.Model):
    """Pricelist Partnerinfo"""
    _inherit = 'pricelist.partnerinfo'

    _columns = {
        'required_value_ids': fields.many2many(
            'product.variant.dimension.value',
            rel='partner_info_dim_value_include',
            id1='partner_info_id', id2='value_id',
             string="Must Have"),
        'excluded_value_ids': fields.many2many(
            'product.variant.dimension.value',
            id1='partner_info_id', id2='value_id',
            rel='partner_info_dim_value_exclude',
            string="Exclude"),

    }


class ProductVariantDimensionValue(orm.Model):
    _inherit = 'product.variant.dimension.value'

    _columns = {
        'required_partnerinfo_ids': fields.many2many(
            'pricelist.partnerinfo',
            rel='partner_info_dim_value_include',
            id1='value_id', id2='partner_info_id',
            string="Apply only to:"),
        'excluded_partnerinfo_ids': fields.many2many(
            'pricelist.partnerinfo',
            rel='partner_info_dim_value_exclude',
            id1='value_id', id2='partner_info_id',
            string="Don't apply to:")
    }

class StockWarehouse(orm.Model):
    _inherit = 'stock.warehouse'

    _columns = {'pricelist_ids': fields.many2many(
        'product.supplierinfo', string='Product Price Records')}
