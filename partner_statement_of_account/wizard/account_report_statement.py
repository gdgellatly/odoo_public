# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution - module extension
#    Copyright (C) 2010- Graeme Gellatly - O4SB (<http://openforsmallbusiness.co.nz>).
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from osv import osv, fields

class account_report_partner_statement(osv.TransientModel):
    '''
    Statement of Account
    '''
    _name = 'account.partner.statement'
    _description = __doc__
    
    _columns = {
        'initial_balance': fields.boolean('Include initial balances',
                                    help='It adds initial balance row on report '
                                    'which display previous sum amount of '
                                    'debit/credit/balance'),
        'reconcil': fields.boolean('Include Reconciled Entries',
                                   help='Consider reconciled entries'),
        'partners': fields.many2many('res.partner', 'custom_report_partner_rel',
                                     'partners', 'partner_id', 'Partners',
                                     required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'period_from': fields.many2one('account.period', 'Period'),
        'statement_type': fields.selection([('open', 'Open Item'),
                                            ('activity', 'Activity')],
                                           "Statement Type", required=True),
        'zero_balance': fields.boolean('Include Zero and Credit balances'),
        'aging': fields.selection([('months', 'Age by Months'),
                                   ('days', 'Age by Days')], 'Aging',
                                  help='Show aging on balances by days or months'),
        'days': fields.integer('Days'),
        'date_from': fields.date('Date From'),
        'target_move': fields.selection([('posted', 'All Posted Entries'),
                                         ('all', 'All Entries'),
                                        ], 'Target Moves', required=True),
        'groupdebtor': fields.boolean('Central Debtor',
                                      help='If partner is a parent include '
                                      'subsidiaries activity'),
        'multicompany': fields.boolean('Consolidated Statement',
                                       help='Consolidated Statement from this and all '
                                       'child companies - requires appropriate access '
                                       'rights')
    }

### Functions to initialise defaults    
    def _get_company_id(self, cr, uid, context=None):
        company = self.pool.get('res.users').browse(cr,uid, uid).company_id.id
        return company or False

    def _get_period(self, cr, uid, context=None):
        last_month = (datetime.now()-relativedelta(months=1)).strftime('%Y-%m-%d')
        company_id = self._get_company_id(cr, uid, context)      
        period = self.pool.get('account.period').search(cr, uid, [('date_start', '<', last_month), ('date_stop', '>', last_month), ('company_id', '=', company_id)] ,)
        return period and period[0] or False

    def _get_account(self, cr, uid, context=None):
        company_id = self._get_company_id(cr, uid, context)
        accounts = self.pool.get('account.account').search(cr, uid, [('parent_id', '=', False), ('company_id', '=', company_id)], limit=1)
        return accounts and accounts[0] or False
    
    def _get_default_partners(self, cr, uid, context=None):
        if context['active_model'] == 'res.partner':
            search_args = [('id', 'in', context['active_ids'])]
        else:
            search_args = [('customer', '=', True), ('credit', '>', 0.0)]
        return self.pool.get('res.partner').search(cr, uid, search_args, context=context)

    _defaults = {
        'company_id': _get_company_id,
        'period_from': _get_period,
        'statement_type': 'activity',
        'reconcil': False,
        'zero_balance': False,
        'initial_balance': False,
        'multicompany': False,
        'groupdebtor': False,
        'aging': 'months',
        'days': 30,
        'partners': _get_default_partners,
        'target_move': 'posted',
    }

### Onchange Functions to set logical default settings for changes    
    def onchange_aging(self, cr, uid, ids, aging, company_id, context=None):
        res = {}
        if not company_id:
            return res
        last_month = (datetime.now()-relativedelta(months=1)).strftime('%Y-%m-%d')
        if aging == 'days':
            res['value'] = {'period_from': False, 'date_from': time.strftime('%Y-01-01')}
        if aging == 'months':
            period = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', last_month), ('date_stop', '>=', last_month), ('company_id', '=', company_id)] ,)
            res['value'] = {'period_from': period[0], 'date_from': False}
        return res
    
    def onchange_statement_type(self, cr, uid, ids, statement_type, context=None):
        if statement_type == 'open':
            return {'value': {'initial_balance': False, 'reconcil': False}}
        return {'value': {'initial_balance': True, 'reconcil': True}}

### Functions for check_report to generate non partner dependent info to report to reduce processing time    
    def _get_date(self, cr, uid, ids, context):
        """Determines date report is based on, 
        @return: iso_format/postgres formatted date string"""
        fields = self.read(cr, uid, ids, ['aging', 'date_from', 'period_from'], context)[0] 
        if fields['aging'] == 'months':
            period = self.pool.get('account.period').browse(cr, uid, fields['period_from'][0])
            return period.date_stop
        else: 
            return fields['date_from']
        
    def _get_invoices(self, cr, uid, ids, context=None):
        inv_obj = self.pool.get('account.invoice')
        wizard = self.browse(cr, uid, ids)[0]
        inv_ids = inv_obj.search(cr, uid, [('type', '=', 'out_invoice'), ('period', '=', wizard.period_from.id), ('state', 'not in', ('draft', 'cancel'))])
        cn_ids = inv_obj.search(cr, uid, [('type', '=', 'out_invoice'), ('period', '=', wizard.period_from.id), ('state', 'not in', ('draft', 'cancel'))])
        
    def _move_ids(self, cr, uid, ids, context=None):
        """
        @return: dictionary whose keys are partner ids, and values are lists
        of move line ids relevant to the partner and wizard input
        """
        move_line_pool = self.pool.get('account.move.line')
        fields = self.read(cr,uid,ids,['groupdebtor', 'partners', 'target_move', 'result_selection', 'reconcil', 'company_id', 'multicompany'], context=context)[0]
        
        move_state = ['draft','posted']
        if fields['target_move'] == 'posted':
            move_state = ['posted']
        search_tuples = [('move_id.state', 'in', move_state)]
        
        partner_ids = fields['partners']
        if fields['groupdebtor']:
            search_tuples.extend(['|',('partner_id.parent_id', '!=', False),('partner_id', 'in', partner_ids)])
        else:
            search_tuples.append(('partner_id', 'in', partner_ids))
# We have a limitation here.  If we use the commented out search tuple, lines reconciled after NOW (as in the 
# date the report is run, will still show the reconciled amount.  While this can be tested, if it was previously 
# partially reconciled, OpenERP does not store this information, so either way it would be wrong.  With the current
# implementation, entries reconciled as of NOW will not show.  This is acceptable, because, even if the counter
# reconciling entry occurred after the date of the report, in most cases it also would be reconciled.  This limitation
# is primarily only felt in monthly aging reports, as in days aging NOW and date can be the same        
        if not fields['reconcil']:
            search_tuples.append(('reconcile_id', '=', False))
#            search_tuples.extend(['|',('reconcile_id', '=', False), ('reconcile_id.create_date', '>', self._get_date(cr, uid, ids, context))])
#  Really we need to go back to the payment date
        if fields['result_selection'] == 'customer_supplier':
            search_tuples.append(('account_id.type', 'in', ['receivable', 'payable']))
        else: 
            search_tuples.append(('account_id.type', '=', fields['result_selection']))
        company_ids = [fields['company_id'][0]]
        if fields['multicompany']:
            company_pool_obj = self.pool.get('res.company')
            company_ids.extend([x[0] for x in company_pool_obj.search(cr, uid, [('id', 'child_of', company_ids)] )])
        search_tuples.append(('company_id', 'in', company_ids))
        
        ids = move_line_pool.search(cr, uid, search_tuples, order='ref asc')
        move_lines = move_line_pool.browse(cr, uid, ids, context)
        res = dict((partner_id, []) for partner_id in partner_ids)
        for line in move_lines:
            if line.partner_id.id in partner_ids:
                res[line.partner_id.id].append(line.id) 
            if fields['groupdebtor']:
                if line.partner_id.parent_id and (line.partner_id.parent_id.id in partner_ids):
                    res[line.partner_id.parent_id.id].append(line.id)
                if line.partner_id.parent_id.parent_id and (line.partner_id.parent_id.parent_id.id in partner_ids):
                    res[line.partner_id.parent_id.parent_id.id].append(line.id)      
        return res
    
    def _get_partners(self, cr, uid, ids, context=None): 
        """
        @param move_ids: a dictionary with key partner_id, and a list of move_ids           
        @return: a list of ints (partner_ids) ordered alphabetically
        """ 

        wizard = self.browse(cr, uid, ids)[0]
        if wizard.zero_balance:
            partner_ids = [(p.name, p.id) for p in wizard.partners]
        else:
            partner_ids = [(p.name, p.id) for p in wizard.partners if p.credit > 0.0]
        partner_ids = [x[1] for x in sorted(partner_ids)]
        return partner_ids

### Function to prepare data for sending to report
    def check_report(self, cr, uid, ids, context=None):
        """
        Prepares data for sending to parser.
        @return: report object res.partner.statement
        """
        if context is None:
            context = {}
        wiz = self.browse(cr, uid, ids)[0]
        data = {}
#        data['move_ids'] = self._move_ids(cr, uid, ids, context)
        data['ids'] = self._get_partners(cr, uid, ids, context)
        data['id'] = data['ids'][0]
        data['date'] = self._get_date(cr, uid, ids, context)
        data['model'] = context.get('active_model', 'res.partner')
        data['form'] = {'initial_balance': wiz.initial_balance, 
                        'statement_type': wiz.statement_type, 
                        'aging': wiz.aging,
                        'days': wiz.days,
                        'company_id': wiz.company_id.id,
                        'groupdebtor': wiz.groupdebtor, 
                        'multicompany': wiz.multicompany, 
                        'period_from': wiz.period_from.date_stop}
        context.update(data)
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'res.partner.statement',
            'datas': data,
            'context': context,
            }
