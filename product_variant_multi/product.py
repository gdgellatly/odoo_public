# -*- encoding: utf-8 -*-
# #############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Copyright (C) 2010-2011 Akretion (www.akretion.com). All Rights Reserved
#    @author Sebatien Beau <sebastien.beau@akretion.com>
#    @author Raphaël Valyi <raphael.valyi@akretion.com>
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#    update to use a single "Generate/Update" button & price computation code
#    @author Graeme Gellatly <gdgellatly@gmail.com>
#    add_all_options, variant_codes, better name search, weight support
#    performance optimisation and stats logging
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, orm
import openerp.addons.decimal_precision as dp
# Lib to eval python code with security
from openerp.tools.safe_eval import safe_eval
from openerp.tools.translate import _

import re

import logging

_logger = logging.getLogger(__name__)


class ProductProduct(orm.Model):
    _inherit = "product.product"

    def name_get(self, cr, user, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []

        def _name_get(d):
            name = d.get('name', '')
            code = d.get('default_code', False)
            if code:
                name = '[%s] %s' % (code, name)
            return d['id'], name

        partner_id = context.get('partner_id', False)

        result = []
        for product in self.browse(cr, user, ids, context=context):
            sellers = filter(lambda x: x.name.id == partner_id, product.seller_ids)
            if sellers:
                for s in sellers:
                    mydict = {
                        'id': product.id,
                        'name': s.product_name or product.name,
                        'default_code': s.product_code or product.default_code,
                        'variants': product.variants
                    }
                    result.append(_name_get(mydict))
            else:
                mydict = {
                    'id': product.id,
                    'name': product.name,
                    'default_code': product.default_code,
                    'variants': product.variants
                }
                result.append(_name_get(mydict))
        return result

    def search(self, cr, user, args, offset=0, limit=None, order=None,
               context=None, count=False):
        """
        Override of search to split search strings to make it easier
        to find products.  Will only amend the search if multiple words
        in name search
        """
        if args:
            args2 = []
            for arg in args:
                if arg[0] == 'name' and ' ' in arg[2]:
                    args2 += [[arg[0], arg[1], x] for x in arg[2].split()]
                    if isinstance(arg, tuple):
                        arg = list(arg)
                    arg[2] = arg[2].split()[0]
            args = args + args2
        return super(ProductProduct, self).search(
            cr, user, args, offset=offset, limit=limit, order=order,
            context=context, count=count)

    def name_search(self, cr, user, name='', args=None, operator='ilike',
                    context=None, limit=100):
        """
        Override of name search to split search strings to make it easier
        to find variants
        """
        if not args:
            args = []
        if name:
            if ' ' not in name:
                ids = self.search(cr, user, ['|', ('default_code', '=', name), ('ean13', '=', name)] + args,
                                  limit=limit, context=context)
                if not ids:
                    ids = self.search(cr, user,
                                      [('default_code', operator, name)] + args,
                                      limit=limit, context=context)
            else:
                ids = []
            args2 = [('name', operator, x) for x in name.split()]
            ids += self.search(cr, user, args + args2, limit=limit,
                               context=context)
            if not ids:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    ids = self.search(
                        cr, user,
                        [('default_code', '=', res.group(2))] + args,
                        limit=limit, context=context
                    )
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        return result

    #variant update functions
    def simple_build_product_name(self, cr, uid, products, vals, context=None):
        vals[0].append('name')
        tmpl_name = products[0].product_tmpl_id.name or ''
        [v.append('%s %s' % (str(tmpl_name),
                             str(v[vals[0].index('variants')]))) for
         k, v in vals[1].items()]
        return vals

    def build_product_name(self, cr, uid, ids, context=None):
        return self.build_product_field(cr, uid, ids, 'name', context=context)

    def build_product_field(self, cr, uid, ids, field, context=None):

        # noinspection PyUnusedLocal
        def get_name(prod):
            return ((prod.product_tmpl_id.name or '') +
                    ' ' + (prod.variants or ''))

        if not context:
            context = {}
        context['is_multi_variants'] = True
        obj_lang = self.pool['res.lang']
        lang_ids = obj_lang.search(cr, uid, [('translatable', '=', True)],
                                   context=context)
        lang_code = [x['code'] for x in obj_lang.read(cr, uid, lang_ids,
                                                      ['code'],
                                                      context=context)]
        for code in lang_code:
            context['lang'] = code
            for product in self.browse(cr, uid, ids, context=context):
                new_field_value = getattr('build_product_field',
                                          'get_%s' % field)(product)
                cur_field_value = product[field]
                if new_field_value != cur_field_value:
                    product.write({field: new_field_value}, context=context)
        return True

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def parse(self, cr, uid, o, text, context=None):
        if not text:
            return ''
        vals = text.split('[_')
        description = []
        for val in vals:
            if '_]' in val:
                sub_val = val.split('_]')
                description.extend([(safe_eval(sub_val[0], {'o': o, 'context': context}) or ''),
                                    sub_val[1]])

            else:
                description.append(val)
        return ''.join(description)

    def generate_product_code(self, cr, uid, product_obj, code_generator, context=None):
        """I wrote this stupid function to be able to inherit it in a custom module !"""
        return self.parse(cr, uid, product_obj, code_generator, context=context)

    def build_product_code_and_properties(self, cr, uid, products, vals,
                                          reuse=True, context=None):
        vals[0].extend(['track_production', 'track_outgoing',
                        'track_incoming', 'default_code'])
        if reuse:
            tmpl = products[0].product_tmpl_id
            code_gen = tmpl.code_generator
            new_values = [tmpl.variant_track_production,
                          tmpl.variant_track_outgoing,
                          tmpl.variant_track_incoming]

        #  This regex searches for occurrences of [_o.field_] or [_o.field[n:m]_]
        #  where field is in calculated columns and [n:m] is standard slice
        #  syntax - e.g. TR[_o.variant_code[0]_].40[_o.variant_code[1:]_]DUR
        pattern = re.compile(r'(\[_o\.(%s)(\[?[\d:]*\]?)_\])' % '|'.join(vals[0]))
        # then browse products
        for product in products:
            if not reuse:
                code_gen = product.product_tmpl_id.code_generator
                new_values = [product.product_tmpl_id.variant_track_production,
                              product.product_tmpl_id.variant_track_outgoing,
                              product.product_tmpl_id.variant_track_incoming]
            #because we don't write as we go we need to check for stored values
            res = re.findall(pattern, code_gen)
            parsed_code_gen = code_gen
            for r in res:
                repl_string = vals[1][product.id][vals[0].index(r[1])]
                if r[2]:
                    repl_string = eval("repl_string" + r[2])
                parsed_code_gen = parsed_code_gen.replace(r[0], repl_string)
            # noinspection PyUnboundLocalVariable
            vals[1][product.id].extend(new_values)
            vals[1][product.id].append(self.generate_product_code(
                cr, uid, product,
                parsed_code_gen,
                context=context))
        return vals

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def product_ids_variant_changed(self, cr, uid, ids, res, context=None):
        """it's a hook for product_variant_multi advanced"""
        return True

    @staticmethod
    def generate_variant_code(product):
        r = [(dim.dimension_id.sequence, (dim.option_id.code or '')) for
             dim in product.dimension_value_ids]
        r.sort()
        r = [x[1] for x in r]
        return ''.join(r)

    # noinspection PyUnusedLocal
    def build_variants_code(self, cr, uid, products, vals, context=None):
        vals[0].append('variant_code')
        [vals[1][product.id].append(self.generate_variant_code(product)) for product in products]
        return vals

    def generate_variant_name(self, cr, uid, product, model, separator='',
                              context=None):
        """
        Do the generation of the variant name in a
        dedicated function, so that we can
        inherit this function to hack the code generation
        """
        if not model:
            model = product.variant_model_name
        # adds 100 records or so per minute to speed
        p = self.parse
        r = [(dim.dimension_id.sequence, p(cr, uid, dim, model,
                                           context=context)) for dim in product.dimension_value_ids]
        r.sort()
        r = [x[1] for x in r]
        return separator.join(r)

    def build_variants_name(self, cr, uid, products, vals, reuse=True, context=None):
        if reuse:
            model = products[0].variant_model_name
            sep = products[0].variant_model_name_separator or ''
        else:
            model = False
            sep = ''
        gvn = self.generate_variant_name
        vals[0].extend(['id', 'variants'])
        [vals[1][product.id].extend([product.id,
                                     gvn(cr, uid, product, model, sep,
                                         context=context)])
         for product in products]
        return vals

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def update_variant_price_and_weight(self, cr, uid, products, vals, context=None):
        vals[0].extend(['cost_price_extra', 'price_extra',
                        'weight', 'weight_net'])
        tmpl = products[0].product_tmpl_id
        tmpl_weight = tmpl.weight
        tmpl_weight_net = tmpl.weight_net
        for product in products:
            cost_price_extra = 0.0
            price_extra = 0.0
            weight_extra = 0.0
            for var_obj in product.dimension_value_ids:
                cost_price_extra += var_obj.cost_price_extra
                price_extra += var_obj.price_extra
                weight_extra += var_obj.weight_extra
            vals[1][product.id].extend([cost_price_extra,
                                        price_extra,
                                        tmpl_weight + weight_extra,
                                        tmpl_weight_net + weight_extra])
        return vals

    # End variant update functions

    def _check_dimension_values(self, cr, uid, ids):
        # TODO: check that all dimension_types of the product_template have a corresponding dimension_value ??
        for product in self.browse(cr, uid, ids, {}):
            buffer_ = []
            for value in product.dimension_value_ids:
                buffer_.append(value.dimension_id)
            unique_set = set(buffer_)
            if len(unique_set) != len(buffer_):
                raise orm.except_orm(_('Constraint error :'),
                                     _("On product '%s', there are several "
                                       "dimension values for the same dimension"
                                       " type.") % product.name)
        return True

    # TODO: Check if these 2 functions are even used anywhere anymore
    def compute_product_dimension_extra_price(
            self, cr, uid, product_id, product_price_extra=0.0,
            dim_price_margin=1.0, dim_price_extra=0.0, context=None
    ):
        if context is None:
            context = {}
        dimension_extra = 0.0
        product = self.browse(cr, uid, product_id, context=context)
        for dim in product.dimension_value_ids:
            dimension_extra += (product.product_price_extra *
                                dim.dim_price_margin +
                                dim.dim_price_extra)

        if 'uom' in context:
            product_uom_obj = self.pool['product.uom']
            uom = product.uos_id or product.uom_id
            dimension_extra = product_uom_obj._compute_price(cr, uid,
                                                             uom.id, dimension_extra, context['uom'])
        return dimension_extra

    def compute_dimension_extra_price(self, cr, uid, ids, result,
                                      product_price_extra=0.0,
                                      dim_price_margin=1.0,
                                      dim_price_extra=0.0, context=None):
        if context is None:
            context = {}
        for product in self.browse(cr, uid, ids, context=context):
            dimension_extra = self.compute_product_dimension_extra_price(
                cr, uid, product.id,
                product_price_extra=product_price_extra,
                dim_price_margin=dim_price_margin,
                dim_price_extra=dim_price_extra,
                context=context
            )
            result[product.id] += dimension_extra
        return result

    #ORM Overrides
    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        product = self.browse(cr, uid, id, context=context)
        if product.product_tmpl_id.is_multi_variants:
            raise orm.except_orm(_('Prohibited'),
                                 _('Cannot duplicate templated products'))
        return super(ProductProduct, self).copy(cr, uid, id, default, context)


    def unlink(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        context['unlink_from_product_product'] = True
        return super(ProductProduct, self).unlink(cr, uid, ids, context)

    # noinspection PyUnusedLocal
    def _product_partner_ref(self, cr, uid, ids, name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        for p in self.browse(cr, uid, ids, context=context):
            # noinspection PyUnresolvedReferences
            data = self._get_partner_code_name(cr, uid, [], p,
                                               context.get('partner_id', None),
                                               context=context)
            if not data['variants']:
                data['variants'] = p.variants
            if not data['code']:
                data['code'] = p.code
            if not data['name']:
                data['name'] = p.name
            res[p.id] = ((data['code'] and ('[' + data['code'] + '] ') or '') +
                         (data['name'] or ''))
        return res

    # noinspection PyUnusedLocal
    def _product_cost_price(self, cr, uid, ids, name, arg, context=None):
        """
        Because some functions do not use price get and access standard
        price directly we modify those functions to refer to cost price
        which calls price_get
        """
        # noinspection PyUnresolvedReferences
        return self.price_get(cr, uid, ids, ptype='standard_price',
                              context=context)

    _columns = {
        'name': fields.char('Name', size=128, translate=True),
        'variants': fields.char('Variants', size=128),
        'product_tmpl_id': fields.many2one('product.template', 'Product Template', auto_join=True,
                                           required=True, ondelete="cascade", select=True),
        'dimension_value_ids': fields.many2many(
            'product.variant.dimension.value',
            'product_product_dimension_rel',
            'product_id', 'dimension_id',
            'Dimensions',
            domain="[('product_tmpl_id','=',product_tmpl_id)]"
        ),
        'cost_price_extra': fields.float(
            'Purchase Extra Cost',
            digits_compute=dp.get_precision('Product Price')
        ),
        'volume': fields.float('Volume', help="The volume in m3."),
        'weight': fields.float(
            'Gross weight',
            digits_compute=dp.get_precision('Stock Weight'),
            help="The gross weight in Kg."
        ),
        'weight_net': fields.float(
            'Net weight',
            digits_compute=dp.get_precision('Stock Weight'),
            help="The net weight in Kg."
        ),
        'variant_code': fields.char('Variant Code', size=32),
        'partner_ref': fields.function(
            _product_partner_ref, type='char',
            string='Customer ref'
        ),
        'cost_price': fields.function(
            _product_cost_price, type='float',
            string='Cost Price',
            digits_compute=dp.get_precision('Product Price'),
        )
    }

    _constraints = [
        (_check_dimension_values, 'Error msg in raise', ['dimension_value_ids']),
    ]

