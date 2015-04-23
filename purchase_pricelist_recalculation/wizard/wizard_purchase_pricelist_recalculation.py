# -*- coding: utf-8 -*-
# #############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2011- O4SB (<http://www.openforsmallbusiness.co.nz>)
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
"""Wizard to recalculate all PO Line Prices after changing pricelist"""
from openerp.osv import orm, fields
from openerp.tools.translate import _


class PurchaseExtendedWizard(orm.TransientModel):
    """Purchase Pricelist Recalculation"""
    _name = "purchase.extended.wizard"
    _description = __doc__
    _columns = {
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist',
                                        required=True, domain=[('type', '=', 'purchase')])
    }

    def change_pricelist_products(self, cr, uid, ids, context):
        """Iterates over order lines and calculates the price based on
        the new pricelist"""
        obj_curr = self.browse(cr, uid, ids, context)[0]
        order_line_obj = self.pool.get('purchase.order.line')
        po_obj_pool = self.pool.get('purchase.order')
        pricelist_id = obj_curr['pricelist_id']
        po_obj = po_obj_pool.browse(cr, uid, context['active_id'], context)
        partner_id = po_obj.partner_id.id
        date_order = po_obj.date_order

        if po_obj.pricelist_id.id == pricelist_id.id:
            raise orm.except_orm(_('Warning'),
                                 _('The Pricelist is already applied to the purchase order!'))

        if po_obj['state'] == 'draft':
            po_obj_pool.write(cr, uid, context['active_id'], {'pricelist_id': pricelist_id.id})
            for line in po_obj.order_line:
                vals = order_line_obj.product_id_change(
                    cr, uid, line.id, pricelist_id.id, line.product_id.id,
                    qty=line.product_qty, uom_id=line.product_uom.id,
                    partner_id=partner_id, date_order=date_order
                )
                if vals.get('value', False):
                    if 'price_unit' in vals['value'].keys():
                        order_line_obj.write(cr, uid, line.id,
                                             {'price_unit': vals['value']['price_unit']},
                                             context=context)
        else:
            raise orm.except_orm(_('Warning'),
                                 _('PriceList cannot be changed! '
                                   'Make sure the Purchase Order is in "Quotation" state!'))
        return {}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: