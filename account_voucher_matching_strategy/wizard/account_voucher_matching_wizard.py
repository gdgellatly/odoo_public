# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP / Odoo, Open Source Management Solution - module extension
#    Copyright (C) 2014- O4SB (<http://openforsmallbusiness.co.nz>).
#    Author Graeme Gellatly <g@o4sb.com>
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

from openerp.osv import orm, fields
from openerp.tools import float_compare, float_round


class VoucherMatching(orm.TransientModel):
    """Voucher Matching Wizard"""
    _name = 'voucher.matching.wizard'
    _description = __doc__

    def _get_strategy(self, cr, uid, context=None):
        return [('default', 'Off the back'),
                ('period', 'Paying certain periods'),
                ('date', 'Between two dates'),
                ('selected', 'Selected Invoices')]


    _columns = {
        'name': fields.many2one('account.voucher', 'Name'),
        'partner_id': fields.many2one('res.partner', string='Partner'),
        'company_id': fields.many2one('res.company', type='many2one',
                                      string='Company'),
        'type': fields.selection([('receipt', 'Receivable'),
                                  ('payment', 'Payable')],
                                 string='Voucher Type'),
        'strategy': fields.selection(
            _get_strategy, 'Invoice Match Method', required=True),
        'no_partial': fields.boolean(string='No Part Payments'),
        'period_ids': fields.many2many('account.period', string='Periods'),
        'date_from': fields.date(string='Date From'),
        'date_to': fields.date(string='Date To'),
        'date_type': fields.selection([('original', 'Invoice Date'),
                                       ('due', 'Due Date')],
                                      string='Date Type'),
        'exclude_inv_ids': fields.many2many(
            'account.voucher.line', rel='voucher_match_excl_inv_ids',
            string='Exclude Invoices', id1='match_id', id2='invoice_id'),
        'inv_ids': fields.many2many(
            'account.voucher.line', string='Invoices to pay'),
        'refund_ids': fields.many2many(
            'account.voucher.line', string='Refunds to Take Up',
            rel='voucher_match_refund_ids'),
        'amount_payment': fields.float(string="Amount")
    }

    def default_get(self, cr, uid, fields_list, context=None):
        res = super(VoucherMatching, self).default_get(
            cr, uid, fields_list, context=context)
        if context is None:
            context = {}
        if context.get('active_model') != 'account.voucher':
            raise orm.except_orm('Error',
                                 'Wizard must be run from voucher screen')
        voucher = self.pool['account.voucher'].browse(
            cr, uid, context['active_id'], context=context)
        res.update({'name': voucher.id,
                    'partner_id': voucher.partner_id.id,
                    'company_id': voucher.company_id.id,
                    'type': voucher.type,
                    'amount_payment': voucher.amount})
        return res

    _defaults = {
        'date_type': 'original',
        'no_partial': True
    }

    def onchange_strategy(self, cr, uid, ids, strategy, context=None):
        pass

    def onchange_date(self, cr, uid, ids, date_type, date_from, date_to,
                      context=None):
        if date_type == 'due' and not date_to:
            return {'value': {'date_to': date_from}}
        return {}

    def action_add_refunds(self, cr, uid, ids, context=None):
        for wiz in self.browse(cr, uid, ids, context=context):
            if wiz.type == 'receivable':
                lines = [x.id for x in wiz.line_cr_ids]
            else:
                lines = [x.id for x in wiz.line_dr_ids]
            wiz.write({'refund_ids': [(6, 0, lines)]})
        return {}

    def action_remove_refunds(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'refund_ids': [(5,)]})
        return {}

    def filter_inv_default(self, wiz, lines):
        return lines

    def filter_inv_date(self, wiz, lines):
        field = 'date_%s' % wiz.date_type
        return [line for line in lines
                if wiz.date_from <= line[field] <= wiz.date_to]

    def filter_inv_period(self, wiz, lines):
        return [line for line in lines
                if line.move_line_id.period_id in wiz.period_ids]

    def filter_inv_selected(self, wiz, lines):
        return [line for line in lines if line in wiz.inv_ids]

    def apply_strategy_and_close(self, cr, uid, ids, context=None):
        voucher_line_obj = self.pool['account.voucher.line']
        wiz = self.browse(cr, uid, ids, context=context)[0]

        invoices, refunds = wiz.name.line_cr_ids, wiz.name.line_dr_ids
        voucher_line_ids = set([x.id for x in invoices + refunds])
        line_vals = {}
        if wiz.type == 'payment':
            invoices, refunds = refunds, invoices

        filter_func = getattr(self, 'filter_inv_%s' % wiz.strategy)
        invoices = filter_func(wiz, invoices)
        amount_remaining = wiz.amount_payment

        if wiz.refund_ids:
            for refund in refunds:
                if refund in wiz.refund_ids:
                    line_vals[refund.id] = {
                        'reconcile': True,
                        'amount': refund.amount_unreconciled}
                    amount_remaining += refund.amount_unreconciled

        for inv in invoices:
            if inv not in wiz.exclude_inv_ids:
                if amount_remaining < inv.amount_unreconciled and wiz.no_partial:
                    break
                line_vals[inv.id] = {
                    'reconcile': amount_remaining >= inv.amount_unreconciled,
                    'amount': min(amount_remaining, inv.amount_unreconciled)
                    }
                amount_remaining -= min(amount_remaining, inv.amount_unreconciled)
            if not amount_remaining:
                break

        voucher_line_ids = list(voucher_line_ids.difference(line_vals.keys()))
        voucher_line_obj.write(cr, uid, voucher_line_ids,
                               {'reconcile': False, 'amount': 0.0})
        for pk, vals in line_vals.iteritems():
            voucher_line_obj.write(cr, uid, pk, vals, context=context)
        wiz.name.write({'no_recompute': True})

        return {'type': 'ir.actions.act_window_close'}


class AccountVoucher(orm.Model):
    _inherit = 'account.voucher'

    _columns = {'no_recompute': fields.boolean('Don\'t Reload Lines'),
                'delete_unpaid': fields.boolean('Remove Unpaid lines')}

    _defaults = {'no_recompute': False,
                 'delete_unpaid': True}

    def recompute_voucher_lines(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):
        if ids:
            voucher = self.browse(cr, uid, ids, context=context)[0]
            if voucher.no_recompute:
                default = {'value': {}}
                default['value']['writeoff_amount'] = self._compute_writeoff_amount(
                    cr, uid, voucher.line_dr_ids, voucher.line_cr_ids, price, ttype)
                return default
        default = super(AccountVoucher, self).recompute_voucher_lines(
            cr, uid, ids, partner_id, journal_id, price, currency_id,
            ttype, date, context=context)
        return default

    def voucher_move_line_create(self, cr, uid, voucher_id, line_total,
                                 move_id, company_currency, current_currency,
                                 context=None):
        voucher_line_obj = self.pool['account.voucher.line']

        voucher = self.browse(cr, uid, voucher_id, context=context)
        if voucher.delete_unpaid:
            lines_to_delete = voucher_line_obj.search(
                cr, uid, [('voucher_id', '=', voucher_id),
                          ('amount', '=', 0.0),
                          ('reconcile', '=', False)])
            if lines_to_delete:
                voucher_line_obj.unlink(cr, uid, lines_to_delete)
        return super(AccountVoucher, self).voucher_move_line_create(
            cr, uid, voucher_id, line_total, move_id, company_currency,
            current_currency, context=context)


