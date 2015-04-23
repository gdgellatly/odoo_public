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
"""Implements central billing for Openerp by changing the partner at invoice time"""

from openerp.osv import orm, fields
from openerp.tools.translate import _


class ResPartner(orm.Model):
    """inherit base.res_partner and add columns to allow central invoicing"""
    _inherit = 'res.partner'

    _columns = {
        'central_inv': fields.boolean(
            'Central Billing', help='When enabled invoices for subsidiaries'
                                    'will be billed to the parent account'),
        'store_ref': fields.char(
            'Store Code', size=16, help='If the customer requires specific store '
                                        'references on documentation'),
        'central_supplier_inv': fields.boolean(
            'Central Supplier', help='When enabled supplier invoices for subsidiaries'
                                     'will be from the Billing Supplier'),
        'hq_partner_id': fields.many2one('res.partner', 'Billing Supplier')
    }

    def copy(self, cr, uid, id, defaults=None, context=None):
        """due to duplicate constraint we must set store_ref to False when
        copying:
        @return: the copied object"""
        defaults.update({'store_ref': False})
        return super(ResPartner, self).copy(cr, uid, id, defaults, context)

    def _check_store_code(self, cr, uid, ids, context=None):
        """This function checks that the store code is unique within 
        the account hierarchy it belongs"""
        partner_obj = self.pool['res.partner']
        partner = partner_obj.browse(cr, uid, ids[0], context)
        if partner.store_ref:
            if partner.parent_id:
                group_partners = partner_obj.search(cr, uid,
                                                    [('id', 'child_of', [partner.parent_id.id])])
            else:
                group_partners = partner_obj.search(cr, uid, [('id', 'child_of', [partner.id])])
            group_partners = list(set(group_partners) - {ids[0]})
            if group_partners:
                for part in partner_obj.browse(cr, uid, group_partners, context):
                    if part.store_ref and part.store_ref == partner.store_ref:
                        return False
        return True

    _constraints = [
        (_check_store_code, _('Store Codes must be unique per group'), ['store_ref']),
    ]


class AccountInvoice(orm.Model):
    """inherits account.account_invoice and adds the order_partner_id field
    as well as overriding ORM functions to ensure the parent partner and order partner
    are written and created correctly"""
    _inherit = 'account.invoice'
    _columns = {
        'order_partner_id': fields.many2one('res.partner', 'Ordering Partner',
                                            required=False, readonly=True),
    }

    def create(self, cr, uid, vals, context=None):
        """Function overrides create to ensure that parent account is always used"""
        if (vals.get('partner_id', False) and
                vals.get('type', False) not in ['in_invoice', 'in_refund']):
            partner_obj = self.pool['res.partner']
            partner = partner_obj.browse(cr, uid, vals['partner_id'], context=context)
            if partner.parent_id and partner.parent_id.central_inv:
                vals.update({'partner_id': partner.parent_id.id,
                             'order_partner_id': partner.id})
        elif (vals.get('partner_id', False) and
                vals.get('type', False) not in ['out_invoice', 'out_refund']):
            partner_obj = self.pool['res.partner']
            partner = partner_obj.browse(cr, uid, vals['partner_id'], context=context)
            if partner.hq_partner_id and partner.central_supplier_inv:
                comp_id = self.pool.get('res.users').browse(
                    cr, uid, uid).company_id.partner_id.id
                if partner.hq_partner_id.id != comp_id:
                    vals.update({'partner_id': partner.hq_partner_id.id,
                                 'order_partner_id': partner.id})
        return super(AccountInvoice, self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        """Function overrides create to ensure that parent account is always used"""
        if vals.get('partner_id', False):
            partner_obj = self.pool.get('res.partner')
            partner = partner_obj.browse(cr, uid, vals['partner_id'], context=context)
            if partner.parent_id and partner.parent_id.central_inv:
                new_vals_to_write = vals.copy()
                new_vals_to_write.update({'partner_id': partner.parent_id.id,
                                          'order_partner_id': partner.id})
                new_ids_to_write = [inv.id for inv in self.browse(cr, uid, ids, context)
                                    if inv.type in ['out_invoice', 'out_refund']]
                if new_ids_to_write:
                    self.write(cr, uid, new_ids_to_write, new_vals_to_write, context)
                    ids = [x for x in ids if x not in new_ids_to_write]
            elif partner.hq_partner_id and partner.central_supplier_inv:
                comp_id = self.pool.get('res.users').browse(
                    cr, uid, uid).company_id.partner_id.id
                if partner.hq_partner_id.id != comp_id:
                    new_vals_to_write = vals.copy()
                    new_vals_to_write.update({'partner_id': partner.hq_partner_id.id,
                                              'order_partner_id': partner.id})
                    new_ids_to_write = [inv.id for inv in self.browse(cr, uid, ids, context)
                                        if inv.type in ['in_invoice', 'in_refund']]
                    if new_ids_to_write:
                        self.write(cr, uid, new_ids_to_write, new_vals_to_write, context)
                        ids = [x for x in ids if x not in new_ids_to_write]
        if ids:
            return super(AccountInvoice, self).write(cr, uid, ids, vals, context)
        return True

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        """override search so we find subsidiary invoices when looking at that partner
        @note: this could break quite easily if used with multiple custom filters"""
        for search_args in args:
            if search_args[0] == 'partner_id' and search_args[1] in ['=', 'like', 'ilike']:
                args.remove(search_args)
                args.extend(['|', search_args,
                             ('order_partner_id', search_args[1], search_args[2])])
                break
        return super(AccountInvoice, self).search(cr, uid, args, offset, limit=limit,
                                                  order=order, context=context, count=False)

    def refund(self, cr, uid, ids, date=None, period_id=None, description=None, journal_id=None, context=None):
        """overide refund to make sure we preserve the original ordering partner, also we
        update the credit not to display the invoice in the origin and the comments.  To work
        either the refunds must be for a single original order partner or all order partners. In
        practice this is not an issue as the wizard only works on a single id, but at least
        this way we are covered if that changes."""
        order_partner_ids = set([x.order_partner_id and x.order_partner_id.id or False
                                 for x in self.browse(cr, uid, ids)])
        if len(order_partner_ids) != 1:
            raise orm.except_orm(_('Error:'),
                                 _('May only refund centrally billed invoices for one store at a time'))
        new_ids = super(AccountInvoice, self).refund(cr, uid, ids, date, period_id,
                                                     description, journal_id, context=context)
        vals_to_write = {'order_partner_id': list(order_partner_ids)[0]}
        if len(ids) == 1:
            inv_num = self.pool.get('account.invoice').browse(cr, uid, ids)[0].number
            vals_to_write.update({'comment': 'Credit Raised against Invoice %s' % inv_num,
                                  'origin': inv_num})
        self.write(cr, uid, new_ids, vals_to_write, context=context)
        return new_ids


class AccountInvoiceRefund(orm.TransientModel):
    _inherit = 'account.invoice.refund'

    def invoice_refund(self, cr, uid, ids, context=None):
        """All this horrible shit just so we can call super, inefficient
        but don't blame me, parent module needs refactoring!!! In essence
        we parse the return domain for active ids (which is broken anyway)
        and add comments and origins to the invoice.
        @return: returns a view object being the credit note created"""
        res = super(AccountInvoiceRefund, self).invoice_refund(cr, uid, ids, context=context)
        inv_obj = self.pool['account.invoice']
        if (self.read(cr, uid, ids, [], context)[0]['filter_refund'] == 'modify' and
                len(context.get('active_ids')) == 1):
            for args in res['domain']:
                if args[0] == 'id':
                    inv = inv_obj.browse(cr, uid, args[2])[0]
                    if inv.type == 'out_invoice':
                        orig_inv = inv_obj.browse(cr, uid, context.get('active_ids'))[0]
                        inv.write({'comment': 'Original Invoice %s\n%s' % (orig_inv.number, orig_inv.comment or ''),
                                   'order_partner_id': orig_inv.order_partner_id.id,
                                   'origin': orig_inv.number})
                        break
                    break
        return res

