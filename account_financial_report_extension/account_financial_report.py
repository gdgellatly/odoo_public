# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP / Odoo, Open Source Management Solution - module extension
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
import openerp.addons.account.report.account_financial_report as parent

import hashlib
import inspect
import logging

_logger = logging.getLogger(__name__)

# VALID_HASHES = [
#     '123',
#     ]
#
# h = hashlib.sha224(inspect.getsourcelines(''.join(
#     parent.report_account_common.get_lines)[0])).hexdigest()
# if h not in VALID_HASHES:
#     _logger.critical('Parent Function get_lines has changed or not '
#                      'known to be compatible with this version. Got: %s, Expected 123' % h)


class AccountFinancialReport(orm.Model):
    _inherit = "account.financial.report"

    def _get_children_by_order(self, cr, uid, ids, context=None):
        """returns a dictionary with the key= the ID of a record and
        value = all its children, computed recursively, and sorted by
        sequence. Ready for the printing"""
        res = []
        for pk in self.browse(cr, uid, ids, context=context):
            if pk.position != 'bottom':
                res.append(pk.id)
            ids2 = self.search(cr, uid, [('parent_id', '=', pk.id)],
                               order='sequence ASC', context=context)
            res += self._get_children_by_order(cr, uid, ids2, context=context)
            if pk.position == 'bottom':
                res.append(pk.id)
        return res

    _columns = {
        'position': fields.selection(
            [('top', 'Heading and Value Before Children'),
             ('bottom', 'Heading and Value After Children'),
             ('mixed', 'Heading Before Children, Total After'),
             ('none', 'Do not display Total')],
            string='Display Position', required=True)
    }

    _defaults = {'position': 'top'}


def _get_detail_lines(self, cr, uid, data, report):
    account_obj = self.pool['account.account']
    currency_obj = self.pool['res.currency']
    account_ids = []
    lines = []
    if report.type == 'accounts' and report.account_ids:
        account_ids = account_obj._get_children_and_consol(cr, uid, [x.id for x in report.account_ids])
    elif report.type == 'account_type' and report.account_type_ids:
        account_ids = account_obj.search(cr, uid, [('user_type','in', [x.id for x in report.account_type_ids])])
    if account_ids:
        for account in account_obj.browse(cr, uid, account_ids, context=data['form']['used_context']):
        #if there are accounts to display, we add them to the lines with a level equals to their level in
        #the COA + 1 (to avoid having them with a too low level that would conflicts with the level of data
        #financial reports for Assets, liabilities...)
            if report.display_detail == 'detail_flat' and account.type == 'view':
                continue
            flag = False
            detail_vals = {
                'name': account.code + ' ' + account.name,
                'balance': (account.balance != 0.0 and
                            account.balance * report.sign or
                            account.balance),
                'type': 'account',
                'level': (report.display_detail == 'detail_with_hierarchy' and
                          min(account.level + 1, 6) or 6),
                'account_type': account.type,
                }

            if data['form']['debit_credit']:
                detail_vals['debit'] = account.debit
                detail_vals['credit'] = account.credit
            if not currency_obj.is_zero(
                    cr, uid, account.company_id.currency_id,
                    detail_vals['balance']):
                flag = True
            if data['form']['enable_filter']:
                detail_vals['balance_cmp'] = account_obj.browse(
                    cr, uid, account.id,
                    context=data['form']['comparison_context']).balance * report.sign or 0.0
                if not currency_obj.is_zero(
                        cr, uid, account.company_id.currency_id,
                        detail_vals['balance_cmp']):
                    flag = True
            if flag:
                lines.append(detail_vals)
    return lines


def get_lines(self, data):
    cr, uid = self.cr, self.uid
    lines = []
    ids2 = self.pool['account.financial.report']._get_children_by_order(cr, uid, [data['form']['account_report_id'][0]], context=data['form']['used_context'])
    for report in self.pool['account.financial.report'].browse(cr, uid, ids2, context=data['form']['used_context']):
        vals = {
            'name': report.name,
            'balance': report.balance * report.sign or 0.0,
            'type': 'report',
            'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
            'account_type': report.type =='sum' and 'view' or False, #used to underline the financial report balances
        }
        if data['form']['debit_credit']:
            vals['debit'] = report.debit
            vals['credit'] = report.credit
        if data['form']['enable_filter']:
            vals['balance_cmp'] = self.pool['account.financial.report'].browse(cr, uid, report.id, context=data['form']['comparison_context']).balance * report.sign or 0.0
        if report.position == 'top':
            lines.append(vals)
        elif report.position == 'mixed':
            lines.append(dict(vals, **{'balance': '', 'debit': '',
                                       'credit': '', 'balance_cmp': ''}))

        if report.display_detail != 'no_detail':
            lines.extend(self._get_detail_lines(cr, uid, data, report))

        if report.position == 'mixed':
            lines.append(dict(vals, **{'name': ''}))
        elif report.position == 'bottom':
            lines.append(vals)
    return lines

parent.report_account_common.get_lines = get_lines
parent.report_account_common._get_detail_lines = _get_detail_lines
