# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP / Odoo, Open Source Management Solution - module extension
#    Copyright (C) 2014- Ursa Information Systems (<http://ursainfosystems.com>).
#    Author Graeme Gellatly
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


class AccountingReport(orm.TransientModel):
    _inherit = "accounting.report"

    _columns = {'adv_options': fields.boolean('Advanced Options')}

    def onchange_filter(self, cr, uid, ids, filter='filter_no', fiscalyear_id=False, context=None):
        res = super(AccountingReport, self).onchange_filter(cr, uid, ids, filter=filter, fiscalyear_id=fiscalyear_id, context=context)
        if context and context.get('as_of') and res['value'].get('date_from'):
            res['value']['date_from'] = '1970-01-01'
        return res

    def _build_comparison_context(self, cr, uid, ids, data, context=None):
        result = super(AccountingReport, self)._build_comparison_context(cr, uid, ids, data, context=context)
        if context and context.get('as_of') and result.get('date_from'):
            result['date_from'] = '1970-01-01'
        return result

    def onchange_chart_id(self, cr, uid, ids, chart_account_id=False, context=None):
        res = super(AccountingReport, self).onchange_chart_id(cr, uid, ids, chart_account_id=chart_account_id, context=context)
        if res and context and context.get('as_of') and res['value'].get('fiscalyear_id'):
            res['value']['fiscalyear_id'] = False
        return res
