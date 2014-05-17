# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution - module extension
#    Copyright (C) 2010- O4SB (<http://openforsmallbusiness.co.nz>).
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
    'name': 'Account Central Billing',
    'version': '1.0',
    'category': 'Accounting',
    'author': 'O4SB',
    'website': 'http://www.openforsmallbusiness.co.nz',
    'depends': ['base', 'account'],
    "description": '''
    This module provides:
        The ability to flag a parent account to be invoiced for all its child accounts
        It is designed to be used like:
            Sales Order raised on child company and follows normal flow.
            At invoice create (or write) the partner_id is automatically changed to the parent
            and the original partner stored in the 'Ordering Partner' field.
            
            It also implements a search enhancement so invoices can be viewed directly from the 
            standard customer screen.  In the case of the child it is only for the child, in the case of
            the parent, for all children.  This functionality has only be tested in views, it may break some
            analysis reports although it may not.  Please report your experience under bugs.
            
            Finally it implements some back referencing for credits and reinvoices by updating origin and 
            comment fields of the credit and reinvoice to reference the original.
    ''',
    'data': ['res_partner_view.xml'],
    'demo': [],
    'test': [],
    'installable': True,
    'active': False,
}