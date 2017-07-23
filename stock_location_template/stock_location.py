# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
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

from openerp.osv import fields,osv


class stock_location_path(osv.osv):
    __inherit = "stock.location.path"

    _columns = {
        'product_tmpl_id' : fields.many2one(
            'product.template', 'Product Templates',
             ondelete='cascade', select=1)
    }


class product_pulled_flow(osv.osv):
    _inherit = 'product.pulled.flow'
    _columns = {
        'product_tmpl_id': fields.many2one('product.template', 'Product Templates'),
    }


class product_template(osv.osv):
    _inherit = 'product.template'
    _columns = {
        'tmpl_flow_pull_ids': fields.one2many('product.pulled.flow', 'product_tmpl_id', 'Pulled Flows'),
        'tmpl_path_ids': fields.one2many('stock.location.path', 'product_tmpl_id',
            'Pushed Flow',
            help="These rules set the right path of the product in the "\
            "whole location tree.")
    }


class stock_location(osv.osv):
    _inherit = 'stock.location'
    def chained_location_get(self, cr, uid, location, partner=None, product=None, context=None):
        if product and not product.path_ids:
            for path in product.path_ids:
                if path.location_from_id.id == location.id:
                    return path.location_dest_id, path.auto, path.delay, path.journal_id and path.journal_id.id or False, path.company_id and path.company_id.id or False, path.picking_type, path.invoice_state
        return super(stock_location, self).chained_location_get(cr, uid, location, partner, product, context)
stock_location()

