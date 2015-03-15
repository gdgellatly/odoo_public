# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 NovaPoint Group LLC (<http://www.novapointgroup.com>)
#    Copyright (C) 2004-2010 OpenERP SA (<http://www.openerp.com>)
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################
import time

from openerp.osv import fields, orm
from openerp.tools.translate import _
from openerp.addons.decimal_precision import get_precision as dp

try:
    from toolz.curried import *
except ImportError:
    from toolz.itertoolz import reduceby, groupby, map, filter, filterfalse, pluck
    from toolz.functoolz import pipe, juxt, compose, complement
    from toolz.dicttoolz import valmap, get_in


class BankAccRecStatement(orm.Model):
    def check_group(self, cr, uid, ids, context=None):
        """Check if following security constraints are implemented for groups:
        Bank Statement Preparer– they can create, view and delete any of
        the Bank Statements provided the Bank Statement is not in the
        DONE state, or the Ready for Review state.
        Bank Statement Verifier – they can create, view, edit, and delete
        any of the Bank Statements information at any time.
        NOTE: DONE Bank Statements  are only allowed to be deleted by a
        Bank Statement Verifier."""
        model_data_obj = self.pool['ir.model.data']
        res_groups_obj = self.pool['res.groups']
        group_verifier_id = model_data_obj._get_id(
            cr, uid, 'bank_account_reconciliation',
            'group_bank_stmt_verifier')
        for statement in self.browse(cr, uid, ids, context=context):
            if group_verifier_id:
                res_id = model_data_obj.read(
                    cr, uid, [group_verifier_id], ['res_id'])[0]['res_id']
                group_verifier = res_groups_obj.browse(
                    cr, uid, res_id, context=context)
                group_user_ids = [user.id for user in group_verifier.users]
                if statement.state != 'draft' and uid not in group_user_ids:
                    raise orm.except_orm(
                        _('User Error !'),
                        _("Only a member of '%s' group may "
                          "delete/edit bank statements "
                          "when not in draft state!" % group_verifier.name))
        return True

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default.update({
            'credit_move_line_ids': [],
            'debit_move_line_ids': [],
            'name': '',
        })
        return super(BankAccRecStatement, self).copy(
            cr, uid, id, default=default, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        self.check_group(cr, uid, ids, context)
        return super(BankAccRecStatement, self).write(
            cr, uid, ids, vals, context=context)

    def create(self, cr, user, vals, context=None):
        def compact(line_ids):
            return filter(None, line_ids)
        if context is None:
            context = {}
        if vals.get('credit_move_line_ids') or vals.get('debit_move_line_ids'):
            move_line_ids = pipe(
                vals.get('credit_move_line_ids', []) +
                vals.get('debit_move_line_ids', []),
                pluck(2), compact, pluck('move_line_id'), compact, list)

            if move_line_ids:
                self.pool['account.move.line'].write(
                    cr, user, move_line_ids,
                    {'draft_assigned_to_statement': True}, context=context)
                context.update(move_written=True)
        return super(BankAccRecStatement, self).create(
            cr, user, vals, context=context)


    def check_difference_balance(self, cr, uid, ids, context=None):
        """Check if difference balance is zero or not."""
        for statement in self.browse(cr, uid, ids, context=context):
            if statement.difference != 0.0:
                raise orm.except_orm(
                    _('Warning!'),
                    _("Prior to reconciling a statement, all differences must "
                      "be accounted for and the Difference balance must be "
                      "zero. Please review and make necessary changes."))
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        """Cancel the the statement."""
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True

    def action_review(self, cr, uid, ids, context=None):
        """Change the status of statement from 'draft' to 'to_be_reviewed'."""
        # If difference balance not zero prevent further processing
        self.check_difference_balance(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'state': 'to_be_reviewed'}, context=context)
        return True

    def action_process(self, cr, uid, ids, context=None):
        """Set the account move lines as 'Cleared' and
        Assign 'Bank Acc Rec Statement ID'
        for the statement lines which are marked as 'Cleared'."""
        aml_obj = self.pool['account.move.line']
        # If difference balance not zero prevent further processing
        self.check_difference_balance(cr, uid, ids, context=context)

        cleared = lambda l: l.cleared_bank_account and 'Cleared' or 'Uncleared'
        has_move = lambda l: l.move_line_id and True or False
        move_id = lambda res: [l.move_line_id.id for l in res]
        process_lines = compose(valmap(move_id),
                                groupby(cleared),
                                filter(has_move))

        for stmt in self.browse(cr, uid, ids, context=context):
            statement_lines = process_lines(stmt.credit_move_line_ids +
                                            stmt.debit_move_line_ids)
            if statement_lines.get('Cleared'):
                aml_obj.write(
                    cr, uid,
                    statement_lines['Cleared'],
                    {'cleared_bank_account': True,
                     'bank_acc_rec_statement_id': stmt.id},
                    context=context)
            if statement_lines.get('Uncleared'):
                aml_obj.write(
                    cr, uid,
                    statement_lines['Uncleared'],
                    {'cleared_bank_account': False,
                     'bank_acc_rec_statement_id': False},
                    context=context)
            self.write(cr, uid, [stmt.id],
                       {'state': 'done',
                        'verified_by_user_id': uid,
                        'verified_date': fields.date.context_today(
                            self, cr, uid, context=context)
                        }, context=context)
        return True

    def action_cancel_draft(self, cr, uid, ids, context=None):
        """Reset the statement to draft and perform resetting operations."""
        aml_obj = self.pool['account.move.line']
        stmt_line_obj = self.pool['bank.acc.rec.statement.line']
        for stmt in self.browse(cr, uid, ids, context=context):
            stmt_lines = stmt.credit_move_line_ids + stmt.debit_move_line_ids
            line_ids = []
            stmt_line_ids = []
            for stmt_line in stmt_lines:
                stmt_line_ids.append(stmt_line.id)
                if stmt_line.move_line_id:
                    line_ids.append(stmt_line.move_line_id.id)

            # Reset 'Cleared' and 'Bank Acc Rec Statement ID' to False
            aml_obj.write(cr, uid, line_ids,
                          {'cleared_bank_account': False,
                           'bank_acc_rec_statement_id': False,
                           }, context=context)
            # Reset 'Cleared' in statement lines
            stmt_line_obj.write(cr, uid, stmt_line_ids,
                                {'cleared_bank_account': False,
                                 'research_required': False
                                 }, context=context)
            # Reset statement
            self.write(cr, uid, [stmt.id], {'state': 'draft',
                                            'verified_by_user_id': False,
                                            'verified_date': False
                                            }, context=context)

        return True

    def _write_all_lines(self, cr, uid, ids, vals_to_write, context=None):
        stmt_line_obj = self.pool['bank.acc.rec.statement.line']
        for stmt in self.browse(cr, uid, ids, context=context):
            stmt_line_ids = map(lambda x: x.id,
                                stmt.credit_move_line_ids +
                                stmt.debit_move_line_ids)
            stmt_line_obj.write(
                cr, uid, stmt_line_ids, vals_to_write, context=context)
        return True

    def action_select_all(self, cr, uid, ids, context=None):
        """Mark all the statement lines as 'Cleared'."""
        return self._write_all_lines(
            cr, uid, ids, {'cleared_bank_account': True}, context=context)

    def action_unselect_all(self, cr, uid, ids, context=None):
        """Reset 'Cleared' in all the statement lines."""
        return self._write_all_lines(
            cr, uid, ids, {'cleared_bank_account': False}, context=context)

    def _get_balance(self, cr, uid, ids, name, args, context=None):
        """Computed as following:
        A) Cleared Deposits, Credits, and Interest Amount: SUM of Amts of lines
           Cleared Deposits, Credits, and Interest # of Items: Number of lines

        B) Checks, Withdrawals, Debits, and Service Charges Amount:
           Checks, Withdrawals, Debits, and Service Charges Amount # of Items:

        Cleared Balance:
            (Total Sum of the Deposit Amount Cleared (A) –
             Total Sum of Checks Amount Cleared (B))
        Difference=
            (Ending Balance – Beginning Balance) - cleared balance
            should be zero.
        """
        res = {}
        account_precision = self.pool['decimal.precision'].precision_get(
            cr, uid, 'Account')
        for stmt in self.browse(cr, uid, ids, context=context):
            res[stmt.id] = {}
            cleared = lambda l: l.cleared_bank_account and 'Cleared' or 'Uncleared'
            get_amount = lambda l: [round(v.amount, account_precision) for v in l]
            process_lines = compose(valmap(get_amount), groupby(cleared))

            for line_type in ('debit', 'credit'):
                r = process_lines(eval('stmt.%s_move_line_ids' % line_type))
                res[stmt.id].update({
                    'sum_of_%ss' % line_type:
                        sum(r.get('Cleared', [])),
                    'sum_of_%ss_lines' % line_type:
                        len(r.get('Cleared', [])),
                    'sum_of_%ss_unclear' % line_type:
                        sum(r.get('Uncleared', [])),
                    'sum_of_%ss_lines_unclear' % line_type:
                        len(r.get('Uncleared', []))
                })

            res[stmt.id]['cleared_balance'] = round(
                res[stmt.id]['sum_of_debits'] - res[stmt.id]['sum_of_credits'],
                account_precision)
            res[stmt.id]['uncleared_balance'] = round(
                res[stmt.id]['sum_of_debits_unclear'] -
                res[stmt.id]['sum_of_credits_unclear'], account_precision)
            res[stmt.id]['difference'] = round(
                (stmt.ending_balance - stmt.starting_balance) -
                res[stmt.id]['cleared_balance'], account_precision)
        return res

    def _get_move_line_write(self, line):
        return {
            'ref': line.ref,
            'date': line.date,
            'partner_id': line.partner_id.id,
            'currency_id': line.currency_id.id,
            'amount': line.credit or line.debit,
            'name': line.name,
            'move_line_id': line.id,
            'type': line.credit and 'cr' or 'dr',
            'amount_in_currency': (line.credit and 
                                   -1 or 1) * line.amount_currency
        }

    def refresh_record(self, cr, uid, ids, context=None):
        account_move_line_obj = self.pool["account.move.line"]
        # is_credit = lambda x: (x.credit and 'credit_move_line_ids' or
        #                        'debit_move_line_ids')

        for obj in self.browse(cr, uid, ids, context=context):
            if not obj.account_id:
                continue

            to_write = {'credit_move_line_ids': [], 'debit_move_line_ids': []}
            move_line_ids = [
                line.move_line_id.id
                for line in obj.credit_move_line_ids + obj.debit_move_line_ids
                if line.move_line_id
            ]

            domain = [
                ('id', 'not in', move_line_ids),
                ('account_id', '=', obj.account_id.id),
                ('move_id.state', '=', 'posted'),
                ('cleared_bank_account', '=', False),
            ]

            # if not keep_previous_uncleared_entries:
            #     domain += [('draft_assigned_to_statement', '=', False)]

            if not obj.suppress_ending_date_filter:
                domain += [('date', '<=', obj.ending_date)]
            line_ids = account_move_line_obj.search(cr, uid, domain,
                                                    context=context)
            for line in account_move_line_obj.browse(cr, uid, line_ids,
                                                     context=context):
                if obj.keep_previous_uncleared_entries:
                    # only take bank_acc_rec_statement at state cancel or done
                    if not self.is_stmt_done(cr, uid, line,
                                             context=context):
                        continue
                res = (0, 0, self._get_move_line_write(line))
                if line.credit:
                    to_write['credit_move_line_ids'].append(res)
                else:
                    to_write['debit_move_line_ids'].append(res)
                obj.write(to_write)

        return True

    def is_stmt_done(self, cr, uid, move_line_id, context=None):
        stmt_line_obj = self.pool['bank.acc.rec.statement.line']
        stmt_line_ids = stmt_line_obj.search(
            cr, uid, [('move_line_id', '=', move_line_id.id)], context=context)
        for stmt_line in stmt_line_obj.browse(
                cr, uid, stmt_line_ids, context=context):
            stmt = stmt_line.statement_id
            if stmt and stmt.state not in ("done", "cancel"):
                return False
        return True

    def onchange_account_id(self, cr, uid, ids, account_id, ending_date,
                            suppress_ending_date_filter,
                            keep_previous_uncleared_entries, context=None):
        aml_obj = self.pool['account.move.line']
        stmt_line_obj = self.pool['bank.acc.rec.statement.line']
        val = {'value': {'credit_move_line_ids': [],
                         'debit_move_line_ids': []}}
        if not account_id:
            return val
        for statement in self.browse(cr, uid, ids, context=context):
            cr.execute('''
UPDATE account_move_line
SET draft_assigned_to_statement=False,
    cleared_bank_account=False,
    bank_acc_rec_statement_id=NULL
WHERE bank_acc_rec_statement_id=%s''', (statement.id,))
            cr.execute('''
DELETE FROM bank_acc_rec_statement_line
WHERE statement_id=%s''', (statement.id,))

        # Apply filter on move lines to allow
        # 1. credit and debit side journal items in posted
        #    state of the selected GL account
        # 2. Journal items which are not assigned to
        #    previous bank statements
        # 3. Date less than or equal to ending date provided the
        #    'Suppress Ending Date Filter' is not checked
        # get previous uncleared entries
        domain = [('account_id', '=', account_id),
                  ('move_id.state', '=', 'posted'),
                  ('cleared_bank_account', '=', False)]
        if not keep_previous_uncleared_entries:
            domain += [('draft_assigned_to_statement', '=', False)]

        if not suppress_ending_date_filter:
            domain += [('date', '<=', ending_date)]

        if keep_previous_uncleared_entries:
            keep = curry(self.is_stmt_done, cr, uid, context=context)
        else:
            keep = lambda x: True

        aml_search = curry(aml_obj.search, cr, uid, context=context)
        aml_browse = curry(aml_obj.browse, cr, uid, context=context)
        is_credit = (lambda l: '%s_move_line_ids' % (l['type'] == 'cr' and 'credit' or 'debit'))

        val['value'].update(
            pipe(domain, aml_search, aml_browse, filter(keep),
                 map(self._get_move_line_write), groupby(is_credit)))

        return val

    _name = "bank.acc.rec.statement"
    _columns = {
        'name': fields.char(
            'Name', required=True, size=64, 
            states={'done': [('readonly', True)]}, 
            help="This is a unique name identifying the statement "
                 "(e.g. Bank X January 2012)."),
        'account_id': fields.many2one(
            'account.account', 'Account', required=True,
            states={'done': [('readonly', True)]},
            domain="[('company_id', '=', company_id), ('type', '!=', 'view')]",
            help="The Bank/Gl Account that is being reconciled."),
        'ending_date': fields.date(
            'Ending Date', required=True,
            states={'done': [('readonly', True)]},
            help="The ending date of your bank statement."),
        'starting_balance': fields.float(
            'Starting Balance', required=True, 
            digits_compute=dp('Account'), 
            help="The Starting Balance on your bank statement.", 
            states={'done': [('readonly', True)]}),
        'ending_balance': fields.float(
            'Ending Balance', required=True, 
            digits_compute=dp('Account'), 
            help="The Ending Balance on your bank statement.", 
            states={'done': [('readonly', True)]}),
        'company_id': fields.many2one(
            'res.company', 'Company', required=True, readonly=True,
            help="The Company for which the deposit ticket is made to"),
        'notes': fields.text('Notes'),
        'verified_date': fields.date(
            'Verified Date', states={'done': [('readonly', True)]},
            help="Date in which Deposit Ticket was verified."),
        'verified_by_user_id': fields.many2one(
            'res.users', 'Verified By', states={'done': [('readonly', True)]},
            help="Entered automatically by the “last user” who saved it. "
                 "System generated."),
        'credit_move_line_ids': fields.one2many(
            'bank.acc.rec.statement.line', 'statement_id', 'Credits',
            domain=[('type', '=', 'cr')], context={'default_type': 'cr'}, 
            states={'done': [('readonly', True)]}),
        'debit_move_line_ids': fields.one2many(
            'bank.acc.rec.statement.line', 'statement_id', 'Debits',
            domain=[('type', '=', 'dr')], context={'default_type': 'dr'}, 
            states={'done': [('readonly', True)]}),
        'cleared_balance': fields.function(
            _get_balance, string='Cleared Balance', multi="balance",
            digits_compute=dp('Account'), type='float', 
            help="Total Sum of the Deposit Amount Cleared – "
                 "Total Sum of Checks, Withdrawals, Debits, and "
                 "Service Charges Amount Cleared"),
        'difference': fields.function(
            _get_balance, type='float', string='Difference', multi="balance",
            digits_compute=dp('Account'),
            help="(Ending Balance – Beginning Balance) - Cleared Balance."),
        'sum_of_credits': fields.function(
            _get_balance, string='Checks, Withdrawals, Debits, and '
                                 'Service Charges Amount', 
            digits_compute=dp('Account'), type='float', multi="balance",
            help="Total SUM of Amts of lines with Cleared = True"),
        'sum_of_debits': fields.function(
            _get_balance, type='float', digits_compute=dp('Account'),
            string='Deposits, Credits, and Interest Amount', 
            help="Total SUM of Amts of lines with Cleared = True",
            multi="balance"),
        'sum_of_credits_lines': fields.function(
            _get_balance,
            string='Checks, Withdrawals, Debits, and Service Charges '
                   '# of Items',
            type='integer', help="Total of number of lines with Cleared = True",
            multi="balance"),
        'sum_of_debits_lines': fields.function(
            _get_balance, type='integer',
            string='Deposits, Credits, and Interest # of Items',
            help="Total of number of lines with Cleared = True",
            multi="balance"),
        'uncleared_balance': fields.function(
            _get_balance, string='Uncleared Balance',
            digits_compute=dp('Account'), type='float',
            help="Total Sum of the Deposit Amount Cleared – "
                 "Total Sum of Checks, Withdrawals, Debits, and "
                 "Service Charges Amount Cleared",
            multi="balance"),
        'sum_of_credits_unclear': fields.function(
            _get_balance,
            string='Checks, Withdrawals, Debits, and Service Charges Amount',
            digits_compute=dp('Account'), type='float',
            help="Total SUM of Amts of lines with Cleared = True",
            multi="balance"),
        'sum_of_debits_unclear': fields.function(
            _get_balance, type='float',
            string='Deposits, Credits, and Interest Amount',
            digits_compute=dp('Account'),
            help="Total SUM of Amts of lines with Cleared = True",
            multi="balance"),
        'sum_of_credits_lines_unclear': fields.function(
            _get_balance, type='integer', multi="balance",
            string='Checks, Withdrawals, Debits, and Service Charges '
                   '# of Items',
            help="Total of number of lines with Cleared = True"),
        'sum_of_debits_lines_unclear': fields.function(
            _get_balance, type='integer', multi="balance",
            string='Deposits, Credits, and Interest # of Items',
            help="Total of number of lines with Cleared = True"),
        'suppress_ending_date_filter': fields.boolean(
            'Remove Ending Date Filter', 
            help="If this is checked then the Statement End Date filter on "
                 "the transactions below will not occur. All transactions "
                 "would come over."),
        'keep_previous_uncleared_entries': fields.boolean(
            'Keep Previous Uncleared Entries', 
            help="If this is checked then the previous uncleared entries "
                 "will be included."),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('to_be_reviewed', 'Ready for Review'),
            ('done', 'Done'),
            ('cancel', 'Cancel')
            ], 'State', select=True, readonly=True),
    }
    
    _defaults = {
        'state': 'draft',
        'company_id': lambda s, c, u, x: s.pool['res.users'].browse(
            c, u, u, x).company_id.id,
        'ending_date': fields.date.context_today,
        'keep_previous_uncleared_entries': True
    }
    
    _order = "ending_date desc"
    _sql_constraints = [
        ('name_company_uniq', 'unique (name, company_id, account_id)', 
         'The name of the statement must be unique per '
         'company and G/L account!')
    ]


class BankAccRecStatementLine(orm.Model):
    _name = "bank.acc.rec.statement.line"
    _description = "Statement Line"
    _columns = {
        'name': fields.char(
            'Name', size=64, help="Derived from the related Journal Item.",
            required=True),
        'ref': fields.char(
            'Reference', size=64, help="Derived from related Journal Item."),
        'partner_id': fields.many2one(
            'res.partner', string='Partner',
            help="Derived from related Journal Item."),
        'amount': fields.float(
            'Amount', digits_compute=dp('Account'),
            help="Derived from the 'debit' amount from related Journal Item."),
        'amount_in_currency': fields.float(
            'Amount in Currency', digits_compute=dp('Account'),
            help="Amount in currency from the related Journal Item."),
        'date': fields.date(
            'Date', required=True, help="Derived from related Journal Item."),
        'statement_id': fields.many2one(
            'bank.acc.rec.statement', 'Statement', required=True,
            ondelete='cascade'),
        'move_line_id': fields.many2one(
            'account.move.line', 'Journal Item', required=True,
            help="Related Journal Item.", ondelete='cascade'),
        'cleared_bank_account': fields.boolean(
            'Cleared? ',
            help='Check if the transaction has cleared from the bank'),
        'research_required': fields.boolean(
            'Research Required? ',
            help='Check if the transaction should be researched'
                 ' by Accounting personnel'),
        'currency_id': fields.many2one(
            'res.currency', 'Currency',
            help="The optional other currency if it is a "
                 "multi-currency entry."),
        'type': fields.selection([('dr', 'Debit'), ('cr', 'Credit')], 'Cr/Dr'),
    }



    def create(self, cr, uid, vals, context=None):
        # This sucks and is really slow so we try and
        # and bulk write it at statement create
        if context is None:
            context = {}
        if not context.get('move_written'):
            self.pool['account.move.line'].write(
                cr, uid, [vals['move_line_id']],
                {'draft_assigned_to_statement': True}, context=context)
        return super(BankAccRecStatementLine, self).create(
            cr, uid, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        move_line_ids = [line.move_line_id.id for line in
                         self.browse(cr, uid, ids, context=context)]
        # Reset field values in move lines to be added later
        if move_line_ids:
            aml_obj = self.pool['account.move.line']
            aml_obj.write(cr, uid, move_line_ids,
                          {'draft_assigned_to_statement': False,
                           'cleared_bank_account': False,
                           'bank_acc_rec_statement_id': False,
                           }, context=context)
        return super(BankAccRecStatementLine, self).unlink(
            cr, uid, ids, context=context)
