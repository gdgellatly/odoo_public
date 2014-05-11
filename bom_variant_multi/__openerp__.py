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
# noinspection PyStatementEffect,PyPep8
{
    'name': 'MRP Bill of Material Templates',
    'version': '1.2',
    'category': 'MRP',
    'author': 'O4SB',
    'website': 'http://www.o4sb.com',
    'depends': ['base', 'product_variant_multi', 'mrp'],
    "description": '''
    This module implements BOM templates, more analogous to account templates than product templates.

    A BOM template is created which then creates the associated BOM's. For any bom line you may specify a
    product template with one of 2 match types One 2 One (simple case) of One Dimension to a different dimension
    where you must specify a match condition (formed as a domain expression on the dimension option object).

    Most of the time the simple case is fine, however when mapping different variants, it pays to use a consistent naming
    scheme.  Examples where this may be the case is say you can get a material in a certain range of colours, and paint in
    a lot more colours so you have 2 different variant dimensions.  By giving each colour the exact same name, or code, or
    sequence number you can match differing dimensions.

    Alternatively where you specify a product in a bom line you can optionally specify a match expression on the
    product object which if met will add the product to the bom, otherwise it will not.  e.g say you have a variant of
    knickers, called frilly knickers, which calls for a quantity of lace then you can match that and if not the lace will
    not be added.
    ''',
    'data': ['mrp_view.xml', 'security/ir.model.access.csv'],
    'demo': [],
    'test': [],
    'installable': True,
    'active': False,
}