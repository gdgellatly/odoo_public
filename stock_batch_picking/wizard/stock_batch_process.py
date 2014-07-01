# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 Akretion LTDA.
#    authors: Raphaël Valyi
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

from openerp.osv import fields, orm


class StockBatchProcess(orm.TransientModel):
    _name = "stock.batch.process"
    _description = "Stock Batch Process"

    _columns = {
        'force_availability': fields.boolean('Force availability if not available?',
                                             help='That will lead to abnormal negative stock values'),
    }

    def _check_tracking(self, cr, uid, move):
        """ Checks if production lot is assigned to stock move or not.
        @return: True or False
        """
        if not move.prodlot_id and (
                move.product_id.track_outgoing or move.product_id.track_incoming or move.product_id.track_production):
            return True
        return False

    def process(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        picking_pool = self.pool['stock.picking']
        active_ids = context.get('active_ids', [])
        active_pickings = picking_pool.browse(cr, uid, active_ids, context=context)
        to_remove_ids = []
        for picking in active_pickings:
            to_remove_ids.extend(
                [move.picking_id.id for move in picking.move_lines if self._check_tracking(cr, uid, move)])
        active_ids = list(set(active_ids).difference(set(to_remove_ids)))
        picking_pool.action_move(cr, uid, active_ids, context)
        return {}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
