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

{
    'name': 'Partner Statement of Account Report',
    'version': '0.9',
    'category': 'Reporting',
    'author': 'O4SB - Graeme Gellatly',
    'website': 'http://www.openforsmallbusiness.co.nz',
    'depends': ["base", "account", "report_aeroo"],
    "description": """
        *** This module is AGPLv3 and incompatible with OpenERP Enterprise Private Use License.  It may also depend on other AGPLv3 modules
    for which neither OpenERP or I hold copyright, so sorry Private Use customers, I am unable to dual license ***

    This module provides the following features :
    A wizard for producing Account Statements, with parser and default report layout in Aeroo.  It has been tested for its primary use as a Customer Statement of Account.
    It supports:
        Consolidated Statements - i.e. One statement from multiple companies.
        Central Debtor Statements - i.e One statement for a parent debtor consolidating all the children.
        An activity statement, with transactions during the period, or an open item statement with all current unreconciled entries.
        Aging by an arbitrary number of days, or by months.  In the case of months select the period in which current transactions occurred.
        Include or exclude zero balances.
        Include or exclude reconciled entries.
        Include or exclude partner initial balance.
        Selection of receivables, payables or both.
    
    Note in v6 there was a dependency on GST module.  With 6.1 this dependency is no longer required.
    """,
    "init_xml": [],
    'update_xml': [
        'wizard/account_report_statement_view.xml',
        'report/report_statement.xml',
        ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}