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

{
    'name': 'Account Financial Report Formatting Extension',
    'version': '1.0',
    'category': 'Accounting',
    'author': 'Graeme Gellatly - O4SB',
    'website': 'http://www.openforsmallbusiness.co.nz',
    'depends': ['account'],
    "description": """
    =============================================
    Account Financial Report Formatting Extension
    =============================================

    Extends the default account financial report to allow header and footer
    totals to be customised.  The default behaviour is 'top' and behaves
    identically to the default report where header details and totals are
    put above its children.  The other positions are:
    * 'bottom' where it appears below the children
    * 'mixed', balances below children, heading above
    * 'none', not displayed at all

    """,
    "data": ['account_financial_report_view.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
}

