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
"""Wizard to recalculate all Invoice Line Prices"""
from openerp.osv import orm, fields
from openerp.tools.translate import _


class InvoiceRepriceWizard(orm.TransientModel):
    """Invoice Pricelist Recalculation"""
    _name = "invoice.reprice.wizard"
    _description = __doc__
    _columns = {
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist'),
        'check_qty_breaks': fields.boolean('Check Qty Breaks (slower)')
    }

    def change_pricelist_products(self, cr, uid, ids, context):
        """Iterates over invoices lines and calculates the price based on
        the new pricelist"""
        wiz = self.browse(cr, uid, ids, context)[0]
        inv_pool = self.pool['account.invoice']

        pricelist_id = wiz.pricelist_id.id
        invoices = inv_pool.browse(cr, uid, context['active_ids'], context)
        partner_id = invoices[0].partner_id.id

        if pricelist_id and inv_pool.search(
                cr, uid,
                [('id', 'in', context['active_ids']),
                 ('partner_id', '!=', partner_id)]):
            raise orm.except_orm(
                _('Warning'),
                _('For your own safety this function only works'
                  ' with invoices from a single supplier when'
                  ' a pricelist is selected!'))
        if inv_pool.search(cr, uid, [('id', 'in', context['active_ids']),
                                     ('state', '!=', 'draft')]):
            raise orm.except_orm(
                _('Warning'),
                _('Pricing cannot be changed! '
                  'Make sure all invoices are in Draft state!'))
        if pricelist_id:
            part_plist = {partner_id: pricelist_id}
        else:
            partner_ids = list(set([x.partner_id.id for x in invoices]))
            part_plist = {
                x.id: x.property_product_pricelist_purchase.id for x in
                self.pool['res.partner'].browse(cr, uid, partner_ids)
                }
        calls_to_make = {}
        for inv in invoices:
            pricelist_id = part_plist.get(inv.partner_id.id)
            if pricelist_id not in calls_to_make:
                calls_to_make[pricelist_id] = []
            calls_to_make[pricelist_id].extend(
                [(x.product_id.id, wiz.check_qty_breaks and
                  x.quantity or 1, False) for x in inv.invoice_line if
                 x.product_id])

        prices = {}
        price_func = self.pool['product.pricelist'].price_get_multi
        for part_plist, args in calls_to_make.items():
            args = list(set(args))
            prices.update(price_func(cr, uid, [part_plist], args))
        [line.write({
            'price_unit':
                line.product_id and
                prices[line.product_id.id][part_plist[inv.partner_id.id]] or
                line.price_unit})
         for inv in invoices for line in inv.invoice_line]

        inv_pool.button_compute(cr, uid, context['active_ids'])
        return {}
