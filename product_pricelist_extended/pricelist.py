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
from openerp.tools.translate import _
# noinspection PyUnresolvedReferences
from openerp.addons.product._common import rounding


class ProductPricelist(orm.Model):
    """
    Inherited class - to change pricing calculation and options
    """
    _inherit = 'product.pricelist'
    _order = 'name'

    def price_get_multi(self, cr, uid, pricelist_ids,
                        products_by_qty_by_partner, context=None):
        """multi products 'price_get'.
           @param pricelist_ids:
           @param products_by_qty_by_partner:
           @param context: {
             'date': Date of the pricelist (%Y-%m-%d),}
           @return: a dict of dict with product_id as key and a dict
                       'price by pricelist' as value
           @note: includes bug fix in sql statement to correctly access
                   plversions over Openerp trunk as flagged as won't fix
           @note: since I don't believe that the min and max margin code works
                   it is disabled in order to speed things up.
        """

        def _create_parent_category_list(cat_id, categ_lst):
            """
            Creates parent category list.
            @param cat_id:
            """
            if not cat_id:
                return []
            parent_categ_id = product_category_tree.get(cat_id)
            if parent_categ_id:
                categ_lst.append(parent_categ_id)
                return _create_parent_category_list(parent_categ_id, categ_lst)
            else:
                return categ_lst

        if context is None:
            context = {}

        date = context.get('date', fields.date.today())

        currency_obj = self.pool['res.currency']
        product_obj = self.pool['product.product']
        product_template_obj = self.pool['product.template']
        product_uom_obj = self.pool['product.uom']
        supplierinfo_obj = self.pool['product.supplierinfo']
        price_type_obj = self.pool['product.price.type']
        product_pricelist_version_obj = self.pool['product.pricelist.version']
        product_pricelist_obj = self.pool['product.pricelist']

        #  product.pricelist.version:
        if not pricelist_ids:
            pricelist_ids = product_pricelist_obj.search(cr, uid, [],
                                                         context=context)

        plversion_ids = product_pricelist_version_obj.search(cr, uid, [
            ('pricelist_id', 'in', pricelist_ids),
            '|', ('date_start', '=', False), ('date_start', '<=', date),
            '|', ('date_end', '=', False), ('date_end', '>=', date),
        ])
        if len(pricelist_ids) != len(plversion_ids):
            msg = '''At least one pricelist has no active version!
                    Please create or activate one.'''
            raise orm.except_orm(_('Warning !'), _(msg))

        versions = product_pricelist_version_obj.read(cr, uid, plversion_ids,
                                                      ['pricelist_id', 'id'])
        plversions_dict = {}
        for version in versions:
            plversions_dict[version['pricelist_id'][0]] = version['id']

        #  product.product:
        product_ids = [i[0] for i in products_by_qty_by_partner]
        products = product_obj.browse(cr, uid, product_ids, context=context)
        products_dict = dict([(item.id, item) for item in products])

        #  product.category:
        if context.get('product_category_tree'):
            product_category_tree = context.get('product_category_tree')
        else:
            product_category_obj = self.pool.get('product.category')
            product_category_ids = product_category_obj.search(cr, uid, [])
            product_categories = product_category_obj.read(
                cr, uid, product_category_ids, ['parent_id'])
            product_category_tree = {item['id']: item['parent_id'][0] for
                                     item in product_categories if
                                     item['parent_id']}
            context['product_category_tree'] = product_category_tree

        results = {}
        for product_id, qty, partner in products_by_qty_by_partner:

            tmpl_id = (products_dict[product_id].product_tmpl_id and
                       products_dict[product_id].product_tmpl_id.id or False)
            categ_id = (products_dict[product_id].categ_id and
                        products_dict[product_id].categ_id.id or False)
            categ_ids = _create_parent_category_list(categ_id, [categ_id])
            if categ_ids:
                categ_where = '(categ_id IN (' + ','.join(
                    [str(x) for x in categ_ids]) + '))'
            else:
                categ_where = '(categ_id IS NULL)'

            if partner:
                partner_where = ('base <> -2 OR %s IN '
                                 '(SELECT name FROM product_supplierinfo WHERE product_tmpl_id = %s) ')
                partner_args = (partner, product_id)
            else:
                partner_where = 'base <> -2 '
                partner_args = ()

            for pricelist_id in pricelist_ids:
                price = False

                cr.execute(
                    'SELECT i.*, pl.currency_id '
                    'FROM ((product_pricelist_item '
                    'LEFT JOIN pricelist_item_product_rel '
                    'ON product_pricelist_item.id='
                    'pricelist_item_product_rel.pricelist_item_id) '
                    'LEFT JOIN pricelist_item_tmpl_rel '
                    'ON product_pricelist_item.id='
                    'pricelist_item_tmpl_rel.pricelist_item_id) AS i, '
                    'product_pricelist_version AS v, '
                    'product_pricelist AS pl '
                    'WHERE (product_tmpl_id IS NULL OR product_tmpl_id = %s) '
                    'AND (tmpl_id IS NULL OR tmpl_id = %s) '
                    'AND (product_id IS NULL OR product_id = %s) '
                    'AND (prod_id IS NULL or prod_id = %s) '
                    'AND (' + categ_where + ' OR (categ_id IS NULL)) '
                    'AND (' + partner_where + ') '
                    'AND price_version_id = %s '
                    'AND (min_quantity IS NULL OR min_quantity <= %s) '
                    'AND i.price_version_id = v.id '
                    'AND v.pricelist_id = pl.id '
                    'ORDER BY sequence',
                    (tmpl_id, tmpl_id, product_id, product_id) +
                    partner_args + (plversions_dict[pricelist_id], qty))
                res1 = cr.dictfetchall()
                uom_price_already_computed = False
                for res in res1:
                    if res:
                        if res['base'] == -1:
                            try:
                                parent_pl_price = product_pricelist_obj.price_get(
                                    cr, uid, [res['base_pricelist_id']], product_id,
                                    qty, context=context)[res['base_pricelist_id']]
                                ptype_currency_id = product_pricelist_obj.browse(cr, uid, res[
                                    'base_pricelist_id']).currency_id.id
                                price = currency_obj.compute(cr, uid, ptype_currency_id, res['currency_id'],
                                                             parent_pl_price, round=False)
                            except KeyError:
                                price = 0.0
                        elif res['base'] == -2:
                            #  this section could be improved by moving the
                            #  queries outside the loop:
                            where = []
                            if partner:
                                where = [('name', '=', partner)]
                            sinfo = supplierinfo_obj.search(cr, uid,
                                                            [('product_id', '=', tmpl_id)] + where)
                            price = 0.0
                            if sinfo:
                                qty_in_product_uom = qty
                                product_default_uom = \
                                    product_template_obj.read(cr, uid, [tmpl_id], ['uom_id'])[0]['uom_id'][0]
                                supplier = supplierinfo_obj.browse(cr, uid, sinfo, context=context)[0]
                                seller_uom = supplier.product_uom and supplier.product_uom.id or False
                                if seller_uom and product_default_uom and product_default_uom != seller_uom:
                                    uom_price_already_computed = True
                                    qty_in_product_uom = product_uom_obj._compute_qty(
                                        cr, uid, product_default_uom, qty, to_uom_id=seller_uom)
                                cr.execute('SELECT * '
                                           'FROM pricelist_partnerinfo '
                                           'WHERE suppinfo_id IN %s'
                                           'AND min_quantity <= %s '
                                           'ORDER BY min_quantity DESC LIMIT 1', (tuple(sinfo), qty_in_product_uom,))
                                res2 = cr.dictfetchone()
                                if res2:
                                    price = res2['price']
                        else:
                            price_type = price_type_obj.browse(cr, uid, int(res['base']))
                            price = currency_obj.compute(
                                cr, uid, price_type.currency_id.id, res['currency_id'],
                                product_obj.price_get(
                                    cr, uid, [product_id], price_type.field, context=context)[product_id],
                                round=False, context=context)

                            uom_price_already_computed = True
                            context.update({'already_computed': True})

                        if price is not False:
                            # code commented as it is plainly wrong - fields also hidden in view
                            # price_limit = price

                            price *= 1.0 + (res['price_discount'] or 0.0)
                            price = rounding(price, res['price_round'])
                            price += (res['price_surcharge'] or 0.0)
                            # code commented as it is plainly wrong - fields also hidden in view
                            # if res['price_min_margin']:
                            # price = max(price, price_limit+res['price_min_margin'])
                            # if res['price_max_margin']:
                            # price = min(price, price_limit+res['price_max_margin'])
                            break

                    else:
                        #  False means no valid line found ! But we may not raise an
                        #  exception here because it breaks the search
                        price = False

                if price and ('uom' in context) and (not uom_price_already_computed) and (
                        not context.get('already_computed', False)):
                    uom = products_dict[product_id].uos_id.id or products_dict[product_id].uom_id.id
                    price = product_uom_obj._compute_price(cr, uid, uom, price, context['uom'])

                if results.get(product_id):
                    results[product_id][pricelist_id] = price
                else:
                    results[product_id] = {pricelist_id: price}
        return results


class Productpricelistitem(orm.Model):
    """product pricelist item - little changes to enable m2m product_ids"""
    _inherit = 'product.pricelist.item'

    _columns = {
        'product_ids': fields.many2many(
            'product.product', 'pricelist_item_product_rel',
            'pricelist_item_id', 'prod_id', string="Products"),
        'tmpl_ids': fields.many2many(
            'product.template', 'pricelist_item_tmpl_rel',
            'pricelist_item_id', 'tmpl_id', string="Templates"),
    }

