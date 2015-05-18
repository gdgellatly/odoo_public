# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2011- O4SB (<http://www.openforsmallbusiness.co.nz>)
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
    'name': 'Purchase Pricelist Recalculation',
    'version': '1.0',
    'category': 'Sales & Purchases',
    'description': """
        This module adds a wizard on purchase order and supplier invoice which will let the user change the pricelist
        and the concerned purchase order lines will take an effect.
     """,
    'author': 'O4SB - Graeme Gellatly, OpenERP SA',
    'depends': ['purchase', 'account'],
    'init_xml': [],
    'update_xml': [
        'wizard/wizard_purchase_pricelist_recalculation.xml',
        'wizard/wizard_supplier_invoice_pricelist_recalculation.xml'
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: