from openerp.osv import orm, fields
from collections import defaultdict
from psycopg2 import IntegrityError


class DimensionMerge(orm.TransientModel):
    """Merge Dimensions"""
    _name = 'dimension.merge'
    _columns = {
        'del_option': fields.many2many(
            'product.variant.dimension.option',
            required=True, string='To be deleted'),
        'keep_option': fields.many2one('product.variant.dimension.option',
                                       required=True, string='Merge into'),
        'dimension_id':
            fields.many2one('product.variant.dimension.type', required=True,
                            string='Dimension Type'),
    }

    def default_get(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        res = super(DimensionMerge, self).default_get(
            cr, uid, fields_list, context=context)
        if context.get('active_model') == 'product.variant.dimension.type':
            if 'dimension_id' in fields_list:
                res.update({'dimension_id': context.get('active_id')})
        return res

    def _get_product_dependencies(self, cr, uid, ids, context=None):
        """
        Get all the dependencies of the product_product table
        """
# get list of dependent tables
        cr.execute("""
SELECT cl1.relname, att1.attname
FROM pg_constraint as con, pg_class as cl1, pg_class as cl2,
pg_attribute as att1, pg_attribute as att2
WHERE con.conrelid = cl1.oid
AND con.confrelid = cl2.oid
AND array_lower(con.conkey, 1) = 1
AND con.conkey[1] = att1.attnum
AND att1.attrelid = cl1.oid
AND cl2.relname = 'product_product'
AND att2.attname = 'id'
AND array_lower(con.confkey, 1) = 1
AND con.confkey[1] = att2.attnum
AND att2.attrelid = cl2.oid
AND con.contype = 'f';
"""
                   )
        return cr.fetchall()

    @staticmethod
    def _get_templates(wiz):
        return [x.id for x in wiz.dimension_id.product_tmpl_id]

    def _get_product_pairings(self, cr, wiz):
        """
        Find the matching product(s) to merge
        A product pairing will have
        Old id (one or more options, including the option to be removed)
        New id (identical to old_id except the option to be removed is replaced by the option to keep)
        Barring manual deletions every old_id should have a new_id.
        Every old id can have only one new_id and vice versa
        We must check inactive.
        :return: list of tuples, (old_id, new_id)
        """

        def _get_product_ids(option):
            # get list of ids
            cr.execute("""SELECT ppdl.product_id
FROM product_product_dimension_rel ppdl
LEFT JOIN product_variant_dimension_value pvdv ON ppdl.dimension_id=pvdv.id
WHERE pvdv.option_id = %s""", (option,))
            res = cr.fetchall()
            if not res:
                return []
            product_ids = [r[0] for r in res]
            cr.execute("""
SELECT pp.product_tmpl_id, pp.id, array_agg(ppdl.dimension_id ORDER BY ppdl.dimension_id ASC)
FROM product_product pp
LEFT JOIN product_product_dimension_rel ppdl ON pp.id = ppdl.product_id
LEFT JOIN product_variant_dimension_value pvdv ON ppdl.dimension_id=pvdv.id
WHERE pvdv.option_id != %s AND pp.id IN %s
GROUP BY pp.product_tmpl_id, pp.id
ORDER BY pp.product_tmpl_id, pp.id ;
""", (option, tuple(product_ids)))
            res = cr.fetchall()
            dimension_map = {}
            if res:
                dimension_map.update({r[1]: r for r in res})
                ids_to_add = [p for p in product_ids if p not in dimension_map.keys()]
            else:
                ids_to_add = product_ids
            if ids_to_add:
                cr.execute("""
                SELECT product_tmpl_id, id, array[]::int[]
                FROM product_product WHERE id in %s""", (tuple(ids_to_add),))
                res = cr.fetchall()
                dimension_map.update({r[1]: r for r in res})
            #needs to return a dicts of dicts - product_template: dims: product
            res = defaultdict(dict)
            for template, product, dims in dimension_map.values():
                res[template][tuple(sorted(dims))] = product
            return res

        if not isinstance(wiz.id, (int, long)):
            raise orm.except_orm("Error", "Something bad could happen here")
        pairing = []
        keep_product_ids = _get_product_ids(wiz.keep_option.id)
        for option in wiz.del_option:
            del_product_ids = _get_product_ids(option.id)

            if not (set(del_product_ids.keys()) <= set(keep_product_ids.keys())):
                error_ids = set(del_product_ids.keys()) - set(keep_product_ids.keys())
                raise orm.except_orm(
                    "Error", "Template ids %s do not contain the merge "
                             "dimension" % error_ids)
            try:
                for tmpl, dimension in del_product_ids.items():
                    pairing.extend([(del_product_ids[tmpl][d],
                                     keep_product_ids[tmpl][d])
                                    for d in dimension.keys()])
            except KeyError:
                raise orm.except_orm("Error", "Something bad could happen here")
        return pairing

    def do_merge(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        wiz = self.browse(cr, uid, ids, context)[0]

        tables = self._get_product_dependencies(cr, uid, ids, context=context)
        pairings = self._get_product_pairings(cr, wiz)
        value_clause = ['(%s,%s)' % x for x in pairings]
        value_clause = ','.join(value_clause)
        # First update dependent tables
        to_delete = [old for old, new in pairings]
        del_options = tuple([x.id for x in wiz.del_option])
        for table, column in tables:
            cr.execute("""SAVEPOINT update_table""")
            try:
                query = ('UPDATE %s SET %s=vals.new_id from (values ' % (table, column) + value_clause +
                         ') as vals(old_id, new_id) where %s.%s=vals.old_id' % (table, column))
                cr.execute(query)
            except IntegrityError as e:
                cr.execute("""ROLLBACK TO SAVEPOINT update_table;""")
                print table
                if e.pgcode == '23505':

                    del_query = """DELETE FROM %s where %s IN %%s;""" % (table, column)
                    cr.execute(del_query, (tuple(to_delete),))
            else:
                cr.execute("""RELEASE SAVEPOINT update_table""")


        # Delete obselete codes
        cr.execute("""
DELETE FROM product_variant_dimension_value
WHERE option_id IN %s""", (del_options,))
        cr.execute("""
DELETE FROM product_variant_dimension_option
WHERE id IN %s""", (del_options,))
        cr.execute("""
DELETE FROM product_product
WHERE id IN %s""", (tuple(to_delete),))
        return True

# class TemplateSplit(orm.TransientModel):
#     _name = 'template.dimension.split'
#
#     _columns = {
#         'product_tmpl_id': fields.many2one(
#             'product.template', 'Product Template'),
#         'dimension_id': fields.many2one('product.variant.dimension.value'),
#         'code_position': fields.selection(
#             [('start', 'Start of Code'),
#              ('end', 'End of Code'),
#              ('before', 'Before variant codes'),
#              ('after', 'after_variant_codes')],
#             'Code Generator')
#     }
#
#     # When splitting we must copy all properties
#
#     def _write_new_values(self, cr, uid, wiz, tmpl, new_tmpl, value, dimensions, context=None):
#
#         tmpl_obj.add_all_option(cr, uid, [new_tmpl.id], context=context)
#
#
#     def split_dimension(self, cr, uid, ids, context=None):
#         dim_obj = self.pool['product.variant.dimension.type']
#         value_obj = self.pool['product.variant.dimension.value']
#         tmpl_obj = self.pool['product.template']
#         #we need to create a new template for each option respecting price_extra etc
#         wiz = self.browse(cr, uid, ids, context=context)
#         tmpl = wiz.product_tmpl_id
#         dimension = wiz.dimension_id
#         new_dimensions = (6, 0, [x.id for x in tmpl.dimension_type_ids if x != dimension.id])
#         if dimension.mandatory_dimension:
#             dimension_option_ids = [None]
#             dimension_value_ids = [None]
#         else:
#             dimension_option_ids = []
#             dimension_value_ids = []
#         dimension_value_ids += value_obj.browse(cr, uid, value_obj.search(
#             cr, uid, [('dimension_id', '=', dimension.id),
#                       ('product_tmpl_id', '=', tmpl.id)]), context=context)
#         dimension_option_ids += [x for x in dimension.option_ids]
#
#         if len(dimension_value_ids) > 1:
#             for value in dimension_value_ids[1:]:
#
#                 tmpl_obj = self.pool['product.template']
#                 product_obj = self.pool['product.product']
#                 new_code_gen = tmpl.code_generator
#                 if wiz.code_pos == 'start':
#                     new_code_gen = value.code + tmpl.code_generator
#                 elif wiz.code_pos == 'end':
#                     new_code_gen = tmpl.code_generator + value.code
#                 elif wiz.code_pos == 'before':
#                     index = tmpl.code_generator.find('[_')
#                     if index > -1:
#                         new_code_gen = tmpl.code_generator[:index] + value.code + tmpl.code_generator[index:]
#                 elif wiz.code_pos == 'before':
#                     index = tmpl.code_generator.find('_]')
#                     if index > -1:
#                         new_code_gen = tmpl.code_generator[:index+2] + value.code + tmpl.code_generator[index+2:]
#
#                 defaults = {
#                     'name': '%s %s' % (tmpl.name, value.name),
#                     'dimension_type_ids': new_dimensions,
#                     'dimension_value_ids': [(6, 0, [])],
#                     'list_price': tmpl.list_price + value.price_extra,
#                     'weight': tmpl.weight + value.weight_extra,
#                     'code_generator': new_code_gen
#                     }
#                 self.copy()
#                 new_tmpl_id = tmpl_obj.copy(
#                     cr, uid, tmpl.id, default=defaults, context=context)
#                 new_tmpl = tmpl_obj.browse(cr, uid, new_tmpl_id, context=context)
#                 # Xfer products and values
#                 product_obj.write(cr, uid, {'product_tmpl_id':})
#                 value.write({'product_tmpl_id': new_tmpl_id})
#
#         if dimension_value_ids[0]:
#             value = dimension_value_ids[0]
#             new_tmpl_name = '%s %s' % (tmpl.name, value.name)
#             new_tmpl_code = self._parse(wiz.code_generator, tmpl, value)
