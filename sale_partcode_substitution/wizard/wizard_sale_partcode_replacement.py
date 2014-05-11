# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution - module extension
#    Copyright (C) 2014- O4SB (<http://o4sb.com>).
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
from openerp.tools.translate import _


class SaleCodeReplacement(orm.TransientModel):
    _name = "sale.code.replacement"
    _description = "Sale Partcode Substitution Wizard"

    _columns = {
        'from_code': fields.char('From', size=32, required=True),
        'to_code': fields.char('To', size=32, required=True),
    }

    _defaults = {
        'from_code': '???',
        'to_code': '???',
    }

    def change_products_partcode(self, cr, uid, ids, context=None):

        order_line_pool = self.pool['sale.order.line']
        prod_pool = self.pool['product.product']

        sale_obj = self.pool['sale.order'].browse(cr, uid, context['active_id'],
                                                  context=context)

        obj_curr = self.browse(cr, uid, ids, context)[0]
        from_code = obj_curr.from_code
        to_code = obj_curr.to_code

        pricelist_id = sale_obj.pricelist_id.id
        partner_id = sale_obj.partner_id.id
        date_order = sale_obj.date_order

        if sale_obj['state'] == 'draft':
            context.update({'shop': sale_obj.shop_id.id})
            for line in sale_obj.order_line:
                if line.product_id:
                    old_part = line.product_id.default_code
                    if old_part.find(from_code) != -1:
                        new_part = old_part.replace(from_code, to_code)
                        new_part_id = prod_pool.search(
                            cr, uid,
                            [('default_code', '=', new_part)]
                        )
                        if new_part_id:
                            new_part_id = new_part_id[0]
                            line.write({'product_id': new_part_id})
                            vals = order_line_pool.product_id_change(
                                cr, uid, line.id,
                                pricelist_id, new_part_id,
                                qty=line.product_uom_qty,
                                uom=line.product_uom.id,
                                uos=line.product_uos.id,
                                partner_id=partner_id,
                                date_order=date_order,
                                update_tax=True,
                                context=context)
                            if vals.get('value', False):
                                taxes = vals['value'].get('tax_id', False)
                                if taxes:
                                    vals['value'].update(
                                        {'tax_id': [(6, 0, taxes)]}
                                    )
                                line.write(vals['value'])
        else:
            raise orm.except_orm(_('Warning'),
                                 _('Partcodes cannot be changed! Make sure '
                                   'the Sales Order '
                                   'is in "Quotation" state!'))
        return {}

#  vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
