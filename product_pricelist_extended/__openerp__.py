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
    'version': '1.1',
    'category': '',
    'author': 'O4SB',
    'website': 'http://www.openforsmallbusiness.co.nz',
    'depends': ["base", 'product'],
    "description": """
    This module implements many2many product ids for pricelist rules and provides
    a report for checking pricelist rules.
    """,
    "init_xml": [],
    'update_xml': ['pricelist_view.xml',
    #               'report/pricelist_report.xml'
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
