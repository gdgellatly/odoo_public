from openerp.osv import orm, fields
from openerp.addons.decimal_precision import decimal_precision as dp


class SaleQuoteSection(orm.Model):
    """Quote Section"""

    _name = 'sale.quote.section'
    _description = __doc__

    def _amount_section(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool['res.currency']
        res = {}
        for section in self.browse(cr, uid, ids, context=context):
            cur = section.order.pricelist_id.currency_id
            res[section.id] = section.order_lines and cur_obj.round(
                cr, uid, cur, sum([l.subtotal for l in section.order_lines])) or 0.00
        return res

    def _get_section(self, cr, uid, ids, context=None):
        result = dict.fromkeys(ids, False)
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            if line.layout:
                result[line.layout.id] = True
        return result.keys()

    _columns = {
        'name': fields.char('Section Title', required=True),
        'header_text': fields.text('Header Text'),
        'footer_text': fields.text('Footer Text'),
        'sequence': fields.integer('Seq'),
        'section_total': fields.boolean('Print Section Subtotal'),
        'order': fields.many2one('sale.order', 'Quote', auto_join=True),
        'order_lines': fields.one2many(
            'sale.order.line', 'layout', 'Order Lines', auto_join=True),
        'amount_subtotal': fields.function(
            _amount_section, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
            store={
                'sale.quote.section': (lambda self, cr, uid, ids, c={}: ids, ['order_lines'], 10),
                'sale.order.line': (_get_section, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },),
        #technical fields to overcome intermediate model
        'calc': fields.boolean('Calc'),
        'pricelist_id': fields.integer('pricelist_id'),
        'partner_id': fields.integer('partner_id'),
        'date_order': fields.date('date_order'),
        'fiscal_position': fields.integer('fiscal_position'),
        'shop_id': fields.integer('shop_id'),
        'order_id': fields.integer('order_id')
    }

    _defaults = {'sequence': 10,
                 'section_total': True}

    def set_fields(self, cr, uid, ids, context=None):
        """
        This onchange just assists setting fields from the parent
        model.

        If using
        web_context_tunnel inheriting the view and updating
        context will allow you to set any additional fields
        :param cr:
        :param uid:
        :param ids:
        :param context:
        :return: dict of values
        """
        if not context:
            return {}
        return {'value': context}

    def write(self, cr, user, ids, vals, context=None):
        if context is None:
            context = {}
        context.update({'layout': 'write'})
        return super(SaleQuoteSection, self).write(cr, user, ids, vals, context=context)

    def create(self, cr, user, vals, context=None):
        if context is None:
            context = {}
        context.update({'layout': 'create'})
        return super(SaleQuoteSection, self).write(cr, user, vals, context=context)


class SaleOrder(orm.Model):
    _inherit = 'sale.order'

    _columns = {
        'layouts': fields.one2many(
            'sale.quote.section', 'order', string='Section', auto_join=True),
        'quote_footer': fields.text('Quote Tags'),
        'use_sections': fields.boolean('Multi Part Quote')
        }

    def convert_quote_to_order(self, cr, uid, ids, context=None):
        return True


class SaleOrderLine(orm.Model):
    _inherit = 'sale.order.line'

    _columns = {
        'layout': fields.many2one('sale.quote.section', 'Section', auto_join=True)}

    _order = 'layout, sequence asc'

    def set_fields(self, cr, uid, ids, context=None):
        """
        This onchange just assists setting fields from the parent
        model.

        If using
        web_context_tunnel inheriting the view and updating
        context will allow you to set any additional fields
        :param cr:
        :param uid:
        :param ids:
        :param context:
        :return: dict of values
        """
        if not context:
            return {}
        return {'value': context}

    def write(self, cr, user, ids, vals, context=None):
        print context
        return super(SaleOrderLine, self).write(cr, user, ids, vals, context=context)

    def create(self, cr, user, vals, context=None):
        print context
        return super(SaleOrderLine, self).create(cr, user, vals, context=None)
