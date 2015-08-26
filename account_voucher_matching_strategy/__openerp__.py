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
{
    'name': 'Account Voucher Matching Strategy',
    'version': '0.1',
    'category': 'Accounting',
    'author': 'Graeme Gellatly - O4SB',
    'website': 'http://www.openforsmallbusiness.co.nz',
    'depends': ['base', 'account_voucher', 'account_voucher_no_auto_lines'],
    "description": """
    This module provides for advanced matching strategies to quickly reconcile payments
    with their remittances.

    Strategies included are:
    - Off the back
    - Selected Periods
    - Selected Invoices

    Plus exclusions.  For example if a customer pays 10,000.00 and the accout balance
    is 11,000.00 with an invoice in dispute, then it can quickly be unchosen.
    """,
    "data": ['wizard/account_voucher_matching_view.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
}

