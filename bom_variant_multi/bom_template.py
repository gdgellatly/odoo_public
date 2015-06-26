#  -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution - module extension
#    Copyright (C) 2011- O4SB (<http://openforsmallbusiness.co.nz>).
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
"""bom_variant_multi Openerp Module"""

from ast import literal_eval

from openerp.osv import orm, fields
from openerp.tools.translate import _

import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(orm.Model):
    _inherit = 'product.template'

    def _tmpl_bom(self, cr, uid, ids, name, arg, context=None):
        bom_obj = self.pool['mrp.bom']
        res = dict.fromkeys(ids, False)
        bom_ids = bom_obj.search(cr, uid, [('bom_id', '=', False),
                                           ('bom_template', '=', True),
                                           ('product_id.product_tmpl_id.id', 'in', ids)], context=context)
        for bom in bom_obj.browse(cr, uid, bom_ids, context=context):
            res[bom.product_id.product_tmpl_id.id] = True
        return res

    def _get_tmpl_ids(self, cr, uid, ids, context=None):
        bom_obj = self.pool['mrp.bom']
        res = [bom.product_id.product_tmpl_id.id for bom in bom_obj.browse(cr, uid, ids, context=context)]
        return res

    _columns = {'tmpl_bom': fields.function(_tmpl_bom, type='boolean', string='Has Tmpl Bom',
                store={'product.template': (lambda self, c, u, ids, x: ids, [], 10),
                       'mrp.bom': (_get_tmpl_ids, ['product_id', 'bom_template', 'bom_id'], 5)})}


class ProductProduct(orm.Model):
    _inherit = 'product.product'

    def _has_bom(self, cr, uid, ids, name, arg, context=None):
        bom_obj = self.pool['mrp.bom']
        res = dict.fromkeys(ids, False)
        bom_ids = bom_obj.search(cr, uid, [('product_id', 'in', ids),
                                           ('bom_id', '=', False),
                                           ('bom_template', '=', False)])
        for bom in bom_obj.browse(cr, uid, bom_ids, context=context):
            res[bom.product_id.id] = True
        return res

    def _get_product_ids(self, cr, uid, ids, context=None):
        bom_obj = self.pool['mrp.bom']
        res = [bom.product_id.id for bom in bom_obj.browse(cr, uid, ids, context=context)]
        return res

    def _get_tmpl_ids(self, cr, uid, ids, context=None):
        return self.search(cr, uid, [('product_tmpl_id', 'in', ids)], context=context)

    _columns = {'has_bom': fields.function(
        _has_bom, type='boolean', string='Has Bom',
        store={'product.product': (lambda self, c, u, ids, x: ids, [], 10),
               'mrp.bom': (_get_product_ids, ['product_id', 'bom_template', 'bom_id'], 10)}
    )}


class BomDimensionMap(orm.Model):
    """BoM Template Variant Dimension Match"""
    _name = 'bom.dimension_map'
    _description = __doc__

    _columns = {
        'name': fields.char('Name', size=64),
        'mapping_type': fields.selection(
            [('one2one', 'Same Variants One -> One'),
             ('one2diff', 'Different Variants - One -> One Mapping')],
            'Mapping Type', required=True
        ),
        'bom_tmpl_id': fields.many2many(
            'mrp.bom', 'dim_map_mrp_bom_rel', 'dimension_map_id',
            'bom_tmpl_id', 'BoM Templates'
        ),
        'base_dimension_type': fields.many2one(
            'product.variant.dimension.type',
            'Base Dimension Type', required=True
        ),
        'mapped_dimension_type': fields.many2one(
            'product.variant.dimension.type',
            'Mapped Dimension Type'
        ),
        'match_opt_condition': fields.char(
            'Match Condition', size=256,
            help='Domain Expression to select which product should'
                 ' be used, expressed on the product option \n'
                 'The base variable is available which is the '
                 'selected products dimension option'
                 'e.g. [("name", "=", base.name)]'
        ),
        'default_opt': fields.char(
            'Default Condition', size=256,
            help='Domain Expression to select a default product if no'
                 'matching product found, '
                 ' expressed on the product option \n'
                 'The base variable is available which is the '
                 'selected products dimension option'
                 'e.g. [("name", "=", base.name)]'
        ),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default.update({'bom_tmpl_id': False})
        return super(BomDimensionMap, self).copy(
            cr, uid, id, default=default, context=context)

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default.update({'bom_tmpl_id': False})
        return super(BomDimensionMap, self).copy(
            cr, uid, id, default=default, context=context)


class BomTemplate(orm.Model):
    """Implements BOM Template"""
    _inherit = 'mrp.bom'

    _columns = {
        'bom_template': fields.boolean(
            'Use as Template', track_visibility='onchange',
            help="If this field is set to True it matches "
                 "for all products sharing the same template"),
        'dimension_map_ids': fields.many2many(
            'bom.dimension_map', 'dim_map_mrp_bom_rel',
            'bom_tmpl_id', 'dimension_map_id',
            'BoM Variant Dimensions Match'),
        'match_condition': fields.char(
            'Match Condition', size=256,
            help='Domain Expression if this product should be used, '
                 'expressed on the product object'
                 'e.g. [("name", "ilike", "frilly"), '
                 '("name", "ilike", "DD")]'),
        'adj_weight': fields.boolean('Use weight'),
        'company_id': fields.many2one('res.company', 'Company', required=False),


    }

    def onchange_product_id(self, cr, uid, ids,
                            product_id, name, bom_template, context=None):
        """ Changes UoM and name if product_id changes.
        @param name: Name of the field
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        """
        res = super(BomTemplate, self).onchange_product_id(
            cr, uid, ids,
            product_id, name,
            context=context)

        if (bom_template and res and 'value' in res and
                res['value'].get('name', False)):
            if product_id:
                prod = self.pool['product.product'].browse(cr, uid, product_id,
                                                           context=context)
                res['value']['name'] = '%s %s' % (prod.product_tmpl_id.name,
                                                  _('TEMPLATE'))
                message = (_('By selecting to use this product as a template'
                             ' all products of template %s will use this BoM') %
                           prod.product_tmpl_id.name)
                if res.get('warning', False):
                    res['warning'].update({'title': _('Multiple Warnings'),
                                           'message': '%s\n%s' %
                                                      (res['warning']['message'],
                                                       message)})
                else:
                    res['warning'] = {'title': 'Set as Template',
                                      'message': message}
        return res

    def search(self, cr, user, args, offset=0, limit=None, order=None,
               context=None, count=False):
        """
        Override product searches to return templates as well.
        """
        prod_obj = self.pool['product.product']
        op_map = {'=': 'in', '!=': 'not in', '<>': 'not in',
                  'in': 'in', 'not in': 'not in'}
        #TODO - support between combination of <,<= and >, >=
        args2 = args[:]
        arg_offset = 0
        res = False
        for idx, arg in enumerate(args2):
            if arg[0] == 'product_id':
                product_ids = prod_obj.search(cr, user,
                                              [('id', arg[1], arg[2]),
                                               ('is_multi_variants', '=', True)],
                                              context=context)
                tmpl_ids = [prod.product_tmpl_id.id for prod in
                            prod_obj.browse(cr, user, product_ids,
                                            context=context)]
                if tmpl_ids:
                    prod_ids = prod_obj.search(cr, user,
                                               [('product_tmpl_id', 'in',
                                                 tmpl_ids)])
                    operator = op_map.get(arg[1], 'in')
                    if idx > 0 and args2[idx - 1] == '!':
                        operator = operator == 'in' and 'not in' or 'in'
                    extra_args = ['|', '&',
                                  ('bom_template', '=', True),
                                  ('product_id', operator, prod_ids)]
                    args = (args[:idx + arg_offset] + extra_args +
                            args[idx + arg_offset:])
                    arg_offset += len(extra_args)
        try:
            res = super(BomTemplate, self).search(cr, user, args, offset=offset,
                                                  limit=limit, order=order,
                                                  context=context, count=count)
        except:
            _logger.exception('Extended search failed for MRP BoM with domain '
                              '%s. Performing standard search with %s' %
                              (args, args2))
        if not res:
            res = super(BomTemplate, self).search(cr, user, args2, offset=offset,
                                                  limit=limit, order=order,
                                                  context=context, count=count)
        return res

    def _bom_explode(self, cr, uid, bom, factor, properties=None,
                     addthis=False, level=0, routing_id=False, context=None):
        """ Finds Products and Workcenters for related BoM for
        manufacturing order.
        @param bom: BoM of particular product.
        @param factor: Factor of product UoM.
        @param properties: A List of properties Ids.
        @param addthis: If BoM found then True else False.
        @param level: Depth level to find BoM lines starts from 10.
        @return: result: List of dictionaries containing product details.
                 result2: List of dictionaries containing workcenter details.

        """
        #product_id is the product we want to build a bom for, e.g. the parent

        if context is None:
            context={}
        prod_obj = self.pool['product.product']

        try:
            product = prod_obj.browse(cr, uid, context.get('prior_product_id', bom.product_id))
        except:
            product = bom.product_id

        if bom.match_condition and not prod_obj.search(
                cr, uid, literal_eval(bom.match_condition) + [('id', '=', product.id)]):
            return [], []
        if bom.adj_weight:
            factor = (product.weight or 1.0) * factor

        if bom.bom_template and addthis:
            def _find_candidates(products, option):
                cr.execute(
                    'select pp.product_id from product_product_dimension_rel as pp '
                    'left join product_variant_dimension_value as dv '
                    'on pp.dimension_id=dv.id '
                    'where pp.product_id in %s and dv.option_id = %s',
                    (tuple(products), option))
                return (y[0] for y in cr.fetchall())

            orig_variant_option_ids = [x.option_id.id for x in
                                       product.dimension_value_ids]
            candidates = set(prod_obj.search(
                cr, uid,
                [('product_tmpl_id', '=',
                  bom.product_id.product_tmpl_id.id)]))
            dim_option_obj = self.pool['product.variant.dimension.option']
            dim_type_obj = self.pool['product.variant.dimension.type']
            for dim_map in bom.dimension_map_ids:

                #Find the option used
                base_option = dim_option_obj.search(cr, uid, [
                    ('dimension_id', '=', dim_map.base_dimension_type.id),
                    ('id', 'in', orig_variant_option_ids)
                ])
                if dim_map.mapping_type == 'one2one':
                    search_option_id = base_option

                elif dim_map.mapping_type == 'one2diff':
                    # noinspection PyUnusedLocal
                    base = dim_option_obj.browse(cr, uid, base_option)[0]
                    search_option_id = dim_option_obj.search(
                        cr, uid, literal_eval(dim_map.match_opt_condition) +
                        [('dimension_id', '=', dim_map.mapped_dimension_type.id)]
                    )
                    if not search_option_id and dim_map.default_opt:
                        search_option_id = dim_option_obj.search(
                            cr, uid, literal_eval(dim_map.default_opt) +
                            [('dimension_id', '=', dim_map.mapped_dimension_type.id)]
                        )

                else:
                    raise NotImplementedError
                # only one option should match for each map.
                if len(search_option_id) == 1:
                    search_option_id = search_option_id[0]

                elif search_option_id:
                    raise orm.except_orm(_('Error!'),
                                         _('More than one mapped dimension value '
                                           'matched the search condition'))
                else:
                    raise orm.except_orm(_('Error!'),
                                         _('No mapped dimension values '
                                           'matched the search condition'))
                candidates.intersection_update(_find_candidates(candidates, search_option_id))

            if not candidates:
                raise orm.except_orm(_('Error'), _('No matching product found!'))
            if len(candidates) > 1:
                # This code is only called if dimension maps need to be interpolated.
                # It will assume a one2one match on any shared dimensions between the product
                # and the target.  In most cases this will avoid defining dimension maps at all.
                # It excludes non mandatory dimensions
                # First we get our sets of mandatory and non mandatory dimensions
                #of the product
                prod_tmpl = bom.product_id.product_tmpl_id
                dimension_ids = [dim.id for dim in prod_tmpl.dimension_type_ids]
                optional_tmpl_dims = set(dim_type_obj.search(
                    cr, uid,
                    [('mandatory_dimension', '=', False),
                     ('id', 'in', dimension_ids)]
                )
                )
                mandatory_tmpl_dims = set(dim_type_obj.search(
                    cr, uid,
                    [('mandatory_dimension', '=', True),
                     ('id', 'in', dimension_ids)]
                )
                )
                dim_maps = bom.dimension_map_ids
                mapped_dims = []
                # Then any existing dimension maps are dropped from the set
                # under consideration
                for dim_map in dim_maps:
                    if dim_map.mapping_type == 'one2one':
                        mapped_dims.append(dim_map.base_dimension_type.id)
                    else:
                        mapped_dims.append(dim_map.mapped_dimension_type.id)
                optional_tmpl_dims.difference_update(set(mapped_dims))
                mandatory_tmpl_dims.difference_update(set(mapped_dims))

                # non mandatory candidates are dropped
                to_drop = []
                if optional_tmpl_dims:
                    for candidate in prod_obj.browse(cr, uid, list(candidates)):
                        for dim_val in candidate.dimension_value_ids:
                            if dim_val.dimension_id.id in optional_tmpl_dims:
                                to_drop.append(candidate.id)
                if to_drop:
                    candidates.difference_update(set(to_drop))

                # We simulate a one2one match for remaining dimensions

                for dim_id in mandatory_tmpl_dims:
                    search_option_id = dim_option_obj.search(cr, uid, [
                        ('dimension_id', '=', dim_id),
                        ('id', 'in', orig_variant_option_ids)
                    ])
                    if search_option_id and len(search_option_id) == 1:
                        candidates.intersection_update(_find_candidates(
                            candidates, search_option_id[0]))

                if len(candidates) != 1:
                    raise orm.except_orm(_('Error'),
                                         _('No matching product found!'))
            product = prod_obj.browse(cr, uid, list(candidates)[0])
        elif addthis:
            product = bom.product_id
        #now we have a product id that matches
        context.update({'prior_product_id': context.get('product_id'),
                        'product_id': product.id})
        res = super(BomTemplate, self)._bom_explode(
            cr, uid, bom, factor, properties=properties,
            addthis=addthis, level=level,
            routing_id=routing_id, context=context)
        context.update({'product_id': context.get('prior_product_id')})
        if res and not bom.bom_lines:
            res[0][0].update({'name': product.name,
                              'product_id': product.id})
        return res


class MrpProduction(orm.Model):
    _inherit = 'mrp.production'

    def _prepare_lines(self, cr, uid, production,
                       properties=None, context=None):
        if context is None:
            context = {}

        if properties is None:
            properties = []

        context.update({'product_id': production.product_id.id,
                        'prior_product_id': production.product_id.id})
        return super(MrpProduction, self)._prepare_lines(
            cr, uid, production, properties=properties, context=context)

    def _action_compute_lines(self, cr, uid, ids, properties=None,
                              context=None):
        """ Computes bills of material of a product.
        @param properties: List containing dictionaries of properties.
                    The list is appended with the product_id in a dict to
                    avoid changing method signature without context
        @return: No. of products.
        """
        if context is None:
            context = {}

        if properties is None:
            properties = []

        context.update({'product_id': False, 'prior_product_id': False})
        res = []
        for production in self.browse(cr, uid, ids):
            context.update({'product_id': production.product_id.id,
                            'prior_product_id': production.product_id.id})
            res = super(MrpProduction, self)._action_compute_lines(
                cr, uid, [production.id],
                properties=properties, context=context
            )
        return res
