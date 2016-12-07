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

from datetime import datetime
from dateutil import tz

from openerp.osv import orm, fields
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class StockMove(orm.Model):
    _inherit = 'stock.move'

    def _create_account_move_line(self, cr, uid, move, src_account_id,
                                  dest_account_id, reference_amount,
                                  reference_currency_id, context=None):
        def _convert_date(from_date):
            from_zone = tz.tzutc()
            to_zone = tz.gettz(context.get('tz'))
            utc = datetime.strptime(from_date, DEFAULT_SERVER_DATETIME_FORMAT)
            utc = utc.replace(tzinfo=from_zone)
            to_date = utc.astimezone(to_zone)
            to_date = to_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            return to_date[:10]

        if context is None:
            context = {}
        res = super(StockMove, self)._create_account_move_line(
            cr, uid, move,
            src_account_id, dest_account_id, reference_amount,
            reference_currency_id, context=context
        )
        for o2m_tuple in res:
            date = False
            if move.date_backdating:
                date = _convert_date(move.date_backdating)
            elif move.date:
                date = _convert_date(move.date)
            o2m_tuple[2]['date'] = date
            context['move_date'] = date
        return res

    def action_done(self, cr, uid, ids, context=None):
        # look at previous state and find date_backdating
        moves = []
        for move in self.browse(cr, uid, ids, context=context):
            # if not already in done and date is given
            if (move.state != 'done') and (not move.date_backdating):
                moves.append(move.id)
        if moves:
            self.write(cr, uid, moves, {'date': fields.datetime.now()},
                       context=context)
        # do actual processing
        result = super(StockMove, self).action_done(cr, uid, ids, context)
        # overwrite date field where applicable

        return result
