# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution - module extension
#    Copyright (C) 2010- O4SB (<http://openforsmallbusiness.co.nz>).
#
##############################################################################

# noinspection PyStatementEffect
{
    'name': 'Pricelist Extensions',
    'version': '1.2',
    'category': '',
    'author': 'O4SB',
    'website': 'http://www.openforsmallbusiness.co.nz',
    'depends': ["base", 'product', 'product_variant_multi'],
    "description": """
    This module implements many2many product ids for pricelist rules and provides
    a report for checking pricelist rules.
    """,
    'data': ['pricelist_view.xml',
                   'product_view.xml',
                   'security/ir.model.access.csv'
    #               'report/pricelist_report.xml'
    ],
    'installable': True,
    'active': False,
}
