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

from osv import fields,osv

REPORT_TYPE_OPTIONS = [
        ('none','/'),
        ('income','Profit & Loss (Operating Income Accounts)'),
        ('cogs', 'Profit & Loss (Cost of Goods Sold Accounts)'),
        ('expense','Profit & Loss (Operating Expense Accounts)'),
        ('other_income', 'Profit & Loss (Other Income Accounts)'),
        ('other_expense', 'Profit & Loss (Other Expense Accounts)'),
        ('depn_expense', 'Profit & Loss (Depreciation/Amortisation Accounts'),
        ('interest_expense', 'Profit & Loss (Interest Accounts)'),
        ('tax_expense', 'Profit & Loss (Taxation Accounts)'),
        ('asset','Balance Sheet (Asset Accounts)'),
        ('liability','Balance Sheet (Liability Accounts)'),
        ('equity', 'Balance Sheet (Equity Accounts)'),
        ]


class AccountAccountType(osv.Model):
    _inherit = 'account.account.type'
    
    _columns = {
        'report_type':fields.selection(
                        REPORT_TYPE_OPTIONS, 'P&L / BS Category', select=True,
                        readonly=False, required=True,
                        help="This field is used to generate legal reports: "
                        "profit and loss, balance sheet."
                        ),
    }
