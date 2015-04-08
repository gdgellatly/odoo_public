#  -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution - module extension
#    Copyright (C) 2010- O4SB (<http://openforsmallbusiness.co.nz>).
#
#    See __openerp__.py for full license description
#
##############################################################################
"""
@summary: Implements pricing enhancements by adding a many2many
          relationship with product ids
        Core changes to get_price_multi - some optimisation and changes to SQL
        Requires monitoring product/pricelist.py for changes as no
        super calls made, straight cut and paste
@todo: Do the same for product categories, implement exclusions
@license: AGPL v3
@author: Graeme Gellatly
@organization: Openforsmallbusiness.co.nz
"""
from openerp.osv import orm, fields


class ProductPricingCategory(orm.Model):
    """Product Price Category"""
    _name = 'product.price.category'
    _description = __doc__

    _columns = {
        'name': fields.char(string='Category Name', required=True),
        'description': fields.text('Description', required=True),
        'product_tmpl_ids': fields.many2many(
            'product.template', string='Product Templates'),
        'product_ids': fields.many2many(
            'product.product', string='Products'),
        'search_pattern': fields.char('Search Pattern'),
        'excl_pattern': fields.char('Search Excl Pattern'),
    }


class ProductTemplate(orm.Model):
    _inherit = 'product.template'

    _columns = {
        'tmpl_price_categ_ids': fields.many2many('product.price.category', string='Template Price Categories')
    }


class ProductProduct(orm.Model):
    _inherit = 'product.product'

    _columns = {
        'price_categ_ids': fields.many2many('product.price.category', string='Product Price Categories')
    }
