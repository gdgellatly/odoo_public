# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution - module extension
#    Copyright (C) 2010- O4SB (<http://openforsmallbusiness.co.nz>).
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
# noinspection PyUnresolvedReferences
from openerp.addons.decimal_precision import decimal_precision as dp


class ProductProduct(orm.Model):
    _inherit = 'product.product'

    _columns = {
        'standard_price': fields.property(
            'product.product', type='float', digits_compute=dp.get_precision('Product Price'),
            string='Standard Price', method=True, view_load=True, required=True, readonly=True,
            help="Product's cost for accounting stock valuation. "
                 "It is the base price for the supplier price."),
    }


class StockMove(orm.Model):
    _inherit = 'stock.move'
    _order = 'date desc'

    def _get_reference_accounting_values_for_valuation(self, cr, uid, move,
                                                       context=None):
        """
        Return the reference amount and reference currency
        representing the inventory valuation for this move.
        These reference values should possibly be converted
        before being posted in Journals to adapt to the primary
        and secondary currencies of the relevant accounts.
        """

        if move.product_id.cost_method == 'standard' or (
                        move.location_id.usage != 'production' and
                        move.product_id.cost_method == 'average'):
            # If we don't need to calculate a manufacturing cost
            return super(StockMove, self)._get_reference_accounting_values_for_valuation(cr, uid, move, context=context)

        move_obj = self.pool['stock.move']
        reference_currency_id = (move.price_currency_id and
                                 move.price_currency_id.id or
                                 move.company_id.currency_id.id)
        reference_amount = None
        product_obj = self.pool['product.product']
        uom_obj = self.pool['product.uom']

        if (move.location_id.usage == 'production' and
                    move.product_id.cost_method == 'average'):
            if move.location_id.usage == 'internal':
                #  Sending to production or other internal moves
                move_ids = move_obj.search(
                    cr, uid,
                    [('product_id', '=', move.product_id.id),
                     ('prodlot_id', '=', move.prodlot_id.id),
                     ('location_dest_id.usage', '=', 'internal')]
                )
                if move_ids:
                    prior_move = move_obj.browse(cr, uid, move_ids[0],
                                                 context)
                    amount_unit = uom_obj._compute_price(
                        cr, uid, move.product_uom.id,
                        prior_move.price_unit,
                        to_uom_id=move.product_id.uom_id.id)
                else:
                    amount_unit = move.product_id.standard_price
                move.write({'price_unit': amount_unit})
                reference_amount = amount_unit * move.product_qty

            if move.location_id.usage == 'production':  # Manufacturing output
                digits = self.pool['decimal.precision'].precision_get(
                    cr, uid, 'Product Price'
                )
                parent_move_ids = move_obj.search(
                    cr, uid,
                    [('move_dest_id', '=', move.id)]
                )
                reference_amount = 0.0
                for parent_move in move_obj.browse(cr, uid, parent_move_ids,
                                                   context=context):
                    if parent_move.price_unit:
                        reference_amount += (parent_move.price_unit *
                                             parent_move.product_qty)
                    else:
                        amount = uom_obj._compute_price(
                            cr, uid, move.product_id.uom_id.id,
                            parent_move.product_id.standard_price,
                            to_uom_id=move.product_uom.id
                        )
                        reference_amount += amount * parent_move.product_qty

                amount_unit = round(reference_amount / move.product_qty,
                                    digits)
                move.write({'price_unit': amount_unit})
                new_price = uom_obj._compute_price(
                    cr, uid, move.product_uom.id, amount_unit,
                    to_uom_id=move.product_id.uom_id.id
                )

                if move.product_id.cost_method == 'average':
                    # Update average costs
                    product = product_obj.browse(cr, uid, move.product_id.id)
                    context['currency_id'] = reference_currency_id
                    qty = uom_obj._compute_qty(cr, uid, move.product_uom.id,
                                               move.product_qty,
                                               product.uom_id.id)
                    product_avail = product.qty_available

                    if qty > 0.0:
                        if product.qty_available <= 0.0:
                            new_std_price = new_price
                        else:
                            # Get the standard price
                            amount_unit = product.price_get(
                                'standard_price',
                                context=context)[product.id]
                            new_std_price = (((amount_unit * product_avail)
                                              + (new_price * qty)) / (product_avail + qty))
                        # Write the field according to price type field
                        product.write({'standard_price': new_std_price})

            if move.location_id.usage in ['supplier', 'inventory']:
                # Receiving
                reference_amount = move.price_unit * move.product_qty
        if reference_amount:
            return reference_amount, reference_currency_id
        else:
            return super(StockMove, self)._get_reference_accounting_values_for_valuation(cr, uid, move, context=context)
