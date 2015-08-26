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


class VoucherMatching(orm.Model):
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
        'partner_id': fields.related('name', 'partner_id', type='many2one',
                                     string='Partner'),
        'company_id': fields.related('name', 'company_id', type='many2one',
                                     string='Company'),
        'type': fields.selection([('receivable', 'Receivable'),
                                  ('payable', 'Payable')],
                                 string='Voucher Type'),
        'strategy': fields.selection(_get_strategy, 'Invoice Match Method'),
        'period_ids': fields.many2many('account.period', string='Periods'),
        'date_from': fields.date(string='Date From'),
        'date_to': fields.date(string='Date To'),
        'date_type': fields.selection([('original', 'Invoice Date'),
                                       ('due', 'Due Date')],
                                      string='Date Type'),
        'line_dr_ids': fields.related(
            'name', 'line_dr_ids', type='one2many', string='Debits'),
        'line_cr_ids': fields.related(
            'name', 'line_cr_ids', type='one2many', string='Credits'),
        'exclude_inv_ids': fields.many2many(
            'account.move.line', rel='voucher_match_excl_inv_ids',
            string='Exclude Invoices', id1='match_id', id2='invoice_id'),
        'inv_ids': fields.many2many(
            'account.move.line', string='Invoices to pay'),
        'refund_ids': fields.many2many(
            'account.move.line', string='Refunds to Take Up'),
        'amount_payment': fields.related('name', 'amount', type='float')
    }

    def default_get(self, cr, uid, fields_list, context=None):
        res = super(VoucherMatching, self).default_get(
            cr, uid, fields_list, context=context)
        if context is None:
            context={}
        if context.get('active_model') != 'account.voucher':
            raise orm.except_orm('Error',
                                 'Wizard must be run from voucher screen')
        voucher = self.pool['account.voucher'].browse(
            cr, uid, context['active_id'], context=context)
        res.update({'name': voucher.id, 'type': voucher.type})
        return res

    _defaults = {
        'date_type': 'original'
    }

    def onchange_strategy(self, cr, uid, ids, strategy, context=None):
        pass

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
        return [line for line in lines if line.move_line_id in wiz.inv_ids]


    def apply_strategy_and_close(self, cr, uid, ids, context=None):
        voucher_obj = self.pool['account.voucher']
        wiz = self.browse(cr, uid, ids, context=context)[0]
        vals_to_write = {'line_dr_ids': [], 'line_cr_ids': []}


        invoices, refunds = wiz.line_dr_ids, wiz.line_cr_ids
        invoice_vals, refund_vals = vals_to_write['line_dr_ids'], vals_to_write['line_cr_ids']
        if wiz.type == 'payable':
            invoices, refunds = refunds, invoices
            invoice_vals, refund_vals = refund_vals, invoice_vals
        filter_func = getattr(self, 'filter_inv_%s', wiz.strategy)
        invoices = filter_func(wiz, invoices)
        amount_remaining = wiz.amount_payment
        if wiz.refund_ids:
            refund_ids = [x.id for x in wiz.refund_ids]
            for refund in refunds:
                line_vals = {}
                if refund.move_line_id.id in refund_ids:
                    refund_vals.append(
                        (1, refund.id, {'reconcile': True,
                                        'amount': refund.amount_unreconciled}))
                    amount_remaining += refund.amount_unreconciled

        while amount_remaining:
            for inv in invoices:
                if inv.move_line_id not in wiz.exclude_inv_ids:
                    invoice_vals.append(
                        (1, inv.id, {
                            'reconcile': amount_remaining >= inv.amount_unreconciled,
                            'amount': min(amount_remaining, inv.amount_unreconciled)
                            }))
                    amount_remaining -= inv.amount_unreconciled
        voucher_obj.write(vals_to_write)
        return {}
