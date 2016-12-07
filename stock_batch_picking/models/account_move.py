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

from openerp.osv import orm


class AccountMove(orm.Model):
    _inherit = "account.move"

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        period_obj = self.pool.get('account.period')
        if not context.get('move_date') and 'line_id' in vals:
            dates = [v['date'] for _, _, v in vals['line_id'] if 'date' in v]
            if dates:
                date = dates[0]
                period_ids = period_obj.find(
                    cr, uid, dt=date, context=context)
                if period_ids:
                    vals['period_id'] = period_ids[0]
                    vals['date'] = date
        return super(AccountMove, self).create(cr, uid, vals, context=context)
