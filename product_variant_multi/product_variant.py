# -*- encoding: utf-8 -*-
##############################################################################
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

import time

from openerp.osv import fields, orm
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

import logging

_logger = logging.getLogger(__name__)


class ProductVariantDimensionType(orm.Model):
    _name = "product.variant.dimension.type"
    _description = "Dimension Type"
    _rec_name = 'description'

    _columns = {
        'description': fields.char('Description', size=64, translate=True),
        'name': fields.char('Dimension Type Name', size=64, required=True),
        'sequence': fields.integer('Sequence', help=("The product 'variants' code will "
                                                     "use this to order the dimension values")),
        'option_ids': fields.one2many('product.variant.dimension.option', 'dimension_id',
                                      'Dimension Options'),
        'product_tmpl_id': fields.many2many('product.template', 'product_template_dimension_rel',
                                            'dimension_id', 'template_id', 'Product Template'),
        'allow_custom_value': fields.boolean('Allow Custom Value',
                                             help=("If true, custom values can be entered "
                                                   "in the product configurator")),
        'mandatory_dimension': fields.boolean('Mandatory Dimension',
                                              help=("If false, variant products will be created "
                                                    "with and without this dimension")),
    }

    _defaults = {
        'mandatory_dimension': 1,
    }

    _order = "sequence, name"

    def name_search(self, cr, uid, name='', args=None, operator='ilike',
                    context=None, limit=None):
        if not context.get('product_tmpl_id', False):
            args = None
        # noinspection PyTypeChecker
        return super(ProductVariantDimensionType,
                     self).name_search(cr, uid, name, args, 'ilike', None, None)

    def button_add_all_option(self, cr, uid, ids, context=None):
        """
        Function adds all options of a type to all relevant product templates
        dimension values.
        """
        if context is None:
            context = {}
        res = []
        for dim in self.browse(cr, uid, ids, context=context):
            tmpl_ids = [template.id for template in dim.product_tmpl_id]
            if tmpl_ids:
                context['dim_type_id'] = dim.id
                self.pool['product.template'].add_all_option(
                    cr, uid, tmpl_ids, context=context)
                res += tmpl_ids
        return list(set(res)) or False

    def button_add_all_and_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context.update({'add_only': True})
        return self.button_add_all_and_update(cr, uid, ids, context=context)

    def button_add_all_and_update(self, cr, uid, ids, context=None):
        """
        Function adds all options of a type to all relevant product templates
        dimension values and then generates the variants.
        """

        tmpl_ids = self.button_add_all_option(cr, uid, ids, context=context)
        if tmpl_ids:
            self.pool.get('product.template').button_generate_variants(
                cr, uid, tmpl_ids, context=context)
        return True

    def copy(self, cr, uid, id, default=None, context=None):
        """
        Override standard copy in order the product template id
        is not copied to stop type being duplicated on product
        templates.
        """
        if default is None:
            default = {}
        default = default.copy()
        default.update({'product_tmpl_id': False})
        return super(ProductVariantDimensionType, self).copy(cr, uid, id,
                                                             default,
                                                             context)


class ProductVariantDimensionOption(orm.Model):
    _name = "product.variant.dimension.option"
    _description = "Dimension Option"

    def _get_dimension_values(self, cr, uid, ids, context=None):
        return self.pool['product.variant.dimension.value'].search(
            cr, uid, [('dimension_id', 'in', ids)], context=context)

    _columns = {
        'name': fields.char('Dimension Option Name', size=64, required=True),
        'code': fields.char('Code', size=64),
        'sequence': fields.integer('Sequence'),
        'dimension_id': fields.many2one('product.variant.dimension.type',
                                        'Dimension Type', ondelete='cascade'),
    }

    _order = "dimension_id, name"

    def button_add_option(self, cr, uid, ids, context=None):
        """
        Assigned to a button in dimension options, it adds the
        selected option(s) to all templates that have that type.
        """
        tmpl_obj = self.pool['product.template']
        for option_id in ids:
            dim = self.browse(cr, uid, option_id, context=context).dimension_id
            tmpl_ids = [template.id for template in dim.product_tmpl_id]
            if tmpl_ids:
                tmpl_obj.add_option_to_all_templates(cr, uid, tmpl_ids,
                                                     option_id,
                                                     context=context)
        return True


class ProductVariantDimensionValue(orm.Model):
    _name = "product.variant.dimension.value"
    _description = "Dimension Value"

    def unlink(self, cr, uid, ids, context=None):
        for value in self.browse(cr, uid, ids, context=context):
            if value.product_ids:
                product_names = [product.name for product in value.product_ids]
                product_list = '\n    - ' + '\n    - '.join(product_names)
                raise orm.except_orm(
                    _('Dimension value can not be removed'),
                    _("The value %s is used by the products : %s \n "
                      "Please remove these products before removing the "
                      "value.") % (value.option_id.name, product_list))
        return super(ProductVariantDimensionValue, self).unlink(
            cr, uid, ids, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['product_ids'] = False
        return super(ProductVariantDimensionValue, self).copy(cr, uid, id,
                                                              default,
                                                              context=context)

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['product_ids'] = False
        return super(ProductVariantDimensionValue, self).copy_data(
            cr, uid, id, default,
            context=context)

    def _get_values_from_types(self, cr, uid, ids, context=None):
        return self.pool['product.variant.dimension.value'].search(
            cr, uid, [('dimension_id', 'in', ids)], context=context)

    def _get_values_from_options(self, cr, uid, ids, context=None):
        return self.pool['product.variant.dimension.value'].search(
            cr, uid, [('option_id', 'in', ids)], context=context)

    _columns = {
        'option_id': fields.many2one('product.variant.dimension.option',
                                     'Option', required=True),
        'name': fields.related(
            'option_id', 'name', type='char',
            relation='product.variant.dimension.option',
            string="Dimension Value", readonly=True
        ),
        'sequence': fields.integer('Sequence'),
        'price_extra': fields.float(
            'Sale Price Extra',
            digits_compute=dp.get_precision('Product Price')
        ),
        'price_margin': fields.float(
            'Sale Price Margin',
            digits_compute=dp.get_precision('Product Price')),
        'cost_price_extra': fields.float(
            'Cost Price Extra',
            digits_compute=dp.get_precision('Product Price')),
        'dimension_id': fields.related(
            'option_id', 'dimension_id', type="many2one",
            relation="product.variant.dimension.type",
            string="Dimension Type",
            readonly=True,
            store={'product.variant.dimension.value': (lambda self, cr, uid, ids, c=None:
                                                       ids, ['option_id'], 10),
                   'product.variant.dimension.option': (_get_values_from_options, ['dimension_id'], 20)}
        ),
        'product_tmpl_id': fields.many2one(
            'product.template', 'Product Template',
            ondelete='cascade'
        ),
        'dimension_sequence': fields.related(
            'dimension_id', 'sequence', type='integer',
            relation='product.variant.dimension.type',
            #used for ordering purposes in the "variants"
            string="Related Dimension Sequence",
            store={'product.variant.dimension.type': (_get_values_from_types, ['sequence'], 10)}
        ),
        'product_ids': fields.many2many(
            'product.product', 'product_product_dimension_rel',
            'dimension_id', 'product_id', 'Variant', readonly=True),
        'active': fields.boolean('Active',
                                 help=("If false, this value will not be "
                                       "used anymore to generate variants.")),
        'weight_extra': fields.float(
            'Weight Extra',
            digits_compute=dp.get_precision('Stock Weight')),
    }

    _defaults = {
        'active': True,
    }

    _sql_constraints = [('opt_dim_tmpl_uniq',
                         'UNIQUE(option_id, dimension_id, product_tmpl_id)',
                         _('The combination option and dimension type '
                           'already exists for this product template !')), ]

    _order = "dimension_sequence, dimension_id, sequence, option_id"


class ProductTemplate(orm.Model):
    _inherit = "product.template"
    _order = "name asc"

    _columns = {
        'name': fields.char('Name', size=128, translate=True, required=False),
        'dimension_type_ids': fields.many2many(
            'product.variant.dimension.type',
            'product_template_dimension_rel',
            'template_id', 'dimension_id',
            'Dimension Types'
        ),
        'value_ids': fields.one2many('product.variant.dimension.value',
                                     'product_tmpl_id',
                                     'Dimension Values'),
        'variant_ids': fields.one2many('product.product', 'product_tmpl_id',
                                       'Variants'),
        'variant_model_name': fields.char(
            'Variant Model Name', size=64, required=True,
            help=('[_o.dimension_id.name_] will be replaced with the'
                  ' name of the dimension and [_o.option_id.code_] '
                  'by the code of the option. Example of Variant '
                  'Model Name : "[_o.dimension_id.name_] - '
                  '[_o.option_id.code_]"')
        ),
        'variant_model_name_separator': fields.char(
            'Variant Model Name Separator', size=64,
            help=('Add a separator between the elements '
                  'of the variant name')
        ),
        'code_generator': fields.char(
            'Code Generator', size=256,
            help=('enter the model for the product code, all parameter'
                  ' between [_o.my_field_] will be replace by the '
                  'product field. Example product_code model : '
                  'prefix_[_o.variants_]_suffixe ==> result : '
                  'prefix_2S2T_suffix')
        ),
        'is_multi_variants': fields.boolean('Is Multi Variants'),
        'variant_track_production': fields.boolean(
            'Track Production Lots on variants ?'),
        'variant_track_incoming': fields.boolean(
            'Track Incoming Lots on variants ?'),
        'variant_track_outgoing': fields.boolean(
            'Track Outgoing Lots on variants ?'),
    }

    _defaults = {
        'variant_model_name': '[_o.option_id.name_]',
        'variant_model_name_separator': ' - ',
        'is_multi_variants': False,
        'code_generator': '[_o.variant_code_]',
    }

    def add_option_to_all_templates(self, cr, uid, ids, option_id,
                                    context=None):
        """
        Function adds a singular option to all relevant product templates
        dimension values.  Essentially the inverse of add_all_option
        """
        dim_val_obj = self.pool['product.variant.dimension.value']
        existing_opt = dim_val_obj.search(cr, uid,
                                          [('option_id.id', '=', option_id),
                                           ('product_tmpl_id.id', 'in', ids)],
                                          context=context)
        if existing_opt:
            existing_tmpl = set([x['product_tmpl_id'][0] for x in
                                 dim_val_obj.read(cr, uid, existing_opt,
                                                  ['product_tmpl_id'])])
            ids = set(ids) - existing_tmpl
        if ids:
            vals = {'value_ids': [[0, 0, {'option_id': option_id}]]}
            self.write(cr, uid, ids, vals, context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        if context and context.get('unlink_from_product_product', False):
            for template in self.browse(cr, uid, ids, context):
                if not template.is_multi_variants:
                    super(ProductTemplate, self).unlink(cr, uid, [template.id], context)
        else:
            for template in self.browse(cr, uid, ids, context):
                if not template.variant_ids:
                    super(ProductTemplate, self).unlink(cr, uid, [template.id], context)
                else:
                    raise orm.except_orm(
                        _("Cannot delete template"),
                        _("This template has existing corresponding "
                          "products...")
                    )
        return True

    def add_all_option(self, cr, uid, ids, context=None):
        #Reactive all unactive values
        value_obj = self.pool['product.variant.dimension.value']
        for template in self.browse(cr, uid, ids, context=context):
            values_ids = value_obj.search(cr, uid,
                                          [('product_tmpl_id', '=', template.id),
                                           '|', ('active', '=', False),
                                           ('active', '=', True)],
                                          context=context)
            value_obj.write(cr, uid, values_ids,
                            {'active': True}, context=context)
            values = value_obj.browse(cr, uid, values_ids, context=context)
            existing_option_ids = [value.option_id.id for value in values]
            vals = {'value_ids': []}
            for dim in template.dimension_type_ids:
                for option in dim.option_ids:
                    if not option.id in existing_option_ids:
                        vals['value_ids'] += [[0, 0, {'option_id': option.id}]]
            self.write(cr, uid, [template.id], vals, context=context)
        return True

    def get_products_from_product_template(self, cr, uid, ids, context=None):
        product_tmpl = self.read(cr, uid, ids, ['variant_ids'], context=context)
        return [id for vals in product_tmpl for id in vals['variant_ids']]

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        template = self.browse(cr, uid, id, context=context)
        if not template.is_multi_variants:
            raise orm.except_orm(
                _('Prohibited'),
                _('Cannot duplicate single product templates'))
        default = default.copy()
        default.update({'variant_ids': False})
        return super(ProductTemplate, self).copy(
            cr, uid, id, default, context=context)

    def copy_translations(self, cr, uid, old_id, new_id, context=None):
        if context is None:
            context = {}
        # avoid recursion through already copied records in case of circular relationship
        seen_map = context.setdefault('__copy_translations_seen', {})
        if old_id in seen_map.setdefault(self._name, []):
            return
        seen_map[self._name].append(old_id)
        return super(ProductTemplate, self).copy_translations(
            cr, uid, old_id, new_id,
            context=context
        )

    @staticmethod
    def _create_variant_list(vals):

        def cartesian_product(args):
            if len(args) == 1:
                return [x and [x] or [] for x in args[0]]
            return [(i and [i] or []) + j for j in cartesian_product(args[1:]) for i in args[0]]

        return cartesian_product(vals)

    def button_generate_variants(self, cr, uid, ids, context=None):
        start_time = time.time()
        total_created = 0
        total_updated = 0
        variants_obj = self.pool['product.product']

        #Define an update and write function
        def temp_insert_and_update():
            if not vals[1]:  # Nothing to insert
                return
            temp_product_table = 'temp_product_%d' % product_temp.id
            # noinspection PyUnusedLocal
            to_insert_val_args = '(' + ','.join(['%s' for y in range(len(vals[0]))]) + ')'
            # Mogrify records here to stop SQL injection as cr.execute cannot easily handle the values
            # and executemany defeats the purpose
            to_insert_args = ','.join([cr.mogrify(to_insert_val_args, tuple(record)) for record in vals[1].values()])
            set_clause = ', '.join(['%s=%s.%s' % (col, temp_product_table, col) for col in vals[0]])
            #Create a temporary table based on template_id
            #using all the same column names (without NOT NULL constraints
            #hence SELECT rather then LIKE that will be dropped on commit
            #Insert all of the variant values into it
            #Update the product table
            #Drop the rows (in case we want to call multiple times)

            cr.execute(
                '''CREATE TEMP table ''' + temp_product_table + ''' ON COMMIT DROP AS
        SELECT * FROM product_product WITH NO DATA;
   INSERT INTO ''' + temp_product_table + ' (' + ','.join(vals[0]) + ''')
        VALUES ''' + to_insert_args + ''';
  UPDATE product_product
      SET ''' + set_clause +
                ' FROM ' + temp_product_table +
                ' WHERE product_product.id=' + temp_product_table + '''.id;
  DELETE FROM ''' + temp_product_table
            )

        def generator(func):
            t_start = time.time()
            _logger.debug("Starting to %s..." % func.func_name.replace('_', ' '))
            gen_res = func(cr, uid, products, vals, context=context)
            t_end = time.time()
            _logger.debug("The %s took %0.3f ms." %
                          (func.func_name.replace('_', ' '),
                           (t_end - t_start) * 1000.0))
            return gen_res

        for product_temp in self.browse(cr, uid, ids, context=context):
            t1 = time.time()
            res = {}
            temp_val_list = []
            for value in product_temp.value_ids:
                if res.get(value.dimension_id, False):
                    res[value.dimension_id] += [value.id]
                else:
                    res[value.dimension_id] = [value.id]
            for dim in res:
                temp_val_list += [res[dim] + (not dim.mandatory_dimension and
                                              [None] or [])]

            existing_product_ids = variants_obj.search(
                cr, uid, [('product_tmpl_id', '=',
                           product_temp.id)]
            )
            created_product_ids = []
            if temp_val_list:
                list_of_variants = self._create_variant_list(temp_val_list)
                existing_product_dim_value = variants_obj.read(
                    cr, uid,
                    existing_product_ids,
                    ['dimension_value_ids']
                )
                list_of_variants_existing = [x['dimension_value_ids'] for x
                                             in existing_product_dim_value]
                [x.sort() for x in list_of_variants_existing]
                [x.sort() for x in list_of_variants]
                list_of_variants_to_create = [x for x in list_of_variants if x
                                              not in list_of_variants_existing]

                _logger.debug("variant existing : %s, variant to create : %s",
                              len(list_of_variants_existing),
                              len(list_of_variants_to_create))

                vals = {'product_tmpl_id': product_temp.id}
                for idx, variant in enumerate(list_of_variants_to_create, 1):
                    vals['dimension_value_ids'] = [(6, 0, variant)]

                    cr.execute("SAVEPOINT pre_variant_save")
                    try:
                        created_product_ids.append(variants_obj.create(
                            cr, uid, vals,
                            {'generate_from_template': True}
                        )
                        )
                        if idx % 50 == 0:
                            _logger.debug("product created : %s", idx)
                    except Exception, e:
                        _logger.error("Error creating product variant: %s",
                                      e, exc_info=True)
                        _logger.debug("Values used to attempt creation of "
                                      "product variant: %s", vals)
                        cr.execute("ROLLBACK TO SAVEPOINT pre_variant_save")
                    cr.execute("RELEASE SAVEPOINT pre_variant_save")
                _logger.debug("product created : %s",
                              len(list_of_variants_to_create))
            if context.get('add_only', False):
                product_ids = created_product_ids
            else:
                product_ids = existing_product_ids + created_product_ids
            products = variants_obj.browse(cr, uid, product_ids,
                                           context=context)
            #order is important - cannot trust dicts to maintain so dual list
            vals = [[], {p: [] for p in product_ids}]

            # FIRST, Generate/Update variant names ('variants' field)
            vals = generator(variants_obj.build_variants_name)
            vals = generator(variants_obj.build_variants_code)
            vals = generator(variants_obj.update_variant_price_and_weight)
            vals = generator(variants_obj.build_product_code_and_properties)
            vals = generator(variants_obj.simple_build_product_name)
            temp_insert_and_update()
            # else:
            #     # play it safe and go the long way
            #     temp_insert_and_update()
            #     cr.commit()
            #     _logger.debug("Start of generation/update of product names...")
            #     variants_obj.build_product_name(cr, uid, product_ids,
            #                                     context=context)
            #     _logger.debug("End of generation/update of product names.")
            t2 = time.time()
            time_diff = (t2 - t1) * 1000.0
            _logger.debug("The %s took %0.3f ms to create %d and "
                          "update another %d records." % (
                              'Total Product Template Update', time_diff,
                              len(created_product_ids),
                              len(existing_product_ids)))
            _logger.debug("Average time of %0.3f ms / record or %0.3f records "
                          "/ minute." %
                          ((time_diff / float(len(product_ids))),
                           (float(len(product_ids) / (time_diff / 60000.0)))))
            total_created += len(created_product_ids)
            total_updated += len(existing_product_ids)
        end_time = time.time()
        time_diff = (end_time - start_time) * 1000.0
        _logger.info("The %s took %0.3f ms to create %d and "
                     "update another %d records." % (
                         'Total Variant Update', time_diff,
                         total_created,
                         total_updated))
        _logger.debug("Average time of %0.3f ms / record or %0.3f records "
                      "/ minute." %
                      (time_diff / float(total_created + total_updated),
                       float(total_created + total_updated) / (time_diff / 60000.0)))

        return True
