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
    'name': 'Account Types Extension',
    'version': '1.0',
    'category': 'Accounting',
    'author': 'O4SB - Graeme Gellatly',
    'website': 'http://www.openforsmallbusiness.co.nz',
    'depends': ['account'],
    'description': """
    This module updates the list of account types to provide more suitable 
    reporting for countries that require better balance sheets and P&L's than
    openerp provides.  It probably breaks the existing reports.
    
    Have created as a seperate module so other charts can inherit rather than
    creating their own types.
    """,
    'data': ['data/data_account_type.xml'],
    'installable': True,
    'active': False,
}